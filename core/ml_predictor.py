"""
ML Predictor для Bybit Trading Bot
Использует обученную LSTM модель для предсказания цен
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import os

# Проверяем доступность TensorFlow
try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Отключаем лишние логи
    import tensorflow as tf
    import joblib
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠️  TensorFlow not available. ML predictions disabled.")

from core.indicators import add_all_indicators


class MLPredictor:
    """ML предсказатель цен"""
    
    def __init__(self, model_path: str = "ml_training/models/bybit_lstm_model.h5",
                 scaler_x_path: str = "ml_training/models/scaler_X.pkl",
                 scaler_y_path: str = "ml_training/models/scaler_y.pkl"):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.model_path = model_path
        self.scaler_x_path = scaler_x_path
        self.scaler_y_path = scaler_y_path
        self.sequence_length = 60
        self.is_loaded = False
        
        # Фичи которые использует модель
        self.features = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
            'atr', 'stoch_k', 'stoch_d', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
        ]
        
    async def load_model(self):
        """Загрузить модель и scalers"""
        if not TF_AVAILABLE:
            print("❌ TensorFlow not available")
            return False
            
        try:
            # Загружаем модель с совместимостью для TensorFlow 2.15+
            try:
                self.model = tf.keras.models.load_model(self.model_path, compile=False)
                print(f"✅ ML Model loaded: {self.model_path}")
            except Exception as e:
                print(f"⚠️  Standard load failed: {e}")
                print(f"   Trying to rebuild model architecture...")
                
                # Пересоздаём модель с правильной архитектурой
                self.model = self._rebuild_model()
                # Загружаем только веса
                self.model.load_weights(self.model_path)
                print(f"✅ Model rebuilt and weights loaded")
            
            # Загружаем scalers
            self.scaler_X = joblib.load(self.scaler_x_path)
            self.scaler_y = joblib.load(self.scaler_y_path)
            print(f"✅ Scalers loaded")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to load ML model: {e}")
            import traceback
            traceback.print_exc()
            self.is_loaded = False
            return False
    
    def _rebuild_model(self):
        """Пересоздание модели с правильной архитектурой для TensorFlow 2.15+"""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
        
        model = Sequential([
            Input(shape=(60, 24)),  # Используем Input вместо batch_shape
            LSTM(128, return_sequences=True),
            Dropout(0.2),
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(1)
        ])
        
        return model
    
    async def predict(
        self,
        symbol: str,
        current_price: float,
        klines: List[Dict]
    ) -> Dict:
        """
        Сделать предсказание
        
        Args:
            symbol: BTCUSDT
            current_price: текущая цена
            klines: последние 60+ свечей
            
        Returns:
            {
                "predicted_price": 43500.0,
                "direction": "UP" | "DOWN" | "SKIP",
                "confidence": 0.85,
                "change_pct": 1.5
            }
        """
        if not self.is_loaded:
            return self._default_prediction()
            
        try:
            # Проверяем что достаточно данных
            if len(klines) < self.sequence_length + 50:  # +50 для индикаторов
                print(f"⚠️  Not enough data: {len(klines)} < {self.sequence_length + 50}")
                return self._default_prediction()
            
            # 1. Подготовка данных
            df = self._prepare_features(klines)
            
            # Проверяем что после очистки NaN достаточно данных
            if len(df) < self.sequence_length:
                print(f"⚠️  Not enough data after cleaning: {len(df)} < {self.sequence_length}")
                return self._default_prediction()
            
            # 2. Выбираем только нужные фичи
            X = df[self.features].values
            
            # 3. Нормализация
            X_scaled = self.scaler_X.transform(X)
            
            # 4. Берём последние 60 timesteps
            X_seq = X_scaled[-self.sequence_length:].reshape(1, self.sequence_length, len(self.features))
            
            # 5. Предсказание
            pred_scaled = self.model.predict(X_seq, verbose=0)
            predicted_price = self.scaler_y.inverse_transform(pred_scaled)[0][0]
            
            # 6. Расчет метрик
            change_pct = ((predicted_price - current_price) / current_price) * 100
            
            if abs(change_pct) < 0.5:
                direction = "SKIP"  # Слишком маленькое изменение
            elif predicted_price > current_price:
                direction = "UP"
            else:
                direction = "DOWN"
            
            confidence = self._calculate_confidence(change_pct)
            
            return {
                "predicted_price": float(predicted_price),
                "direction": direction,
                "confidence": float(confidence),
                "change_pct": float(change_pct)
            }
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return self._default_prediction()
    
    def _prepare_features(self, klines: List[Dict]) -> pd.DataFrame:
        """Подготовить фичи (индикаторы + временные)"""
        # Конвертируем в DataFrame
        df = pd.DataFrame(klines)
        
        # Добавляем технические индикаторы
        df = add_all_indicators(df)
        
        # Добавляем временные фичи
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        
        # Циклические фичи
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Удаляем NaN
        df = df.dropna()
        
        return df
        
    def _calculate_confidence(self, change_pct: float) -> float:
        """Рассчитать уверенность на основе изменения"""
        # Чем больше изменение, тем выше уверенность (но не больше 0.95)
        confidence = min(abs(change_pct) / 5.0, 0.95)
        return max(confidence, 0.3)  # Минимум 0.3
        
    def _default_prediction(self) -> Dict:
        """Дефолтное предсказание если модель не загружена"""
        return {
            "predicted_price": 0.0,
            "direction": "SKIP",
            "confidence": 0.0,
            "change_pct": 0.0
        }


# Singleton
_ml_predictor = None

def get_ml_predictor() -> MLPredictor:
    """Получить singleton instance"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLPredictor()
    return _ml_predictor
