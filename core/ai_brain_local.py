"""
Local AI Brain - Полностью автономный мозг без внешних API
Использует ML модель + News Sentiment + Technical Analysis

Архитектура:
1. News Brain (CryptoPanic + VADER) -> Risk Check
2. ML Service (RandomForest/XGBoost) -> Signal Generation
3. Technical Analysis -> Confirmation
4. Decision Tree -> Final Decision

v3.0: Gatekeeper система - двухуровневая фильтрация входов
"""
import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

from core.news_brain import get_news_brain, MarketSentiment
from core.ml_predictor_v2 import get_ml_predictor_v2  # Используем существующую LSTM модель!
from core.ta_lib import get_choppiness_index
from core.strategic_brain import get_strategic_brain, REGIME_BULL_RUSH, REGIME_BEAR_CRASH, REGIME_SIDEWAYS, REGIME_UNCERTAIN

# Import GlobalBrainState для обновления Neural HUD
try:
    from core.state import get_global_brain_state
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False
    print("⚠️ GlobalBrainState not available")

# Online Learning (опционально - graceful degradation)
try:
    from core.self_learning import get_self_learner
    SELF_LEARNING_AVAILABLE = True
except ImportError:
    SELF_LEARNING_AVAILABLE = False
    print("⚠️ Self-learning module not available")

# Scenario Tester (опционально - graceful degradation)
try:
    from core.scenario_tester import get_scenario_tester
    SCENARIO_TESTER_AVAILABLE = True
except ImportError:
    SCENARIO_TESTER_AVAILABLE = False
    print("⚠️ Scenario tester not available")


class DecisionSource(Enum):
    """Источник решения"""
    ML_CONFIRMED = "ML_CONFIRMED"      # ML + TA подтверждение
    NEWS_OVERRIDE = "NEWS_OVERRIDE"    # Новости перекрыли ML
    SAFETY_MODE = "SAFETY_MODE"        # Безопасный режим (fallback)
    TA_ONLY = "TA_ONLY"               # Только технический анализ


class TradingAction(Enum):
    """Торговое действие"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    SKIP = "SKIP"
    PANIC_SELL = "PANIC_SELL"
    CLOSE_ALL = "CLOSE_ALL"


class LocalBrain:
    """
    Локальный мозг для автономной торговли
    
    Decision Tree:
    1. Risk Check (News) -> EXTREME_FEAR = PANIC_SELL
    2. ML Signal -> Confidence >= 75% = Trade
    3. TA Confirmation -> Boost confidence
    4. Final Decision
    """
    
    def __init__(self, api_client=None):
        self.news_brain = get_news_brain()
        self.ml_predictor = get_ml_predictor_v2()  # LSTM модель v2
        self.ml_loaded = False
        
        # Strategic Brain (Gatekeeper Level 0)
        self.strategic_brain = get_strategic_brain()
        self.api_client = api_client  # Для получения дневных свечей
        
        # Online Learning (опционально)
        self.self_learner = None
        if SELF_LEARNING_AVAILABLE:
            try:
                self.self_learner = get_self_learner()
            except Exception as e:
                print(f"⚠️ Self-learner init failed: {e}")
                self.self_learner = None
        
        # ========== GATEKEEPER v3.0 ==========
        self.scenario_tester = None
        if SCENARIO_TESTER_AVAILABLE and api_client:
            try:
                self.scenario_tester = get_scenario_tester(api_client)
                print("🔍 Gatekeeper: ScenarioTester initialized")
            except Exception as e:
                print(f"⚠️ Gatekeeper: ScenarioTester init failed: {e}")
        
        # Пороги фильтрации (SMART GROWTH $100 - строгие фильтры)
        self.chop_threshold = 60.0  # CHOP > 60 = флэт (строго - не торгуем шум)
        self.historical_wr_threshold = 25.0  # Historical WR < 25% = плохой паттерн
        
        # Минимальные confidence для входа (из config)
        from config import settings
        self.min_confidence_long = settings.futures_min_confidence  # 60% для LONG
        self.min_confidence_short = settings.futures_min_confidence_short  # 65% для SHORT
        
        if SCENARIO_TESTER_AVAILABLE:
            print(f"🚦 Gatekeeper v3.0 enabled:")
            print(f"   CHOP threshold: {self.chop_threshold}")
            print(f"   Historical WR threshold: {self.historical_wr_threshold}%")
        
        # Конфигурация - OPTIMIZED v2.2 (24/7 trading)
        self.config = {
            'min_ml_confidence': 0.55,       # Минимальная уверенность ML (55% - баланс)
            'min_change_pct': 0.4,           # Минимальный % изменения для сигнала
            'news_weight': 0.25,             # Вес новостей в решении
            'ml_weight': 0.45,               # Вес ML в решении
            'ta_weight': 0.30,               # Вес TA в решении (повышен!)
            'enable_news_analysis': True,    # Включить анализ новостей
            'enable_panic_sell': True,       # Включить паник-селл при плохих новостях
            'require_ta_confirmation': False, # Отключено - слишком строго
            'trading_hours_enabled': False,  # ОТКЛЮЧЕНО - торгуем 24/7
            'trading_hours_start': 0,        # Начало торговли UTC (не используется)
            'trading_hours_end': 24          # Конец торговли UTC (не используется)
        }
        
        # Статистика
        self.stats = {
            'total_decisions': 0,
            'ml_confirmed': 0,
            'news_overrides': 0,
            'safety_mode': 0,
            'ta_only': 0,
            'panic_sells': 0,
            'buys': 0,
            'sells': 0,
            'holds': 0,
            'skips': 0
        }
        
        # Последний анализ новостей (кэш)
        self._last_news_analysis = None
        self._last_news_time = None
    
    async def _check_news_risk(self, symbol: str) -> Dict:
        """
        Шаг 1: Проверка риска по новостям
        
        Returns:
            {
                'allow_trading': bool,
                'allow_buy': bool,
                'allow_sell': bool,
                'sentiment': MarketSentiment,
                'score': float,
                'recommendation': str
            }
        """
        if not self.config['enable_news_analysis']:
            return {
                'allow_trading': True,
                'allow_buy': True,
                'allow_sell': True,
                'sentiment': MarketSentiment.NEUTRAL,
                'score': 0.0,
                'recommendation': 'News analysis disabled'
            }
        
        try:
            # Получаем сентимент
            news_data = await self.news_brain.get_market_sentiment(symbol, hours_back=1)
            
            sentiment = news_data['sentiment']
            score = news_data['score']
            
            # Определяем разрешения
            allow_trading = True
            allow_buy = True
            allow_sell = True
            
            if sentiment == MarketSentiment.EXTREME_FEAR:
                # Паника - только продажи!
                allow_trading = self.config['enable_panic_sell']
                allow_buy = False
                allow_sell = True
            elif sentiment == MarketSentiment.FEAR:
                # Страх - осторожные покупки
                allow_buy = True  # Но с пониженным размером
                allow_sell = True
            elif sentiment == MarketSentiment.EXTREME_GREED:
                # Жадность - только покупки
                allow_buy = True
                allow_sell = False  # Не продаем на хайпе
            
            return {
                'allow_trading': allow_trading,
                'allow_buy': allow_buy,
                'allow_sell': allow_sell,
                'sentiment': sentiment,
                'score': score,
                'news_count': news_data['news_count'],
                'recommendation': news_data['recommendation']
            }
        
        except Exception as e:
            print(f"⚠️  News analysis error: {e}")
            # При ошибке - разрешаем торговлю, но осторожно
            return {
                'allow_trading': True,
                'allow_buy': True,
                'allow_sell': True,
                'sentiment': MarketSentiment.NEUTRAL,
                'score': 0.0,
                'recommendation': f'News API error: {e}'
            }
    
    async def _get_ml_signal(self, market_data: Dict) -> Dict:
        """
        Шаг 2: Получить сигнал от LSTM модели v2
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'HOLD',
                'confidence': 0.0-1.0,
                'predicted_change_pct': float,
                'direction': 'UP'/'DOWN'/'SKIP'
            }
        """
        # Загружаем модель если ещё не загружена
        if not self.ml_loaded:
            self.ml_loaded = await self.ml_predictor.load_model()
        
        if not self.ml_loaded:
            return {
                'decision': 'HOLD',
                'confidence': 0.0,
                'predicted_change_pct': 0.0,
                'direction': 'SKIP',
                'error': 'ML model not loaded'
            }
        
        # Получаем klines из market_data
        klines = market_data.get('klines', [])
        symbol = market_data.get('symbol', 'BTCUSDT')
        current_price = market_data.get('price', 0)
        
        if not klines or len(klines) < 60:
            return {
                'decision': 'HOLD',
                'confidence': 0.0,
                'predicted_change_pct': 0.0,
                'direction': 'SKIP',
                'error': 'Not enough klines'
            }
        
        # Предсказание LSTM
        result = await self.ml_predictor.predict(symbol, current_price, klines)
        
        # Конвертируем direction в decision
        direction = result.get('direction', 'SKIP')
        confidence = result.get('confidence', 0.0)
        change_pct = result.get('predicted_change_pct', 0.0)
        
        # Если ML не уверен - используем TA fallback
        if direction == 'SKIP' or confidence < 0.4:
            ta_signal = market_data.get('technical_signal', 'NEUTRAL')
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', {})
            macd_trend = macd.get('trend', 'neutral')
            
            # Сильные RSI сигналы
            if rsi < 25:  # Экстремально перепродан
                direction = 'UP'
                confidence = 0.75
                change_pct = 1.5
            elif rsi > 75:  # Экстремально перекуплен
                direction = 'DOWN'
                confidence = 0.75
                change_pct = -1.5
            elif rsi < 35:  # Перепродан - покупаем!
                direction = 'UP'
                confidence = 0.60
                change_pct = 0.8
            elif rsi > 65:  # Перекуплен - продаём!
                direction = 'DOWN'
                confidence = 0.60
                change_pct = -0.8
            elif rsi < 45 and macd_trend == 'bullish':
                direction = 'UP'
                confidence = 0.55
                change_pct = 0.5
            elif rsi > 55 and macd_trend == 'bearish':
                direction = 'DOWN'
                confidence = 0.55
                change_pct = -0.5
        
        if direction == 'UP':
            decision = 'BUY'
        elif direction == 'DOWN':
            decision = 'SELL'
        else:
            decision = 'HOLD'
        
        return {
            'decision': decision,
            'confidence': confidence,
            'predicted_change_pct': change_pct,
            'direction': direction,
            'predicted_price': result.get('predicted_price', 0)
        }
    
    def _check_ta_confirmation(self, ml_decision: str, market_data: Dict) -> Dict:
        """
        Шаг 3: Проверить подтверждение от технического анализа
        
        Returns:
            {
                'confirms': bool,
                'ta_signal': str,
                'strength': float (0-1)
            }
        """
        ta_signal = market_data.get('technical_signal', 'SKIP')
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        trend = market_data.get('trend', 'sideways')
        
        confirms = False
        strength = 0.5
        
        # Проверяем совпадение сигналов
        if ml_decision == 'BUY':
            if ta_signal == 'BUY':
                confirms = True
                strength = 0.8
            elif rsi < 35 and macd_trend == 'bullish':
                confirms = True
                strength = 0.7
            elif trend in ['uptrend', 'strong_uptrend']:
                confirms = True
                strength = 0.6
        
        elif ml_decision == 'SELL':
            if ta_signal == 'SELL':
                confirms = True
                strength = 0.8
            elif rsi > 65 and macd_trend == 'bearish':
                confirms = True
                strength = 0.7
            elif trend in ['downtrend', 'strong_downtrend']:
                confirms = True
                strength = 0.6
        
        elif ml_decision == 'HOLD':
            if ta_signal == 'SKIP':
                confirms = True
                strength = 0.5
        
        return {
            'confirms': confirms,
            'ta_signal': ta_signal,
            'strength': strength,
            'rsi': rsi,
            'macd_trend': macd_trend,
            'trend': trend
        }
    
    def _calculate_risk_score(
        self, 
        market_data: Dict, 
        news_data: Dict,
        ml_confidence: float
    ) -> int:
        """Рассчитать риск-скор (1-10)"""
        risk = 5  # Базовый
        
        # RSI экстремумы
        rsi = market_data.get('rsi', 50)
        if rsi > 75 or rsi < 25:
            risk += 2
        elif rsi > 65 or rsi < 35:
            risk += 1
        
        # Волатильность
        volatility = market_data.get('volatility', 0)
        if volatility > 0.05:  # >5%
            risk += 2
        elif volatility > 0.03:
            risk += 1
        
        # Новостной фон
        sentiment = news_data.get('sentiment', MarketSentiment.NEUTRAL)
        if sentiment in [MarketSentiment.EXTREME_FEAR, MarketSentiment.EXTREME_GREED]:
            risk += 2
        elif sentiment in [MarketSentiment.FEAR, MarketSentiment.GREED]:
            risk += 1
        
        # ML уверенность (низкая = выше риск)
        if ml_confidence < 0.6:
            risk += 2
        elif ml_confidence < 0.75:
            risk += 1
        
        return min(10, max(1, risk))

    def _is_trading_hours(self) -> bool:
        """Проверить, находимся ли в торговых часах"""
        # Если фильтр отключен - всегда торгуем
        if not self.config.get('trading_hours_enabled', True):
            return True
        
        from datetime import datetime, timezone
        current_hour = datetime.now(timezone.utc).hour
        start = self.config.get('trading_hours_start', 0)
        end = self.config.get('trading_hours_end', 24)
        return start <= current_hour < end

    async def decide_trade(self, market_data: Dict) -> Dict:
        """
        Главный метод принятия решения - OPTIMIZED v2.0
        
        Decision Tree:
        0. Trading Hours Check -> Skip if outside hours
        1. News Risk Check -> EXTREME_FEAR = PANIC_SELL
        2. ML Signal -> Confidence check (60%+)
        3. TA Confirmation -> REQUIRED for entry
        4. Final Decision
        
        Args:
            market_data: Данные рынка с индикаторами
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'SKIP'/'PANIC_SELL',
                'confidence': 0.0-1.0,
                'risk_score': 1-10,
                'source': DecisionSource,
                'reasoning': str,
                'position_size_multiplier': 0.0-1.0,
                'news_sentiment': MarketSentiment,
                'ml_signal': {...},
                'ta_confirmation': {...}
            }
        """
        self.stats['total_decisions'] += 1
        symbol = market_data.get('symbol', 'UNKNOWN')
        
        print(f"\n🧠 Local Brain analyzing {symbol}...")
        
        # Обновляем GlobalBrainState - начало анализа
        if STATE_AVAILABLE:
            try:
                state = get_global_brain_state()
                state.update_system_status(running=True, scan_time=datetime.now())
            except Exception as e:
                pass  # Не критично
        
        # ========== GATEKEEPER LEVEL 0: STRATEGIC BRAIN (Market Regime) ==========
        # Определяет глобальный режим рынка раз в 4 часа через Claude
        strategic_regime = None
        try:
            # Получаем дневные свечи для анализа (7 дней)
            daily_candles = []
            if self.api_client:
                # Берём BTC и ETH как индикаторы рынка
                for major_symbol in ['BTCUSDT', 'ETHUSDT']:
                    try:
                        candles_data = await self.api_client.get_klines(
                            symbol=major_symbol,
                            interval='D',  # Дневные свечи
                            limit=7
                        )
                        for candle in candles_data:
                            daily_candles.append({
                                'symbol': major_symbol,
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5])
                            })
                    except Exception as e:
                        print(f"   ⚠️ Failed to get daily candles for {major_symbol}: {e}")
            
            # Получаем сводку новостей
            news_summary = "No news data"
            try:
                news_data = await self.news_brain.get_market_sentiment(symbol, hours_back=24)
                news_summary = f"{news_data['sentiment'].value} (score: {news_data['score']:.2f}, {news_data['news_count']} news)"
            except:
                pass
            
            # Запрашиваем режим у Strategic Brain
            if daily_candles:
                strategic_regime = await self.strategic_brain.get_market_regime(
                    daily_candles=daily_candles,
                    news_summary=news_summary
                )
                print(f"   🎯 Strategic Regime: {strategic_regime}")
        except Exception as e:
            print(f"   ⚠️ Strategic Brain error: {e}")
            strategic_regime = REGIME_SIDEWAYS  # Fallback
        
        # ========== ШАГ 0: TRADING HOURS CHECK ==========
        if not self._is_trading_hours():
            from datetime import datetime, timezone
            current_hour = datetime.now(timezone.utc).hour
            print(f"   ⏰ Outside trading hours ({current_hour}:00 UTC). Skipping.")
            self.stats['skips'] += 1
            return {
                'decision': 'SKIP',
                'confidence': 0.0,
                'risk_score': 5,
                'source': DecisionSource.SAFETY_MODE.value,
                'reasoning': f'Outside trading hours ({current_hour}:00 UTC)',
                'position_size_multiplier': 0.0,
                'news_sentiment': MarketSentiment.NEUTRAL.value,
                'ml_signal': None,
                'ta_confirmation': None
            }
        
        # ========== GATEKEEPER LEVEL 1: CHOP CHECK ==========
        chop = 50.0  # Default neutral
        try:
            klines = market_data.get('klines', [])
            if len(klines) >= 15:
                high = np.array([float(k['high']) for k in klines])
                low = np.array([float(k['low']) for k in klines])
                close = np.array([float(k['close']) for k in klines])
                
                chop = get_choppiness_index(high, low, close, period=14)
                
                # Обновляем GlobalBrainState - CHOP
                if STATE_AVAILABLE:
                    try:
                        state = get_global_brain_state()
                        state.update_market_data(symbol, chop=chop)
                    except:
                        pass
                
                # Проверка: CHOP > 60 (флэт/боковик)
                if chop > self.chop_threshold:
                    print(f"   🚫 Gatekeeper: Choppy Market (CHOP: {chop:.1f} > {self.chop_threshold})")
                    
                    # Обновляем Gatekeeper status
                    if STATE_AVAILABLE:
                        try:
                            state = get_global_brain_state()
                            state.update_gatekeeper(symbol, f"BLOCK: CHOP {chop:.1f}")
                        except:
                            pass
                    
                    self.stats['skips'] += 1
                    return {
                        'decision': 'SKIP',
                        'confidence': 0.0,
                        'risk_score': 8,
                        'source': DecisionSource.SAFETY_MODE.value,
                        'reasoning': f'Choppy Market (CHOP: {chop:.1f})',
                        'position_size_multiplier': 0.0,
                        'news_sentiment': MarketSentiment.NEUTRAL.value,
                        'ml_signal': None,
                        'ta_confirmation': None,
                        'gatekeeper': {'chop': chop, 'reason': 'CHOP_FILTER'}
                    }
        except Exception as e:
            print(f"   ⚠️ CHOP calculation error: {e}")
        
        # ========== ШАГ 1: NEWS RISK CHECK ==========
        news_data = await self._check_news_risk(symbol)
        sentiment = news_data['sentiment']
        
        print(f"   📰 News Sentiment: {sentiment.value} (score: {news_data['score']:.2f})")
        
        # Обновляем GlobalBrainState - новости
        if STATE_AVAILABLE:
            try:
                state = get_global_brain_state()
                headline = news_data.get('recommendation', 'No news')
                state.update_news(
                    sentiment=news_data['score'],
                    headline=headline,
                    count=news_data.get('news_count', 0)
                )
            except Exception as e:
                pass
        
        # PANIC SELL при экстремальном страхе
        if sentiment == MarketSentiment.EXTREME_FEAR and self.config['enable_panic_sell']:
            self.stats['panic_sells'] += 1
            self.stats['news_overrides'] += 1
            
            return {
                'decision': 'PANIC_SELL',
                'confidence': 0.95,
                'risk_score': 10,
                'source': DecisionSource.NEWS_OVERRIDE.value,
                'reasoning': f'EXTREME FEAR detected! {news_data["recommendation"]}',
                'position_size_multiplier': 0.0,
                'news_sentiment': sentiment.value,
                'ml_signal': None,
                'ta_confirmation': None
            }
        
        # ========== ШАГ 2: ML SIGNAL (LSTM v2) ==========
        ml_result = await self._get_ml_signal(market_data)
        ml_decision = ml_result['decision']
        ml_confidence = ml_result['confidence']
        
        change_pct = ml_result.get('predicted_change_pct', 0)
        print(f"   🤖 ML Signal: {ml_decision} (conf: {ml_confidence:.0%}, change: {change_pct:+.2f}%)")
        
        # Обновляем GlobalBrainState - ML prediction
        if STATE_AVAILABLE:
            try:
                state = get_global_brain_state()
                state.update_ml_prediction(symbol, ml_decision, ml_confidence, change_pct)
                
                # Обновляем RSI и цену
                rsi = market_data.get('rsi', 50)
                price = market_data.get('price', 0)
                state.update_market_data(symbol, rsi=rsi, price=price)
            except Exception as e:
                pass
        
        # Проверяем разрешения от новостей
        if ml_decision == 'BUY' and not news_data['allow_buy']:
            print(f"   ⚠️  BUY blocked by news sentiment")
            ml_decision = 'HOLD'
            ml_confidence *= 0.5
        
        if ml_decision == 'SELL' and not news_data['allow_sell']:
            print(f"   ⚠️  SELL blocked by news sentiment (EXTREME_GREED)")
            ml_decision = 'HOLD'
            ml_confidence *= 0.5
        
        # Фильтр уверенности (SMART GROWTH $100 - разные пороги для LONG/SHORT)
        min_conf_required = self.min_confidence_long if ml_decision == 'BUY' else self.min_confidence_short
        
        if ml_confidence < min_conf_required and ml_decision != 'HOLD':
            action_type = "LONG" if ml_decision == 'BUY' else "SHORT"
            print(f"   ⚠️  ML confidence too low for {action_type} ({ml_confidence:.0%} < {min_conf_required:.0%})")
            self.stats['skips'] += 1
            
            return {
                'decision': 'SKIP',
                'confidence': ml_confidence,
                'risk_score': 7,
                'source': DecisionSource.SAFETY_MODE.value,
                'reasoning': f'ML confidence too low for {action_type}: {ml_confidence:.0%} < {min_conf_required:.0%}',
                'position_size_multiplier': 0.0,
                'news_sentiment': sentiment.value,
                'ml_signal': ml_result,
                'ta_confirmation': None
            }
        
        # ========== GATEKEEPER LEVEL 2: PATTERN CHECK ==========
        historical_wr = 50.0  # Default neutral
        
        if self.scenario_tester and ml_decision in ['BUY', 'SELL']:
            try:
                # Lazy Loading: обновляем историю если нужно
                await self.scenario_tester.update_history(symbol)
                
                # Анализируем исторические паттерны
                historical_wr = self.scenario_tester.analyze_outcome(symbol, ml_decision)
                
                # Проверка: Historical WR < 25% (с исключением для сильных ML сигналов)
                # ИСКЛЮЧЕНИЕ: Если ML уверен (>60%), пропускаем даже с плохим WR
                if historical_wr < self.historical_wr_threshold and ml_confidence < 0.60:
                    print(f"   🚫 Gatekeeper: Bad Historical Pattern (WR: {historical_wr:.1f}%)")
                    self.stats['skips'] += 1
                    return {
                        'decision': 'SKIP',
                        'confidence': 0.0,
                        'risk_score': 7,
                        'source': DecisionSource.SAFETY_MODE.value,
                        'reasoning': f'Bad Historical Pattern (WR: {historical_wr:.1f}%)',
                        'position_size_multiplier': 0.0,
                        'news_sentiment': sentiment.value,
                        'ml_signal': ml_result,
                        'ta_confirmation': None,
                        'gatekeeper': {'chop': chop, 'historical_wr': historical_wr, 'reason': 'PATTERN_FILTER'}
                    }
                elif historical_wr < self.historical_wr_threshold and ml_confidence >= 0.60:
                    print(f"   ⚠️  Gatekeeper: Bad Pattern (WR: {historical_wr:.1f}%) BUT Strong ML (conf: {ml_confidence:.0%}) - OVERRIDE")
                else:
                    print(f"   ✅ Gatekeeper: PASSED (CHOP: {chop:.1f}, Historical WR: {historical_wr:.1f}%)")
            
            except Exception as e:
                print(f"   ⚠️ Pattern analysis error: {e}")
        
        # ========== ШАГ 3: TA CONFIRMATION ==========
        ta_data = self._check_ta_confirmation(ml_decision, market_data)
        
        print(f"   📊 TA Confirmation: {'✅' if ta_data['confirms'] else '❌'} (strength: {ta_data['strength']:.0%})")
        
        # ========== ШАГ 3.5: SELF-LEARNING PREDICTION (опционально) ==========
        self_learning_score = 0.5  # Нейтральный по умолчанию
        self_learning_confidence = 0.0
        ml_features = None
        
        if self.self_learner:
            try:
                # Извлекаем фичи для Self-Learning
                # Используем ta_data вместо market_data (правильная структура)
                ml_features = self.self_learner.extract_features(
                    technical={
                        'rsi': ta_data.get('rsi', 50.0),
                        'macd': {'trend': market_data.get('macd', 'neutral')},
                        'bb': {'position': market_data.get('bb', 'within_bands')},
                        'trend': {'direction': market_data.get('trend', 'neutral'), 'strength': 0.5},
                        'volatility': market_data.get('volatility', 0.0),
                        'volume_ratio': market_data.get('volume_ratio', 1.0)
                    },
                    news_score=news_data.get('score', 0.0),
                    ml_confidence=ml_confidence
                )
                
                # Получаем предсказание от Self-Learner
                self_learning_score, self_learning_confidence = self.self_learner.predict(ml_features)
                
                if self.self_learner.learning_count >= 50:  # Только если модель обучена
                    print(f"   🧠 Self-Learning: {self_learning_score:.2f} (conf: {self_learning_confidence:.2f})")
            
            except Exception as e:
                print(f"   ⚠️ Self-learning prediction failed: {e}")
                ml_features = None
        
        # Корректируем уверенность на основе TA + Self-Learning
        final_confidence = ml_confidence
        
        # TA влияние (СМЯГЧЕНО - не убиваем confidence)
        if ta_data['confirms']:
            final_confidence = min(0.95, ml_confidence * 1.15)  # Boost +15%
        else:
            final_confidence = ml_confidence * 0.90  # Reduce только -10% (было -25%)
        
        # Self-Learning влияние (5% веса, если модель обучена)
        # СНИЖЕНО с 20% до 5% - Self-Learning не должен убивать сигналы
        if self.self_learner and self.self_learner.learning_count >= 50:
            # Взвешивание: 95% Static ML + 5% Self-Learning
            final_confidence = (final_confidence * 0.95) + (self_learning_score * 0.05)
        
        # ========== TA CONFIRMATION (опционально) ==========
        # Если TA не подтверждает - уменьшаем размер позиции вместо SKIP
        if self.config.get('require_ta_confirmation', False) and not ta_data['confirms']:
            if ml_decision in ['BUY', 'SELL']:
                print(f"   ⚠️  TA does not confirm {ml_decision} - reducing position size")
                # Не блокируем, но уменьшаем размер
        
        # ========== ШАГ 4: FEE PROFITABILITY CHECK (SMART GROWTH $100) ==========
        # Проверяем, окупит ли сделка комиссии + минимальный TP 0.6%
        from config import settings, is_trade_profitable_after_fees
        
        if settings.simulate_fees_in_demo and ml_decision in ['BUY', 'SELL']:
            try:
                # Получаем текущую цену и рассчитываем TP
                current_price = market_data.get('price', 0)
                
                # Рассчитываем TP на основе change_pct от ML
                if ml_decision == 'BUY':
                    take_profit = current_price * (1 + abs(change_pct) / 100)
                else:  # SELL
                    take_profit = current_price * (1 - abs(change_pct) / 100)
                
                # ПРОВЕРКА 1: Минимальный TP 0.6% (комиссия + проскальзывание + микро-профит)
                tp_pct = abs(change_pct)
                min_tp_pct = settings.min_profit_threshold_pct  # 0.6%
                
                if tp_pct < min_tp_pct:
                    print(f"   ⚠️  Trade blocked: TP too small ({tp_pct:.2f}% < {min_tp_pct:.2f}%)")
                    self.stats['skips'] += 1
                    
                    return {
                        'decision': 'SKIP',
                        'confidence': 0.0,
                        'risk_score': 6,
                        'source': DecisionSource.SAFETY_MODE.value,
                        'reasoning': f"TP too small: {tp_pct:.2f}% < {min_tp_pct:.2f}% (not worth fees)",
                        'position_size_multiplier': 0.0,
                        'news_sentiment': sentiment.value,
                        'ml_signal': ml_result,
                        'ta_confirmation': ta_data
                    }
                
                # ПРОВЕРКА 2: Прибыльность после комиссий
                quantity = 1.0  # Условное количество для проверки
                
                profitability = is_trade_profitable_after_fees(
                    entry_price=current_price,
                    take_profit=take_profit,
                    quantity=quantity,
                    side=ml_decision
                )
                
                if not profitability['is_profitable']:
                    print(f"   ⚠️  Trade blocked: {profitability['reason']}")
                    self.stats['skips'] += 1
                    
                    return {
                        'decision': 'SKIP',
                        'confidence': 0.0,
                        'risk_score': 6,
                        'source': DecisionSource.SAFETY_MODE.value,
                        'reasoning': f"Profit too small after fees: {profitability['reason']}",
                        'position_size_multiplier': 0.0,
                        'news_sentiment': sentiment.value,
                        'ml_signal': ml_result,
                        'ta_confirmation': ta_data,
                        'fee_check': profitability
                    }
                else:
                    print(f"   ✅ Fee check passed: Profitable: ${profitability['net_profit']:.2f} net (after ${profitability['total_fee']:.2f} fees)")
            
            except Exception as e:
                print(f"   ⚠️ Fee profitability check error: {e}")
        
        # ========== GATEKEEPER LEVEL 0.5: STRATEGIC VETO ==========
        # Проверяем, разрешён ли сигнал в текущем рыночном режиме
        if strategic_regime and ml_decision in ['BUY', 'SELL']:
            signal_allowed = self.strategic_brain.should_allow_signal(
                signal_direction=ml_decision,
                current_regime=strategic_regime
            )
            
            if not signal_allowed:
                # Strategic Brain заблокировал сигнал
                self.stats['skips'] += 1
                
                return {
                    'decision': 'SKIP',
                    'confidence': 0.0,
                    'risk_score': 5,
                    'source': DecisionSource.SAFETY_MODE.value,
                    'reasoning': f'Strategic Veto: {ml_decision} blocked in {strategic_regime} regime',
                    'position_size_multiplier': 0.0,
                    'news_sentiment': sentiment.value,
                    'ml_signal': ml_result,
                    'ta_confirmation': ta_data,
                    'strategic_regime': strategic_regime
                }
        
        # ========== ШАГ 5: FINAL DECISION ==========
        risk_score = self._calculate_risk_score(market_data, news_data, final_confidence)
        
        # Определяем размер позиции
        position_multiplier = 1.0
        
        if sentiment == MarketSentiment.FEAR:
            position_multiplier = 0.5  # Уменьшаем при страхе
        elif sentiment == MarketSentiment.EXTREME_GREED:
            position_multiplier = 1.2  # Увеличиваем при жадности (только лонги)
        
        if not ta_data['confirms']:
            position_multiplier *= 0.7  # Уменьшаем без подтверждения TA
        
        # Финальное решение
        final_decision = ml_decision
        source = DecisionSource.ML_CONFIRMED
        
        if ml_decision == 'HOLD':
            final_decision = 'SKIP'
            self.stats['holds'] += 1
        elif ml_decision == 'BUY':
            self.stats['buys'] += 1
        elif ml_decision == 'SELL':
            self.stats['sells'] += 1
        
        # Формируем reasoning
        reasoning_parts = []
        reasoning_parts.append(f"ML: {ml_result['decision']} ({ml_confidence:.0%})")
        reasoning_parts.append(f"News: {sentiment.value}")
        reasoning_parts.append(f"TA: {'confirms' if ta_data['confirms'] else 'conflicts'}")
        reasoning_parts.append(f"RSI: {ta_data['rsi']:.1f}")
        
        reasoning = " | ".join(reasoning_parts)
        
        print(f"   ✅ Final Decision: {final_decision} (conf: {final_confidence:.0%}, risk: {risk_score}/10)")
        
        self.stats['ml_confirmed'] += 1
        
        return {
            'decision': final_decision,
            'confidence': final_confidence,
            'risk_score': risk_score,
            'source': source.value,
            'reasoning': reasoning,
            'position_size_multiplier': position_multiplier,
            'news_sentiment': sentiment.value,
            'ml_signal': ml_result,
            'ta_confirmation': ta_data,
            'ml_features': ml_features,  # Для Self-Learning
            'strategic_regime': strategic_regime  # Режим рынка от Claude
        }
    
    def print_stats(self):
        """Вывести статистику"""
        total = self.stats['total_decisions']
        if total == 0:
            print("🧠 Local Brain: No decisions yet")
            return
        
        print(f"\n🧠 Local Brain Statistics:")
        print(f"   Total Decisions: {total}")
        print(f"   ML Confirmed: {self.stats['ml_confirmed']} ({self.stats['ml_confirmed']/total*100:.1f}%)")
        print(f"   News Overrides: {self.stats['news_overrides']} ({self.stats['news_overrides']/total*100:.1f}%)")
        print(f"   Safety Mode: {self.stats['safety_mode']} ({self.stats['safety_mode']/total*100:.1f}%)")
        print(f"   ---")
        print(f"   BUYs: {self.stats['buys']}")
        print(f"   SELLs: {self.stats['sells']}")
        print(f"   HOLDs: {self.stats['holds']}")
        print(f"   SKIPs: {self.stats['skips']}")
        print(f"   PANIC SELLs: {self.stats['panic_sells']}")
        
        # Статистика подмодулей
        self.news_brain.print_stats()


# Singleton
_local_brain = None

def get_local_brain(api_client=None) -> LocalBrain:
    """Получить singleton instance"""
    global _local_brain
    if _local_brain is None:
        _local_brain = LocalBrain(api_client)
    return _local_brain
