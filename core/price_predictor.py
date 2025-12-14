"""
ML модель для предсказания цен (LSTM)
Использует только numpy и pandas (без TensorFlow/PyTorch для простоты)
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict
from database.models import Candle


class SimplePricePredictor:
    """
    Простой предсказатель цен на основе скользящих средних и трендов
    (без тяжелых ML библиотек)
    """
    
    def __init__(self, lookback: int = 60):
        self.lookback = lookback
    
    def prepare_features(self, candles: List[Candle]) -> pd.DataFrame:
        """
        Подготовить фичи из свечей
        
        Returns:
            DataFrame с фичами
        """
        if len(candles) < self.lookback:
            return pd.DataFrame()
        
        data = {
            'close': [c.close for c in candles],
            'high': [c.high for c in candles],
            'low': [c.low for c in candles],
            'volume': [c.volume for c in candles]
        }
        
        df = pd.DataFrame(data)
        
        # Технические индикаторы как фичи
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volatility
        df['volatility'] = df['close'].rolling(window=20).std()
        
        # Price change
        df['price_change'] = df['close'].pct_change()
        
        # Volume change
        df['volume_change'] = df['volume'].pct_change()
        
        # Удаляем NaN
        df = df.dropna()
        
        return df
    
    def predict_direction(self, candles: List[Candle]) -> Tuple[str, float]:
        """
        Предсказать направление цены
        
        Returns:
            (direction, confidence)
            direction: "UP", "DOWN", "NEUTRAL"
            confidence: 0.0-1.0
        """
        if len(candles) < self.lookback:
            return "NEUTRAL", 0.0
        
        df = self.prepare_features(candles)
        
        if df.empty:
            return "NEUTRAL", 0.0
        
        # Берем последние данные
        latest = df.iloc[-1]
        
        # Простая логика на основе индикаторов
        signals = []
        
        # 1. Тренд по скользящим средним
        if latest['sma_5'] > latest['sma_10'] > latest['sma_20']:
            signals.append(1)  # Uptrend
        elif latest['sma_5'] < latest['sma_10'] < latest['sma_20']:
            signals.append(-1)  # Downtrend
        else:
            signals.append(0)
        
        # 2. EMA crossover
        if latest['ema_5'] > latest['ema_10']:
            signals.append(1)
        else:
            signals.append(-1)
        
        # 3. RSI
        if latest['rsi'] < 30:
            signals.append(1)  # Oversold -> UP
        elif latest['rsi'] > 70:
            signals.append(-1)  # Overbought -> DOWN
        else:
            signals.append(0)
        
        # 4. Momentum
        if latest['price_change'] > 0.001:  # >0.1%
            signals.append(1)
        elif latest['price_change'] < -0.001:
            signals.append(-1)
        else:
            signals.append(0)
        
        # Агрегируем сигналы
        avg_signal = np.mean(signals)
        
        if avg_signal > 0.3:
            direction = "UP"
            confidence = min(abs(avg_signal), 1.0)
        elif avg_signal < -0.3:
            direction = "DOWN"
            confidence = min(abs(avg_signal), 1.0)
        else:
            direction = "NEUTRAL"
            confidence = 0.5
        
        return direction, confidence
    
    def predict_price(self, candles: List[Candle], horizon: int = 5) -> Optional[float]:
        """
        Предсказать цену через N минут
        
        Args:
            candles: исторические свечи
            horizon: горизонт предсказания (минут)
        
        Returns:
            Предсказанная цена
        """
        if len(candles) < self.lookback:
            return None
        
        df = self.prepare_features(candles)
        
        if df.empty:
            return None
        
        # Простое предсказание на основе тренда
        recent_prices = df['close'].tail(20).values
        
        # Linear regression (простая)
        x = np.arange(len(recent_prices))
        coeffs = np.polyfit(x, recent_prices, 1)
        
        # Предсказываем
        predicted_price = coeffs[0] * (len(recent_prices) + horizon) + coeffs[1]
        
        return float(predicted_price)
    
    def get_prediction_summary(self, candles: List[Candle]) -> Dict:
        """
        Полная сводка предсказаний
        
        Returns:
            {
                "direction": "UP/DOWN/NEUTRAL",
                "confidence": 0.0-1.0,
                "predicted_price_5m": float,
                "predicted_price_15m": float,
                "current_price": float
            }
        """
        if len(candles) < self.lookback:
            return {
                "error": "Not enough data",
                "current_price": candles[-1].close if candles else 0.0
            }
        
        direction, confidence = self.predict_direction(candles)
        price_5m = self.predict_price(candles, horizon=5)
        price_15m = self.predict_price(candles, horizon=15)
        current_price = candles[-1].close
        
        return {
            "direction": direction,
            "confidence": confidence,
            "predicted_price_5m": price_5m,
            "predicted_price_15m": price_15m,
            "current_price": current_price,
            "change_5m_pct": ((price_5m - current_price) / current_price * 100) if price_5m else 0.0,
            "change_15m_pct": ((price_15m - current_price) / current_price * 100) if price_15m else 0.0
        }


# Singleton
_price_predictor = None

def get_price_predictor():
    """Получить singleton instance - использует MLPredictor если доступен"""
    global _price_predictor
    if _price_predictor is None:
        # Пробуем использовать ML модель
        try:
            from core.ml_predictor import MLPredictor
            _price_predictor = MLPredictor()
            print("🤖 Using MLPredictor (LSTM model)")
        except Exception as e:
            print(f"⚠️  MLPredictor not available: {e}")
            print("   Falling back to SimplePricePredictor")
            _price_predictor = SimplePricePredictor()
    return _price_predictor
