"""
ML Predictor v2 для Bybit Trading Bot
Предсказывает % изменение цены (не абсолютную цену)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import os

try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import tensorflow as tf
    import joblib
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️  TensorFlow not available")

from core.indicators import add_all_indicators


class MLPredictorV2:
    """ML предсказатель v2 - предсказывает % изменение"""
    
    def __init__(self, model_path: str = "ml_training/models/bybit_lstm_model_v2.h5",
                 scaler_x_path: str = "ml_training/models/scaler_X_v2.pkl",
                 scaler_y_path: str = "ml_training/models/scaler_y_v2.pkl"):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.model_path = model_path
        self.scaler_x_path = scaler_x_path
        self.scaler_y_path = scaler_y_path
        self.sequence_length = 60
        self.is_loaded = False
        
        # Фичи v2 - нормализованные относительно цены
        self.features = [
            'open_norm', 'high_norm', 'low_norm',
            'rsi_norm',
            'macd_norm', 'macd_signal_norm', 'macd_hist_norm',
            'bb_upper_norm', 'bb_lower_norm', 'bb_width',
            'sma20_norm', 'sma50_norm', 'ema12_norm', 'ema26_norm',
            'atr_norm',
            'stoch_k_norm', 'stoch_d_norm',
            'volume_log',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
        ]
        
    async def load_model(self):
        """Загрузить модель"""
        if not TF_AVAILABLE:
            return False
            
        try:
            self.model = tf.keras.models.load_model(self.model_path, compile=False)
            self.scaler_X = joblib.load(self.scaler_x_path)
            self.scaler_y = joblib.load(self.scaler_y_path)
            self.is_loaded = True
            print(f"✅ ML Model v2 loaded: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load ML model v2: {e}")
            self.is_loaded = False
            return False
    
    async def predict(self, symbol: str, current_price: float, klines: List[Dict]) -> Dict:
        """
        Предсказать % изменение цены
        
        Returns:
            {
                "predicted_change_pct": 0.5,  # +0.5%
                "direction": "UP" | "DOWN" | "SKIP",
                "confidence": 0.75,
                "predicted_price": 91500.0
            }
        """
        if not self.is_loaded:
            return self._default_prediction()
            
        try:
            if len(klines) < self.sequence_length + 50:
                return self._default_prediction()
            
            # Подготовка фичей
            df = self._prepare_features(klines)
            
            if len(df) < self.sequence_length:
                return self._default_prediction()
            
            # Выбираем фичи
            X = df[self.features].values
            
            # Берём последние 60
            X_seq = X[-self.sequence_length:]
            
            # Нормализация
            X_scaled = self.scaler_X.transform(X_seq)
            X_input = X_scaled.reshape(1, self.sequence_length, len(self.features))
            
            # Предсказание
            pred_scaled = self.model.predict(X_input, verbose=0)
            predicted_change_pct = self.scaler_y.inverse_transform(pred_scaled)[0][0] * 100
            
            # Валидация - если предсказание нереальное, возвращаем дефолт
            if abs(predicted_change_pct) > 10:  # >10% за час - нереально
                print(f"⚠️  Unrealistic prediction: {predicted_change_pct:.2f}%, using default")
                return self._default_prediction()
            
            # Направление
            if abs(predicted_change_pct) < 0.3:
                direction = "SKIP"
            elif predicted_change_pct > 0:
                direction = "UP"
            else:
                direction = "DOWN"
            
            # Уверенность
            confidence = min(abs(predicted_change_pct) / 2.0, 0.95)
            confidence = max(confidence, 0.3)
            
            # Предсказанная цена
            predicted_price = current_price * (1 + predicted_change_pct / 100)
            
            return {
                "predicted_change_pct": float(predicted_change_pct),
                "direction": direction,
                "confidence": float(confidence),
                "predicted_price": float(predicted_price),
                "change_pct": float(predicted_change_pct)  # для совместимости
            }
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return self._default_prediction()
    
    def _prepare_features(self, klines: List[Dict]) -> pd.DataFrame:
        """Подготовить нормализованные фичи"""
        df = pd.DataFrame(klines)
        
        # Добавляем индикаторы
        df = add_all_indicators(df)
        
        # Нормализуем относительно close
        df['open_norm'] = (df['open'] - df['close']) / df['close']
        df['high_norm'] = (df['high'] - df['close']) / df['close']
        df['low_norm'] = (df['low'] - df['close']) / df['close']
        
        df['bb_upper_norm'] = (df['bb_upper'] - df['close']) / df['close']
        df['bb_lower_norm'] = (df['bb_lower'] - df['close']) / df['close']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']
        
        df['sma20_norm'] = (df['sma_20'] - df['close']) / df['close']
        df['sma50_norm'] = (df['sma_50'] - df['close']) / df['close']
        df['ema12_norm'] = (df['ema_12'] - df['close']) / df['close']
        df['ema26_norm'] = (df['ema_26'] - df['close']) / df['close']
        
        df['rsi_norm'] = df['rsi'] / 100.0
        
        df['macd_norm'] = df['macd'] / df['close']
        df['macd_signal_norm'] = df['macd_signal'] / df['close']
        df['macd_hist_norm'] = df['macd_histogram'] / df['close']
        
        df['atr_norm'] = df['atr'] / df['close']
        
        df['stoch_k_norm'] = df['stoch_k'] / 100.0
        df['stoch_d_norm'] = df['stoch_d'] / 100.0
        
        df['volume_log'] = np.log1p(df['volume'])
        
        # Временные фичи
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        df = df.dropna()
        return df
        
    def _default_prediction(self) -> Dict:
        return {
            "predicted_change_pct": 0.0,
            "direction": "SKIP",
            "confidence": 0.0,
            "predicted_price": 0.0,
            "change_pct": 0.0
        }


# Singleton
_predictor_v2 = None

def get_ml_predictor_v2() -> MLPredictorV2:
    global _predictor_v2
    if _predictor_v2 is None:
        _predictor_v2 = MLPredictorV2()
    return _predictor_v2
