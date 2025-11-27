"""
ML Service - Локальный инференс обученной модели
Загружает trained_model.joblib и делает предсказания
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime


class MLPredictor:
    """
    Предиктор на основе обученной ML модели (RandomForest/XGBoost)
    
    Загружает модель из ml_data/trained_model.joblib
    Делает предсказания: BUY (1), SELL (-1), HOLD (0)
    """
    
    def __init__(self, model_path: str = "ml_data/trained_model.joblib"):
        self.model_path = model_path
        self.scaler_path = model_path.replace('.joblib', '_scaler.joblib')
        
        self.model = None
        self.scaler = None
        self.is_loaded = False
        
        # Фичи которые ожидает модель (должны совпадать с обучением!)
        self.feature_names = [
            'rsi',
            'macd_value',
            'macd_signal',
            'macd_histogram',
            'bb_upper',
            'bb_middle',
            'bb_lower',
            'bb_width',
            'ema_20',
            'ema_50',
            'volume_sma',
            'price_change_pct',
            'volatility'
        ]
        
        # Статистика
        self.stats = {
            'total_predictions': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'avg_confidence': 0.0
        }
    
    def load_model(self) -> bool:
        """
        Загрузить модель и scaler
        
        Returns:
            True если загрузка успешна
        """
        try:
            import joblib
            
            if not os.path.exists(self.model_path):
                print(f"⚠️  ML model not found: {self.model_path}")
                return False
            
            # Загружаем модель
            self.model = joblib.load(self.model_path)
            print(f"✅ ML model loaded: {self.model_path}")
            
            # Загружаем scaler (если есть)
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                print(f"✅ Scaler loaded: {self.scaler_path}")
            else:
                print(f"⚠️  Scaler not found, using raw features")
            
            self.is_loaded = True
            return True
        
        except Exception as e:
            print(f"❌ Failed to load ML model: {e}")
            self.is_loaded = False
            return False
    
    def _prepare_features(self, market_data: Dict) -> Optional[pd.DataFrame]:
        """
        Подготовить фичи для модели
        
        Args:
            market_data: Данные рынка с индикаторами
        
        Returns:
            DataFrame с фичами или None при ошибке
        """
        try:
            # Извлекаем данные
            price = market_data.get('price', 0)
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', {})
            bb = market_data.get('bollinger_bands', {})
            
            # Формируем фичи
            features = {
                'rsi': rsi,
                'macd_value': macd.get('value', 0),
                'macd_signal': macd.get('signal', 0),
                'macd_histogram': macd.get('histogram', 0),
                'bb_upper': bb.get('upper', price * 1.02),
                'bb_middle': bb.get('middle', price),
                'bb_lower': bb.get('lower', price * 0.98),
                'bb_width': (bb.get('upper', 0) - bb.get('lower', 0)) / price if price > 0 else 0,
                'ema_20': market_data.get('ema_20', price),
                'ema_50': market_data.get('ema_50', price),
                'volume_sma': market_data.get('volume_sma', 0),
                'price_change_pct': market_data.get('price_change_pct', 0),
                'volatility': market_data.get('volatility', 0)
            }
            
            # Создаем DataFrame
            df = pd.DataFrame([features])
            
            # Применяем scaler если есть
            if self.scaler is not None:
                df_scaled = self.scaler.transform(df)
                df = pd.DataFrame(df_scaled, columns=df.columns)
            
            return df
        
        except Exception as e:
            print(f"❌ Error preparing features: {e}")
            return None
    
    def predict(self, market_data: Dict) -> Dict:
        """
        Сделать предсказание
        
        Args:
            market_data: Данные рынка с индикаторами
        
        Returns:
            {
                'signal': 1 (BUY), -1 (SELL), 0 (HOLD),
                'decision': 'BUY' / 'SELL' / 'HOLD',
                'confidence': 0.0 - 1.0,
                'probabilities': {'buy': 0.x, 'sell': 0.x, 'hold': 0.x}
            }
        """
        # Если модель не загружена - возвращаем HOLD
        if not self.is_loaded:
            return {
                'signal': 0,
                'decision': 'HOLD',
                'confidence': 0.0,
                'probabilities': {'buy': 0.33, 'sell': 0.33, 'hold': 0.34},
                'error': 'Model not loaded'
            }
        
        try:
            # Подготавливаем фичи
            features = self._prepare_features(market_data)
            
            if features is None:
                return {
                    'signal': 0,
                    'decision': 'HOLD',
                    'confidence': 0.0,
                    'probabilities': {'buy': 0.33, 'sell': 0.33, 'hold': 0.34},
                    'error': 'Feature preparation failed'
                }
            
            # Предсказание
            prediction = self.model.predict(features)[0]
            
            # Вероятности (если модель поддерживает)
            probabilities = {'buy': 0.33, 'sell': 0.33, 'hold': 0.34}
            confidence = 0.5
            
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features)[0]
                
                # Определяем порядок классов
                classes = self.model.classes_
                for i, cls in enumerate(classes):
                    if cls == 1:
                        probabilities['buy'] = proba[i]
                    elif cls == -1:
                        probabilities['sell'] = proba[i]
                    else:
                        probabilities['hold'] = proba[i]
                
                # Confidence = максимальная вероятность
                confidence = max(proba)
            
            # Конвертируем в решение
            if prediction == 1:
                decision = 'BUY'
                self.stats['buy_signals'] += 1
            elif prediction == -1:
                decision = 'SELL'
                self.stats['sell_signals'] += 1
            else:
                decision = 'HOLD'
                self.stats['hold_signals'] += 1
            
            # Обновляем статистику
            self.stats['total_predictions'] += 1
            self.stats['avg_confidence'] = (
                (self.stats['avg_confidence'] * (self.stats['total_predictions'] - 1) + confidence)
                / self.stats['total_predictions']
            )
            
            return {
                'signal': int(prediction),
                'decision': decision,
                'confidence': confidence,
                'probabilities': probabilities
            }
        
        except Exception as e:
            print(f"❌ ML prediction error: {e}")
            return {
                'signal': 0,
                'decision': 'HOLD',
                'confidence': 0.0,
                'probabilities': {'buy': 0.33, 'sell': 0.33, 'hold': 0.34},
                'error': str(e)
            }

    def print_stats(self):
        """Вывести статистику"""
        total = self.stats['total_predictions']
        if total == 0:
            print("📊 ML Service: No predictions yet")
            return
        
        print(f"📊 ML Service Statistics:")
        print(f"   Total Predictions: {total}")
        print(f"   BUY signals: {self.stats['buy_signals']} ({self.stats['buy_signals']/total*100:.1f}%)")
        print(f"   SELL signals: {self.stats['sell_signals']} ({self.stats['sell_signals']/total*100:.1f}%)")
        print(f"   HOLD signals: {self.stats['hold_signals']} ({self.stats['hold_signals']/total*100:.1f}%)")
        print(f"   Avg Confidence: {self.stats['avg_confidence']:.1%}")


# Singleton
_ml_service = None

def get_ml_service() -> MLPredictor:
    """Получить singleton instance"""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLPredictor()
        _ml_service.load_model()
    return _ml_service
