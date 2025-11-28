"""
ML Service v2.0 - Оптимизированный сервис машинного обучения
МОДУЛЬ 1: Оптимизация "Мозга" и Памяти (Critical Performance)

Особенности:
- Singleton Pattern: модель загружается ОДИН раз при старте
- TFLite Runtime: опциональная поддержка для слабых VPS
- Garbage Collection: очистка памяти после каждого предсказания
- Кэширование: предсказания кэшируются на короткий период
"""
import gc
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading

# Отключаем лишние логи TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Проверяем доступность библиотек
TF_AVAILABLE = False
TFLITE_AVAILABLE = False
JOBLIB_AVAILABLE = False

try:
    import tensorflow as tf
    # Оптимизация памяти TensorFlow
    tf.get_logger().setLevel('ERROR')
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    TF_AVAILABLE = True
except ImportError:
    pass

try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    pass

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    pass

from core.indicators import add_all_indicators


class MLService:
    """
    Оптимизированный ML сервис с кэшированием модели
    
    Singleton Pattern: модель загружается в память ОДИН раз
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - гарантируем один экземпляр"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Инициализация (вызывается только один раз)"""
        if self._initialized:
            return
        
        self._initialized = True
        
        # Пути к моделям
        self.model_h5_path = "ml_training/models/bybit_lstm_model_v2.h5"
        self.model_tflite_path = "ml_training/models/bybit_lstm_model_v2.tflite"
        self.model_joblib_path = "ml_training/models/bybit_model.joblib"
        self.scaler_x_path = "ml_training/models/scaler_X_v2.pkl"
        self.scaler_y_path = "ml_training/models/scaler_y_v2.pkl"
        
        # Модель и скейлеры (загружаются один раз!)
        self.model = None
        self.interpreter = None  # TFLite interpreter
        self.scaler_X = None
        self.scaler_y = None
        self.is_loaded = False
        self.model_type = None  # 'keras', 'tflite', 'joblib'
        
        # Параметры модели
        self.sequence_length = 60
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
        
        # Кэш предсказаний (для экономии ресурсов)
        self._prediction_cache: Dict[str, Dict] = {}
        self._cache_ttl = 30  # 30 секунд
        
        # Статистика
        self.stats = {
            'predictions_made': 0,
            'cache_hits': 0,
            'gc_collections': 0,
            'load_time_ms': 0,
            'avg_prediction_time_ms': 0,
            'total_prediction_time_ms': 0
        }
        
        print(f"🤖 MLService v2.0 initialized (Singleton)")
        print(f"   TensorFlow: {'✅' if TF_AVAILABLE else '❌'}")
        print(f"   TFLite Runtime: {'✅' if TFLITE_AVAILABLE else '❌'}")
        print(f"   Joblib: {'✅' if JOBLIB_AVAILABLE else '❌'}")
    
    async def load_model(self) -> bool:
        """
        Загрузить модель в память (вызывается ОДИН раз при старте)
        
        Приоритет загрузки:
        1. TFLite (если доступен) - самый быстрый и легкий
        2. Keras H5 - стандартный
        3. Joblib - fallback
        """
        if self.is_loaded:
            print(f"✅ Model already loaded ({self.model_type})")
            return True
        
        start_time = datetime.now()
        
        try:
            # Загружаем скейлеры (нужны для всех типов моделей)
            if JOBLIB_AVAILABLE and os.path.exists(self.scaler_x_path):
                self.scaler_X = joblib.load(self.scaler_x_path)
                self.scaler_y = joblib.load(self.scaler_y_path)
                print(f"✅ Scalers loaded")
            else:
                print(f"⚠️  Scalers not found, predictions may be inaccurate")
            
            # Приоритет 1: TFLite (быстрее и легче)
            if TFLITE_AVAILABLE and os.path.exists(self.model_tflite_path):
                self.interpreter = tflite.Interpreter(model_path=self.model_tflite_path)
                self.interpreter.allocate_tensors()
                self.model_type = 'tflite'
                self.is_loaded = True
                print(f"✅ TFLite model loaded: {self.model_tflite_path}")
            
            # Приоритет 2: Keras H5
            elif TF_AVAILABLE and os.path.exists(self.model_h5_path):
                # Оптимизированная загрузка без компиляции
                self.model = tf.keras.models.load_model(
                    self.model_h5_path, 
                    compile=False
                )
                self.model_type = 'keras'
                self.is_loaded = True
                print(f"✅ Keras model loaded: {self.model_h5_path}")
            
            # Приоритет 3: Joblib (sklearn модель)
            elif JOBLIB_AVAILABLE and os.path.exists(self.model_joblib_path):
                self.model = joblib.load(self.model_joblib_path)
                self.model_type = 'joblib'
                self.is_loaded = True
                print(f"✅ Joblib model loaded: {self.model_joblib_path}")
            
            else:
                print(f"❌ No model files found!")
                return False
            
            # Записываем время загрузки
            load_time = (datetime.now() - start_time).total_seconds() * 1000
            self.stats['load_time_ms'] = load_time
            print(f"   Load time: {load_time:.0f}ms")
            
            # Очищаем память после загрузки
            gc.collect()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def predict(
        self,
        symbol: str,
        current_price: float,
        klines: List[Dict]
    ) -> Dict:
        """
        Сделать предсказание с кэшированием и очисткой памяти
        
        Args:
            symbol: BTCUSDT
            current_price: текущая цена
            klines: последние 60+ свечей
            
        Returns:
            {
                "predicted_change_pct": 0.5,
                "direction": "UP" | "DOWN" | "SKIP",
                "confidence": 0.75,
                "predicted_price": 91500.0
            }
        """
        start_time = datetime.now()
        
        # Проверяем кэш
        cache_key = f"{symbol}_{current_price:.2f}"
        if cache_key in self._prediction_cache:
            cached = self._prediction_cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(seconds=self._cache_ttl):
                self.stats['cache_hits'] += 1
                return cached['prediction']
        
        # Проверяем загружена ли модель
        if not self.is_loaded:
            loaded = await self.load_model()
            if not loaded:
                return self._default_prediction()
        
        try:
            # Проверяем данные
            if len(klines) < self.sequence_length + 50:
                return self._default_prediction()
            
            # Подготовка фичей
            df = self._prepare_features(klines)
            
            if len(df) < self.sequence_length:
                return self._default_prediction()
            
            # Выбираем фичи
            X = df[self.features].values
            X_seq = X[-self.sequence_length:]
            
            # Нормализация
            if self.scaler_X is not None:
                X_scaled = self.scaler_X.transform(X_seq)
            else:
                X_scaled = X_seq
            
            # Предсказание в зависимости от типа модели
            if self.model_type == 'tflite':
                predicted_change_pct = self._predict_tflite(X_scaled)
            elif self.model_type == 'keras':
                predicted_change_pct = self._predict_keras(X_scaled)
            elif self.model_type == 'joblib':
                predicted_change_pct = self._predict_joblib(X_scaled)
            else:
                return self._default_prediction()
            
            # Валидация предсказания
            if abs(predicted_change_pct) > 10:
                print(f"⚠️  Unrealistic prediction: {predicted_change_pct:.2f}%")
                return self._default_prediction()
            
            # Определяем направление
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
            
            result = {
                "predicted_change_pct": float(predicted_change_pct),
                "direction": direction,
                "confidence": float(confidence),
                "predicted_price": float(predicted_price),
                "change_pct": float(predicted_change_pct),
                "model_type": self.model_type
            }
            
            # Кэшируем результат
            self._prediction_cache[cache_key] = {
                'timestamp': datetime.now(),
                'prediction': result
            }
            
            # Обновляем статистику
            prediction_time = (datetime.now() - start_time).total_seconds() * 1000
            self.stats['predictions_made'] += 1
            self.stats['total_prediction_time_ms'] += prediction_time
            self.stats['avg_prediction_time_ms'] = (
                self.stats['total_prediction_time_ms'] / self.stats['predictions_made']
            )
            
            # Garbage Collection после предсказания
            gc.collect()
            self.stats['gc_collections'] += 1
            
            return result
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            gc.collect()
            return self._default_prediction()
    
    def _predict_tflite(self, X_scaled: np.ndarray) -> float:
        """Предсказание через TFLite (самый быстрый)"""
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()
        
        # Подготовка входных данных
        X_input = X_scaled.reshape(1, self.sequence_length, len(self.features))
        X_input = X_input.astype(np.float32)
        
        self.interpreter.set_tensor(input_details[0]['index'], X_input)
        self.interpreter.invoke()
        
        pred_scaled = self.interpreter.get_tensor(output_details[0]['index'])
        
        if self.scaler_y is not None:
            predicted_change_pct = self.scaler_y.inverse_transform(pred_scaled)[0][0] * 100
        else:
            predicted_change_pct = pred_scaled[0][0] * 100
        
        return float(predicted_change_pct)
    
    def _predict_keras(self, X_scaled: np.ndarray) -> float:
        """Предсказание через Keras"""
        X_input = X_scaled.reshape(1, self.sequence_length, len(self.features))
        
        pred_scaled = self.model.predict(X_input, verbose=0)
        
        if self.scaler_y is not None:
            predicted_change_pct = self.scaler_y.inverse_transform(pred_scaled)[0][0] * 100
        else:
            predicted_change_pct = pred_scaled[0][0] * 100
        
        return float(predicted_change_pct)
    
    def _predict_joblib(self, X_scaled: np.ndarray) -> float:
        """Предсказание через sklearn/joblib модель"""
        # Для sklearn моделей обычно нужен 2D input
        X_input = X_scaled.reshape(1, -1)
        
        pred = self.model.predict(X_input)
        
        if self.scaler_y is not None:
            predicted_change_pct = self.scaler_y.inverse_transform(pred.reshape(-1, 1))[0][0] * 100
        else:
            predicted_change_pct = pred[0] * 100
        
        return float(predicted_change_pct)
    
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
        """Дефолтное предсказание"""
        return {
            "predicted_change_pct": 0.0,
            "direction": "SKIP",
            "confidence": 0.0,
            "predicted_price": 0.0,
            "change_pct": 0.0,
            "model_type": None
        }
    
    def clear_cache(self):
        """Очистить кэш предсказаний"""
        self._prediction_cache.clear()
        gc.collect()
        print(f"🧹 Prediction cache cleared")
    
    def print_stats(self):
        """Вывести статистику"""
        print(f"🤖 MLService v2.0 Statistics:")
        print(f"   Model Type: {self.model_type or 'Not loaded'}")
        print(f"   Is Loaded: {'✅' if self.is_loaded else '❌'}")
        print(f"   Load Time: {self.stats['load_time_ms']:.0f}ms")
        print(f"   Predictions Made: {self.stats['predictions_made']}")
        print(f"   Cache Hits: {self.stats['cache_hits']}")
        print(f"   Avg Prediction Time: {self.stats['avg_prediction_time_ms']:.1f}ms")
        print(f"   GC Collections: {self.stats['gc_collections']}")


# Singleton accessor
_ml_service = None

def get_ml_service() -> MLService:
    """Получить singleton instance MLService"""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service
