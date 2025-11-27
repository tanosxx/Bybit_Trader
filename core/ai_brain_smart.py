"""
Smart Hybrid AI Brain - ML Gatekeeper Architecture
ML модель принимает решения, AI только для спорных случаев
Экономит API квоты в 10+ раз
"""
import os
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import httpx
from config import settings
from core.ml_predictor_v2 import get_ml_predictor_v2


class DecisionSource:
    """Источник решения"""
    ML_ONLY = "ML_ONLY"           # Только ML (экономия API)
    AI_CONFIRMED = "AI_CONFIRMED"  # ML + AI подтверждение
    SAFETY_MODE = "SAFETY_MODE"    # Fallback при недоступности AI


class CircuitBreaker:
    """Circuit Breaker для защиты от rate limits"""
    
    def __init__(self, cooldown_minutes: int = 15):
        self.cooldown_minutes = cooldown_minutes
        self.is_open = False
        self.opened_at = None
        self.failure_count = 0
    
    def record_failure(self):
        """Записать ошибку API"""
        self.failure_count += 1
        if self.failure_count >= 3:  # После 3 ошибок - открываем
            self.open()
    
    def open(self):
        """Открыть circuit breaker (блокировать AI запросы)"""
        self.is_open = True
        self.opened_at = datetime.utcnow()
        print(f"🔴 Circuit Breaker OPEN - AI requests blocked for {self.cooldown_minutes} min")
    
    def close(self):
        """Закрыть circuit breaker"""
        self.is_open = False
        self.opened_at = None
        self.failure_count = 0
        print(f"🟢 Circuit Breaker CLOSED - AI requests enabled")
    
    def check_and_reset(self) -> bool:
        """Проверить и сбросить если прошло время"""
        if not self.is_open:
            return False
        
        if datetime.utcnow() - self.opened_at > timedelta(minutes=self.cooldown_minutes):
            self.close()
            return False
        
        return True
    
    def can_call_ai(self) -> bool:
        """Можно ли делать запрос к AI"""
        return not self.check_and_reset()


class SmartAIBrain:
    """
    Smart Hybrid AI Brain
    
    Архитектура:
    1. ML модель (RandomForest) - первичный фильтр
    2. Технический анализ - подтверждение
    3. AI (Gemini) - только для спорных случаев
    
    Экономия API: ~90% запросов
    """
    
    def __init__(self):
        self.ml_predictor = get_ml_predictor_v2()  # LSTM модель v2
        self.ml_model_loaded = False
        self.circuit_breaker = CircuitBreaker(cooldown_minutes=1)  # Быстрый сброс для тестов
        
        # Статистика
        self.stats = {
            'total_decisions': 0,
            'ml_only_decisions': 0,
            'ai_confirmed_decisions': 0,
            'safety_mode_decisions': 0,
            'api_calls_saved': 0,
            'api_calls_made': 0
        }
    
    async def init_ml_model(self):
        """Асинхронная загрузка ML модели"""
        if not self.ml_model_loaded:
            self.ml_model_loaded = await self.ml_predictor.load_model()
            if self.ml_model_loaded:
                print(f"✅ Smart AI Brain: LSTM model ready")
            else:
                print(f"⚠️  Smart AI Brain: No ML model, AI-only mode")
    
    def _prepare_ml_features(self, market_data: Dict) -> np.ndarray:
        """
        Подготовить фичи для ML модели
        
        Features: [price, rsi, macd_value, macd_signal, bb_upper, bb_middle, bb_lower, 
                   ema_20, ema_50, volume, trend_score]
        """
        try:
            features = [
                market_data.get('price', 0),
                market_data.get('rsi', 50),
                market_data['macd'].get('value', 0),
                market_data['macd'].get('signal', 0),
                market_data['bollinger_bands'].get('upper', 0),
                market_data['bollinger_bands'].get('middle', 0),
                market_data['bollinger_bands'].get('lower', 0),
                market_data.get('ema_20', market_data.get('price', 0)),
                market_data.get('ema_50', market_data.get('price', 0)),
                market_data.get('volume', 0),
                self._calculate_trend_score(market_data)
            ]
            
            return np.array(features).reshape(1, -1)
        
        except Exception as e:
            print(f"❌ Error preparing ML features: {e}")
            return None
    
    def _calculate_trend_score(self, market_data: Dict) -> float:
        """Рассчитать числовой score тренда"""
        trend = market_data.get('trend', 'NEUTRAL')
        
        if trend == 'BULLISH':
            return 1.0
        elif trend == 'BEARISH':
            return -1.0
        else:
            return 0.0
    
    async def _ml_predict(self, market_data: Dict, klines: list = None) -> Optional[Dict]:
        """
        ML предсказание через LSTM модель
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'HOLD',
                'confidence': 0.85,
                'predicted_change': 0.02  # +2%
            }
        """
        if not self.ml_model_loaded:
            return None
        
        # Если нет klines - используем простой fallback на основе TA
        if not klines:
            return self._simple_ta_decision(market_data)
        
        try:
            symbol = market_data.get('symbol', 'BTCUSDT')
            current_price = market_data.get('price', 0)
            
            # Используем LSTM predictor
            result = await self.ml_predictor.predict(symbol, current_price, klines)
            
            if not result or 'error' in result:
                return self._simple_ta_decision(market_data)
            
            predicted_change = result.get('change_pct', 0) / 100  # конвертируем в доли
            confidence = result.get('confidence', 0.5)
            direction = result.get('direction', 'SKIP')
            
            # Проверка на нереальные значения (ML модель сломана)
            if abs(predicted_change) > 1.0:  # >100% - явно баг
                print(f"⚠️  ML prediction unrealistic ({predicted_change*100:.1f}%), using TA fallback")
                return self._simple_ta_decision(market_data)
            
            # Конвертируем direction в decision
            if direction == 'UP':
                decision = 'BUY'
            elif direction == 'DOWN':
                decision = 'SELL'
            else:
                decision = 'HOLD'
            
            return {
                'decision': decision,
                'confidence': confidence,
                'predicted_change': predicted_change
            }
        
        except Exception as e:
            print(f"❌ ML prediction error: {e}")
            return self._simple_ta_decision(market_data)
    
    def _simple_ta_decision(self, market_data: Dict) -> Dict:
        """Простое решение на основе технического анализа"""
        ta_signal = market_data.get('technical_signal', 'NEUTRAL')
        rsi = market_data.get('rsi', 50)
        trend = market_data.get('trend', 'sideways')
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        
        decision = 'HOLD'
        confidence = 0.5
        
        # Сильные сигналы на основе RSI
        if rsi < 25:  # Сильно перепродан
            decision = 'BUY'
            confidence = 0.75
        elif rsi > 75:  # Сильно перекуплен
            decision = 'SELL'
            confidence = 0.75
        # Средние сигналы
        elif rsi < 35 and macd_trend == 'bullish':
            decision = 'BUY'
            confidence = 0.65
        elif rsi > 65 and macd_trend == 'bearish':
            decision = 'SELL'
            confidence = 0.65
        # TA сигнал
        elif ta_signal == 'BUY':
            decision = 'BUY'
            confidence = 0.6
        elif ta_signal == 'SELL':
            decision = 'SELL'
            confidence = 0.6
        
        return {
            'decision': decision,
            'confidence': confidence,
            'predicted_change': 0.0
        }
    
    def _check_ta_confirmation(self, ml_decision: str, market_data: Dict) -> bool:
        """
        Проверить подтверждение от технического анализа
        
        Args:
            ml_decision: BUY/SELL/HOLD
            market_data: данные рынка с индикаторами
        
        Returns:
            True если TA подтверждает ML решение
        """
        ta_signal = market_data.get('technical_signal', 'SKIP')
        
        # Конвертируем ML решение в формат TA
        if ml_decision == 'BUY' and ta_signal == 'BUY':
            return True
        elif ml_decision == 'SELL' and ta_signal == 'SELL':
            return True
        elif ml_decision == 'HOLD' and ta_signal == 'SKIP':
            return True
        
        return False
    
    async def _call_ai_api(self, market_data: Dict, ml_prediction: Dict) -> Optional[Dict]:
        """
        Вызвать Gemini API для спорных случаев
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'SKIP',
                'confidence': 0.75,
                'risk_score': 5,
                'reasoning': '...'
            }
        """
        if not self.circuit_breaker.can_call_ai():
            print("⚠️  Circuit Breaker is OPEN - skipping AI call")
            return None
        
        try:
            prompt = self._build_ai_prompt(market_data, ml_prediction)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-flash-1.5",
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
            
            if response.status_code == 429:
                print("❌ API Rate Limit - opening Circuit Breaker")
                self.circuit_breaker.record_failure()
                return None
            
            if response.status_code != 200:
                print(f"❌ AI API error: {response.status_code}")
                self.circuit_breaker.record_failure()
                return None
            
            # Успешный запрос - сбрасываем счетчик ошибок
            self.circuit_breaker.failure_count = 0
            self.stats['api_calls_made'] += 1
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            return self._parse_ai_response(content)
        
        except Exception as e:
            print(f"❌ AI API call failed: {e}")
            self.circuit_breaker.record_failure()
            return None
    
    def _build_ai_prompt(self, market_data: Dict, ml_prediction: Dict) -> str:
        """Построить промпт для AI"""
        return f"""Analyze this crypto market situation and make a trading decision.

Symbol: {market_data.get('symbol', 'UNKNOWN')}
Current Price: ${market_data.get('price', 0):.2f}

Technical Indicators:
- RSI: {market_data.get('rsi', 0):.1f}
- MACD: {market_data['macd'].get('trend', 'UNKNOWN')}
- Bollinger Bands: {market_data['bollinger_bands'].get('position', 'UNKNOWN')}
- Trend: {market_data.get('trend', 'UNKNOWN')}
- Volume Trend: {market_data.get('volume_trend', 'UNKNOWN')}

ML Model Prediction:
- Decision: {ml_prediction['decision']}
- Confidence: {ml_prediction['confidence']:.0%}
- Predicted Change: {ml_prediction['predicted_change']:+.2%}

Technical Analysis Signal: {market_data.get('technical_signal', 'UNKNOWN')}

IMPORTANT: ML and TA signals are conflicting or ML confidence is low.
Your task: Make final decision considering all factors.

Respond in this EXACT format:
DECISION: [BUY/SELL/SKIP]
CONFIDENCE: [0-100]
RISK: [1-10]
REASONING: [One sentence explanation]"""
    
    def _parse_ai_response(self, content: str) -> Dict:
        """Парсинг ответа AI"""
        try:
            lines = content.strip().split('\n')
            result = {}
            
            for line in lines:
                if line.startswith('DECISION:'):
                    result['decision'] = line.split(':')[1].strip()
                elif line.startswith('CONFIDENCE:'):
                    conf_str = line.split(':')[1].strip().replace('%', '')
                    result['confidence'] = float(conf_str) / 100
                elif line.startswith('RISK:'):
                    result['risk_score'] = int(line.split(':')[1].strip())
                elif line.startswith('REASONING:'):
                    result['reasoning'] = line.split(':', 1)[1].strip()
            
            return result
        
        except Exception as e:
            print(f"❌ Failed to parse AI response: {e}")
            return {
                'decision': 'SKIP',
                'confidence': 0.0,
                'risk_score': 10,
                'reasoning': 'Parse error'
            }
    
    async def decide_trade(self, market_data: Dict) -> Dict:
        """
        Главный метод принятия решения
        
        Smart Flow:
        1. ML предсказание
        2. Если ML уверен (>80%) + TA подтверждает -> торгуем БЕЗ AI
        3. Если ML неуверен или противоречие -> запрос к AI
        4. Если AI недоступен -> Safety Mode (ML + TA, но размер позиции /2)
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'SKIP',
                'confidence': 0.85,
                'risk_score': 5,
                'source': 'ML_ONLY'/'AI_CONFIRMED'/'SAFETY_MODE',
                'reasoning': '...',
                'position_size_multiplier': 1.0 или 0.5
            }
        """
        self.stats['total_decisions'] += 1
        
        # Инициализируем ML модель если ещё не загружена
        if not self.ml_model_loaded:
            await self.init_ml_model()
        
        # 1. ML предсказание
        klines = market_data.get('klines', None)
        ml_prediction = await self._ml_predict(market_data, klines)
        
        if not ml_prediction:
            # Нет ML модели - используем только AI (дорого!)
            print("⚠️  No ML model - falling back to AI only")
            ai_result = await self._call_ai_api(market_data, {'decision': 'UNKNOWN', 'confidence': 0, 'predicted_change': 0})
            
            if ai_result:
                self.stats['ai_confirmed_decisions'] += 1
                return {
                    **ai_result,
                    'source': DecisionSource.AI_CONFIRMED,
                    'position_size_multiplier': 1.0
                }
            else:
                # Совсем нет данных - SKIP
                return {
                    'decision': 'SKIP',
                    'confidence': 0.0,
                    'risk_score': 10,
                    'source': DecisionSource.SAFETY_MODE,
                    'reasoning': 'No ML model and AI unavailable',
                    'position_size_multiplier': 0.0
                }
        
        print(f"🤖 ML Prediction: {ml_prediction['decision']} (conf: {ml_prediction['confidence']:.0%}, change: {ml_prediction['predicted_change']:+.2%})")
        
        # 2. Проверяем уверенность ML и подтверждение TA
        ml_confident = ml_prediction['confidence'] >= 0.80
        ta_confirms = self._check_ta_confirmation(ml_prediction['decision'], market_data)
        
        # 3. FAST PATH: ML уверен + TA подтверждает -> торгуем БЕЗ AI
        if ml_confident and ta_confirms and ml_prediction['decision'] != 'HOLD':
            print(f"✅ ML confident ({ml_prediction['confidence']:.0%}) + TA confirms -> Trading WITHOUT AI")
            self.stats['ml_only_decisions'] += 1
            self.stats['api_calls_saved'] += 1
            
            # Рассчитываем риск на основе индикаторов
            risk_score = self._calculate_risk_from_indicators(market_data)
            
            return {
                'decision': ml_prediction['decision'],
                'confidence': ml_prediction['confidence'],
                'risk_score': risk_score,
                'source': DecisionSource.ML_ONLY,
                'reasoning': f"ML confident {ml_prediction['confidence']:.0%}, TA confirms, predicted change {ml_prediction['predicted_change']:+.2%}",
                'position_size_multiplier': 1.0
            }
        
        # 4. SLOW PATH: ML неуверен или противоречие -> запрос к AI
        print(f"⚠️  ML uncertain or conflict (conf: {ml_prediction['confidence']:.0%}, TA: {ta_confirms}) -> Calling AI")
        
        ai_result = await self._call_ai_api(market_data, ml_prediction)
        
        if ai_result:
            # AI доступен - используем его решение
            self.stats['ai_confirmed_decisions'] += 1
            return {
                **ai_result,
                'source': DecisionSource.AI_CONFIRMED,
                'position_size_multiplier': 1.0
            }
        
        # 5. FALLBACK: AI недоступен -> Торгуем на основе ML + TA
        print(f"⚠️  AI unavailable -> Trading based on ML + TA")
        self.stats['safety_mode_decisions'] += 1
        
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        trend = market_data.get('trend', 'sideways')
        
        # Определяем решение на основе комбинации сигналов
        decision = 'SKIP'
        confidence = 0.5
        reasoning = ''
        
        # 1. Сильный RSI сигнал (перепродан/перекуплен)
        if rsi < 35:
            decision = 'BUY'
            confidence = 0.7 if rsi < 30 else 0.6
            reasoning = f"RSI oversold ({rsi:.1f})"
        elif rsi > 65:
            decision = 'SELL'
            confidence = 0.7 if rsi > 70 else 0.6
            reasoning = f"RSI overbought ({rsi:.1f})"
        # 2. MACD + Trend согласны
        elif macd_trend == 'bullish' and trend in ['uptrend', 'strong_uptrend']:
            decision = 'BUY'
            confidence = 0.55
            reasoning = f"MACD bullish + {trend}"
        elif macd_trend == 'bearish' and trend in ['downtrend', 'strong_downtrend']:
            decision = 'SELL'
            confidence = 0.55
            reasoning = f"MACD bearish + {trend}"
        # 3. ML дал сигнал (не HOLD)
        elif ml_prediction['decision'] != 'HOLD':
            decision = ml_prediction['decision']
            confidence = max(ml_prediction['confidence'], 0.5)
            reasoning = f"ML signal: {ml_prediction['predicted_change']*100:+.2f}%"
        
        if decision != 'SKIP':
            risk_score = self._calculate_risk_from_indicators(market_data)
            return {
                'decision': decision,
                'confidence': confidence,
                'risk_score': min(risk_score, 8),
                'source': DecisionSource.SAFETY_MODE,
                'reasoning': f"Auto: {reasoning}",
                'position_size_multiplier': 0.5
            }
        else:
            return {
                'decision': 'SKIP',
                'confidence': 0.0,
                'risk_score': 10,
                'source': DecisionSource.SAFETY_MODE,
                'reasoning': f'No clear signal (RSI={rsi:.1f}, MACD={macd_trend})',
                'position_size_multiplier': 0.0
            }
    
    def _calculate_risk_from_indicators(self, market_data: Dict) -> int:
        """Рассчитать риск на основе индикаторов (1-10)"""
        risk = 5  # Базовый риск
        
        # RSI
        rsi = market_data.get('rsi', 50)
        if rsi > 70 or rsi < 30:
            risk += 2  # Перекупленность/перепроданность
        
        # Волатильность (BB)
        bb_position = market_data['bollinger_bands'].get('position', 'MIDDLE')
        if bb_position in ['ABOVE_UPPER', 'BELOW_LOWER']:
            risk += 1
        
        # Тренд
        trend = market_data.get('trend', 'NEUTRAL')
        if trend == 'NEUTRAL':
            risk += 1  # Неопределенность
        
        # Volume
        volume_trend = market_data.get('volume_trend', 'NORMAL')
        if volume_trend == 'LOW':
            risk += 1  # Низкая ликвидность
        
        return min(risk, 10)
    
    def print_stats(self):
        """Вывести статистику"""
        total = self.stats['total_decisions']
        if total == 0:
            print("📊 No decisions made yet")
            return
        
        ml_pct = (self.stats['ml_only_decisions'] / total) * 100
        ai_pct = (self.stats['ai_confirmed_decisions'] / total) * 100
        safety_pct = (self.stats['safety_mode_decisions'] / total) * 100
        
        print(f"📊 Smart AI Brain Statistics:")
        print(f"   Total Decisions: {total}")
        print(f"   ML Only: {self.stats['ml_only_decisions']} ({ml_pct:.1f}%) 💰")
        print(f"   AI Confirmed: {self.stats['ai_confirmed_decisions']} ({ai_pct:.1f}%)")
        print(f"   Safety Mode: {self.stats['safety_mode_decisions']} ({safety_pct:.1f}%)")
        print(f"   API Calls Saved: {self.stats['api_calls_saved']} 🎉")
        print(f"   API Calls Made: {self.stats['api_calls_made']}")
        print(f"   Circuit Breaker: {'🔴 OPEN' if self.circuit_breaker.is_open else '🟢 CLOSED'}")


# Singleton
_smart_ai_brain = None

def get_smart_ai_brain() -> SmartAIBrain:
    """Получить singleton instance"""
    global _smart_ai_brain
    if _smart_ai_brain is None:
        _smart_ai_brain = SmartAIBrain()
    return _smart_ai_brain
