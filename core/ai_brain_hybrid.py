"""
Гибридный AI Brain: ML-First + Smart Rate Limiter
Экономия API запросов любой ценой!
"""
import aiohttp
import json
import time
import joblib
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from config import settings, GEMINI_CRYPTO_ANALYSIS_PROMPT

# Отключаем TensorFlow warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class CircuitBreaker:
    """Circuit Breaker для защиты от спама API"""
    
    def __init__(self, cooldown_seconds=300):
        self.is_open = False
        self.cooldown_seconds = cooldown_seconds
        self.opened_at = None
    
    def open(self):
        """Открыть circuit (заморозить запросы)"""
        self.is_open = True
        self.opened_at = datetime.now()
        print(f"🔴 Circuit Breaker ОТКРЫТ! Заморозка на {self.cooldown_seconds}с")
    
    def check(self) -> bool:
        """Проверить можно ли делать запросы"""
        if not self.is_open:
            return True
        
        # Проверяем прошло ли время cooldown
        if datetime.now() - self.opened_at > timedelta(seconds=self.cooldown_seconds):
            self.is_open = False
            self.opened_at = None
            print(f"🟢 Circuit Breaker ЗАКРЫТ! Можно делать запросы")
            return True
        
        remaining = self.cooldown_seconds - (datetime.now() - self.opened_at).seconds
        print(f"⏳ Circuit Breaker открыт, осталось {remaining}с")
        return False


class RateLimiter:
    """Rate Limiter для троттлинга запросов"""
    
    def __init__(self, min_interval_seconds=20):
        self.min_interval = min_interval_seconds
        self.last_request_time = {}
    
    def can_request(self, key_id: str) -> bool:
        """Проверить можно ли делать запрос с этого ключа"""
        if key_id not in self.last_request_time:
            return True
        
        elapsed = time.time() - self.last_request_time[key_id]
        if elapsed < self.min_interval:
            remaining = self.min_interval - elapsed
            print(f"⏱️  Rate limit: подожди {remaining:.1f}с для ключа {key_id}")
            return False
        
        return True
    
    def mark_request(self, key_id: str):
        """Отметить что запрос был сделан"""
        self.last_request_time[key_id] = time.time()


class ResponseCache:
    """Кэш для предотвращения повторных запросов"""
    
    def __init__(self, ttl_seconds=60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, symbol: str, price: float) -> Optional[Dict]:
        """Получить из кэша если цена изменилась незначительно"""
        if symbol not in self.cache:
            return None
        
        cached_data, cached_time = self.cache[symbol]
        
        # Проверяем TTL
        if time.time() - cached_time > self.ttl:
            del self.cache[symbol]
            return None
        
        # Проверяем изменение цены
        cached_price = cached_data.get('price', 0)
        price_change_pct = abs((price - cached_price) / cached_price) * 100
        
        if price_change_pct < 0.1:  # Менее 0.1% изменения
            print(f"💾 Кэш: цена изменилась на {price_change_pct:.3f}%, используем старый анализ")
            return cached_data.get('result')
        
        return None
    
    def set(self, symbol: str, price: float, result: Dict):
        """Сохранить в кэш"""
        self.cache[symbol] = ({'price': price, 'result': result}, time.time())


class MLPredictor:
    """Локальная ML модель для предсказаний (LSTM)"""
    
    def __init__(self, model_path="ml_training/models"):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.model_path = model_path
        self.sequence_length = 60
        self._load_model()
    
    def _load_model(self):
        """Загрузить LSTM модель"""
        try:
            import os
            
            # Загружаем LSTM модель
            lstm_model_file = os.path.join(self.model_path, "bybit_lstm_model.h5")
            scaler_X_file = os.path.join(self.model_path, "scaler_X.pkl")
            scaler_y_file = os.path.join(self.model_path, "scaler_y.pkl")
            
            if os.path.exists(lstm_model_file) and os.path.exists(scaler_X_file):
                # Загружаем TensorFlow модель
                try:
                    import tensorflow as tf
                    self.model = tf.keras.models.load_model(lstm_model_file, compile=False)
                    self.scaler_X = joblib.load(scaler_X_file)
                    self.scaler_y = joblib.load(scaler_y_file)
                    print(f"✅ LSTM модель загружена из {lstm_model_file}")
                except ImportError:
                    print(f"⚠️ TensorFlow не установлен, ML отключен")
                    print(f"   Установи: pip install tensorflow")
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки LSTM (несовместимая версия TensorFlow)")
                    print(f"   ML отключен, работаем только с API + защитой от спама")
            else:
                print(f"⚠️ ML модель не найдена в {self.model_path}")
                print(f"   Работаем только с API + защитой от спама")
        except Exception as e:
            print(f"❌ Ошибка загрузки ML модели: {e}")
            print(f"   Работаем только с API + защитой от спама")
    
    def predict(self, market_data: Dict) -> Optional[Dict]:
        """
        Предсказание через LSTM модель
        
        Returns:
            {
                "decision": "BUY/SELL/SKIP",
                "confidence": 0.0-1.0,
                "source": "ML"
            }
        """
        if not self.model or not self.scaler_X:
            return None
        
        try:
            # LSTM предсказывает цену, а не класс
            # Для простоты: если предсказанная цена выше текущей → BUY
            current_price = market_data.get('price', 0)
            
            # Подготовка фичей (нужна последовательность из 60 свечей)
            # Пока используем упрощённую логику без последовательности
            features = self._prepare_features(market_data)
            if features is None:
                return None
            
            # Нормализация
            features_scaled = self.scaler_X.transform([features])
            
            # LSTM требует 3D вход: (samples, timesteps, features)
            # Создаём фейковую последовательность (повторяем текущие данные)
            sequence = np.tile(features_scaled, (self.sequence_length, 1))
            sequence = sequence.reshape(1, self.sequence_length, len(features))
            
            # Предсказание цены
            predicted_price_scaled = self.model.predict(sequence, verbose=0)[0][0]
            predicted_price = self.scaler_y.inverse_transform([[predicted_price_scaled]])[0][0]
            
            # Вычисляем изменение цены
            price_change_pct = ((predicted_price - current_price) / current_price) * 100
            
            # Решение на основе предсказания
            if price_change_pct > 0.5:  # Рост > 0.5%
                decision = "BUY"
                confidence = min(0.95, 0.5 + abs(price_change_pct) / 10)
            elif price_change_pct < -0.5:  # Падение > 0.5%
                decision = "SELL"
                confidence = min(0.95, 0.5 + abs(price_change_pct) / 10)
            else:  # Незначительное изменение
                decision = "SKIP"
                confidence = 0.6
            
            return {
                "decision": decision,
                "confidence": float(confidence),
                "source": "ML_LSTM",
                "predicted_price": float(predicted_price),
                "price_change_pct": float(price_change_pct)
            }
        
        except Exception as e:
            print(f"❌ Ошибка ML предсказания: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _prepare_features(self, market_data: Dict) -> Optional[list]:
        """
        Подготовить фичи из market_data (24 фичи как в обучении)
        
        Порядок фичей:
        'open', 'high', 'low', 'close', 'volume',
        'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
        'atr', 'stoch_k', 'stoch_d', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
        """
        try:
            import math
            from datetime import datetime
            
            # Текущее время для временных фичей
            now = datetime.now()
            hour = now.hour
            day = now.day
            month = now.month
            
            # Циклические временные фичи
            hour_sin = math.sin(2 * math.pi * hour / 24)
            hour_cos = math.cos(2 * math.pi * hour / 24)
            day_sin = math.sin(2 * math.pi * day / 31)
            day_cos = math.cos(2 * math.pi * day / 31)
            month_sin = math.sin(2 * math.pi * month / 12)
            month_cos = math.cos(2 * math.pi * month / 12)
            
            # Получаем цену
            price = market_data.get('price', 0)
            
            # 24 фичи в правильном порядке
            features = [
                price,  # open (используем текущую цену)
                price * 1.001,  # high (примерно)
                price * 0.999,  # low (примерно)
                price,  # close
                market_data.get('volume_24h', 0),  # volume
                market_data.get('rsi', 50),  # rsi
                market_data.get('macd', {}).get('value', 0),  # macd
                market_data.get('macd', {}).get('signal', 0),  # macd_signal
                market_data.get('bollinger_bands', {}).get('upper', price * 1.02),  # bb_upper
                market_data.get('bollinger_bands', {}).get('middle', price),  # bb_middle
                market_data.get('bollinger_bands', {}).get('lower', price * 0.98),  # bb_lower
                market_data.get('atr', price * 0.01),  # atr (примерно 1%)
                market_data.get('stochastic', {}).get('k', 50),  # stoch_k
                market_data.get('stochastic', {}).get('d', 50),  # stoch_d
                price,  # sma_20 (примерно текущая цена)
                price,  # sma_50 (примерно текущая цена)
                price,  # ema_12 (примерно текущая цена)
                price,  # ema_26 (примерно текущая цена)
                hour_sin,  # hour_sin
                hour_cos,  # hour_cos
                day_sin,  # day_sin
                day_cos,  # day_cos
                month_sin,  # month_sin
                month_cos,  # month_cos
            ]
            
            return features
        except Exception as e:
            print(f"❌ Ошибка подготовки фичей: {e}")
            import traceback
            traceback.print_exc()
            return None


class AIBrainHybrid:
    """
    Гибридный AI Brain: ML-First + Smart Rate Limiter
    
    Стратегия:
    1. ML модель (локально) - приоритет
    2. Gemini API - только в спорных случаях
    3. Жёсткий троттлинг и circuit breaker
    4. Кэширование результатов
    """
    
    def __init__(self):
        # ML модель (локально)
        self.ml_predictor = MLPredictor()
        
        # Защита от спама
        self.circuit_breaker = CircuitBreaker(cooldown_seconds=300)  # 5 минут
        self.rate_limiter = RateLimiter(min_interval_seconds=20)  # 20 секунд
        self.cache = ResponseCache(ttl_seconds=60)  # 1 минута
        
        # Gemini API ключи
        self.google_api_keys = [
            settings.google_api_key_1,
            settings.google_api_key_2,
            settings.google_api_key_3,
        ]
        self.google_api_keys = [k for k in self.google_api_keys if k]
        
        # Модели (только самые эффективные)
        self.gemini_models = [
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]
        
        # Статистика
        self.stats = {
            "ml_decisions": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "circuit_breaker_blocks": 0
        }
    
    async def analyze_market(self, market_data: Dict) -> Optional[Dict]:
        """
        Гибридный анализ рынка
        
        Приоритет:
        1. Кэш (если цена не изменилась)
        2. ML модель (если уверенность > 80%)
        3. Gemini API (только в спорных случаях)
        """
        symbol = market_data.get('symbol', 'UNKNOWN')
        price = market_data.get('price', 0)
        
        # 1. Проверяем кэш
        cached_result = self.cache.get(symbol, price)
        if cached_result:
            self.stats['cache_hits'] += 1
            print(f"💾 Используем кэш для {symbol}")
            return cached_result
        
        # 2. ML предсказание (приоритет!)
        ml_result = self.ml_predictor.predict(market_data)
        
        if ml_result:
            confidence = ml_result['confidence']
            decision = ml_result['decision']
            
            print(f"🤖 ML: {decision} (уверенность: {confidence:.0%})")
            
            # Если уверенность высокая - НЕ делаем API запрос!
            if confidence >= 0.80:
                self.stats['ml_decisions'] += 1
                result = {
                    "decision": decision,
                    "risk_score": self._confidence_to_risk(confidence),
                    "confidence": confidence,
                    "reasoning": f"ML модель с высокой уверенностью ({confidence:.0%})",
                    "key_factors": ["ML prediction", f"Confidence: {confidence:.0%}"],
                    "source": "ML"
                }
                
                # Сохраняем в кэш
                self.cache.set(symbol, price, result)
                
                print(f"✅ ML решение принято БЕЗ API запроса!")
                return result
            
            # Уверенность средняя (50-80%) - спросим Gemini
            print(f"⚠️ ML уверенность средняя ({confidence:.0%}), спросим Gemini")
        
        # 3. Gemini API (только в спорных случаях)
        api_result = await self._call_gemini_safe(market_data)
        
        if api_result:
            # Комбинируем ML и API результаты
            if ml_result:
                api_result['ml_confidence'] = ml_result['confidence']
                api_result['ml_decision'] = ml_result['decision']
            
            # Сохраняем в кэш
            self.cache.set(symbol, price, api_result)
            
            return api_result
        
        # 4. Fallback на ML если API не ответил
        if ml_result:
            print(f"⚠️ API не ответил, используем ML (уверенность: {ml_result['confidence']:.0%})")
            self.stats['ml_decisions'] += 1
            
            result = {
                "decision": ml_result['decision'],
                "risk_score": self._confidence_to_risk(ml_result['confidence']),
                "confidence": ml_result['confidence'],
                "reasoning": f"ML fallback (API недоступен)",
                "key_factors": ["ML prediction (fallback)"],
                "source": "ML_FALLBACK"
            }
            
            self.cache.set(symbol, price, result)
            return result
        
        # 5. Совсем ничего не сработало
        print(f"❌ Ни ML, ни API не дали результат")
        return None
    
    async def _call_gemini_safe(self, market_data: Dict) -> Optional[Dict]:
        """
        Безопасный вызов Gemini с защитой от спама
        """
        # Проверяем Circuit Breaker
        if not self.circuit_breaker.check():
            self.stats['circuit_breaker_blocks'] += 1
            return None
        
        # Пробуем ключи с rate limiting
        for key_idx, api_key in enumerate(self.google_api_keys):
            if not api_key:
                continue
            
            key_id = f"key_{key_idx+1}"
            
            # Проверяем rate limit
            if not self.rate_limiter.can_request(key_id):
                continue
            
            # Пробуем модели
            for model_name in self.gemini_models:
                try:
                    result = await self._call_gemini_api(api_key, model_name, market_data)
                    
                    if result:
                        # Успех! Отмечаем запрос
                        self.rate_limiter.mark_request(key_id)
                        self.stats['api_calls'] += 1
                        
                        print(f"✅ Gemini (ключ #{key_idx+1}, {model_name}): {result['decision']}")
                        return result
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # Если 429 - открываем Circuit Breaker!
                    if "429" in error_msg or "quota" in error_msg.lower() or "exhausted" in error_msg.lower():
                        print(f"🔴 429 Error! Открываем Circuit Breaker")
                        self.circuit_breaker.open()
                        return None
                    
                    continue
        
        return None
    
    async def _call_gemini_api(self, api_key: str, model_name: str, market_data: Dict) -> Optional[Dict]:
        """Вызов Gemini API"""
        prompt = GEMINI_CRYPTO_ANALYSIS_PROMPT.format(
            market_data=json.dumps(market_data, indent=2)
        )
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 300  # Уменьшили для экономии
            }
        }
        
        headers = {"Content-Type": "application/json"}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # Очищаем от markdown
                    text = text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()
                    
                    # Находим JSON
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                    
                    result = json.loads(text)
                    result['source'] = 'GEMINI'
                    
                    return result
                
                elif response.status == 429:
                    raise Exception("429 Resource Exhausted")
                
                else:
                    return None
    
    def _confidence_to_risk(self, confidence: float) -> int:
        """Конвертировать уверенность в риск (1-10)"""
        # Высокая уверенность = низкий риск
        return max(1, min(10, int((1 - confidence) * 10)))
    
    def print_stats(self):
        """Вывести статистику использования"""
        print(f"\n📊 Статистика AI Brain:")
        print(f"   ML решений: {self.stats['ml_decisions']}")
        print(f"   API запросов: {self.stats['api_calls']}")
        print(f"   Кэш хитов: {self.stats['cache_hits']}")
        print(f"   Circuit breaker блоков: {self.stats['circuit_breaker_blocks']}")
        
        total = self.stats['ml_decisions'] + self.stats['api_calls']
        if total > 0:
            ml_pct = (self.stats['ml_decisions'] / total) * 100
            print(f"   ML использование: {ml_pct:.1f}%")
            print(f"   💰 Экономия API: {self.stats['ml_decisions']} запросов!")


# Singleton
_ai_brain_hybrid = None

def get_ai_brain_hybrid() -> AIBrainHybrid:
    """Получить singleton instance"""
    global _ai_brain_hybrid
    if _ai_brain_hybrid is None:
        _ai_brain_hybrid = AIBrainHybrid()
    return _ai_brain_hybrid
