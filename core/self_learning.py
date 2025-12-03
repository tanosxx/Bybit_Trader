"""
Self-Learning Module - Online Learning с River

Система самообучения на основе результатов реальных сделок:
1. При входе: собираем фичи рынка
2. При выходе: учимся на результате (Win/Loss)
3. Постоянное улучшение предсказаний

КРИТИЧНО: Graceful degradation - если модуль падает, бот продолжает работать!
"""
import os
import pickle
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

try:
    from river import forest, metrics
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    print("⚠️ River not installed. Self-learning disabled. Install: pip install river")


class SelfLearner:
    """
    Online Learning система на базе River
    
    Использует Adaptive Random Forest для классификации:
    - Input: market features (RSI, volatility, trend, etc.)
    - Output: probability of success (0-1)
    
    Graceful Failure: если что-то сломается, возвращаем нейтральный 0.5
    """
    
    def __init__(self, model_path: str = "ml_data/self_learner.pkl"):
        self.model_path = model_path
        self.model = None
        self.metric = None
        self.enabled = RIVER_AVAILABLE
        
        # Статистика
        self.predictions_count = 0
        self.learning_count = 0
        self.wins = 0
        self.losses = 0
        
        if not self.enabled:
            print("❌ SelfLearner: River not available, module disabled")
            return
        
        # Создаем директорию если нужно
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем или создаем модель
        self._load_or_create_model()
        
        print(f"🧠 SelfLearner initialized:")
        print(f"   Model: {model_path}")
        print(f"   Status: {'✅ Active' if self.enabled else '❌ Disabled'}")
    
    def _load_or_create_model(self):
        """Загрузить модель из файла или создать новую"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get('model')
                    self.metric = data.get('metric')
                    self.predictions_count = data.get('predictions_count', 0)
                    self.learning_count = data.get('learning_count', 0)
                    self.wins = data.get('wins', 0)
                    self.losses = data.get('losses', 0)
                print(f"   ✅ Loaded model: {self.learning_count} samples learned")
                print(f"   Model type: {type(self.model)}")
            else:
                # Создаем новую модель
                self.model = forest.ARFClassifier(
                    n_models=10,
                    max_features='sqrt',
                    lambda_value=6,
                    grace_period=50,
                    seed=42
                )
                self.metric = metrics.Accuracy()
                print(f"   ✅ Created new model")
                print(f"   Model type: {type(self.model)}")
        
        except Exception as e:
            print(f"   ⚠️ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            # Создаем новую модель в случае ошибки
            self.model = forest.ARFClassifier(
                n_models=10,
                max_features='sqrt',
                lambda_value=6,
                grace_period=50,
                seed=42
            )
            self.metric = metrics.Accuracy()
            print(f"   Model type after error: {type(self.model)}")
    
    def _save_model(self):
        """Сохранить модель в файл"""
        if not self.enabled or self.model is None:
            print(f"⚠️ SelfLearner: Cannot save - enabled={self.enabled}, model={self.model is not None}")
            return
        
        try:
            data = {
                'model': self.model,
                'metric': self.metric,
                'predictions_count': self.predictions_count,
                'learning_count': self.learning_count,
                'wins': self.wins,
                'losses': self.losses,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(data, f)
            
            print(f"✅ SelfLearner: Model saved to {self.model_path}")
        
        except Exception as e:
            print(f"⚠️ SelfLearner: Error saving model: {e}")
            import traceback
            traceback.print_exc()
    
    def extract_features(self, technical: Dict, news_score: float = 0.0, 
                        ml_confidence: float = 0.5) -> Dict:
        """
        Извлечь фичи из рыночных данных
        
        Args:
            technical: данные технического анализа
            news_score: sentiment score от news brain
            ml_confidence: confidence от ML модели
        
        Returns:
            Dict с нормализованными фичами
        """
        try:
            # Базовые индикаторы
            rsi = technical.get('rsi', 50.0)
            
            # MACD
            macd_trend = technical.get('macd', {}).get('trend', 'neutral')
            macd_bullish = 1.0 if macd_trend == 'bullish' else 0.0
            
            # Bollinger Bands
            bb_position = technical.get('bb', {}).get('position', 'within_bands')
            bb_upper = 1.0 if bb_position == 'above_upper' else 0.0
            bb_lower = 1.0 if bb_position == 'below_lower' else 0.0
            
            # Trend
            trend = technical.get('trend', {}).get('direction', 'neutral')
            trend_strength = technical.get('trend', {}).get('strength', 0.0)
            trend_up = 1.0 if 'up' in trend else 0.0
            
            # Volatility
            volatility = technical.get('volatility', 0.0)
            
            # Volume
            volume_ratio = technical.get('volume_ratio', 1.0)
            
            features = {
                'rsi': float(rsi),
                'macd_bullish': float(macd_bullish),
                'bb_upper': float(bb_upper),
                'bb_lower': float(bb_lower),
                'trend_up': float(trend_up),
                'trend_strength': float(trend_strength),
                'volatility': float(volatility),
                'volume_ratio': float(volume_ratio),
                'news_score': float(news_score),
                'ml_confidence': float(ml_confidence)
            }
            
            return features
        
        except Exception as e:
            print(f"⚠️ SelfLearner: Error extracting features: {e}")
            # Возвращаем нейтральные фичи
            return {
                'rsi': 50.0,
                'macd_bullish': 0.0,
                'bb_upper': 0.0,
                'bb_lower': 0.0,
                'trend_up': 0.0,
                'trend_strength': 0.0,
                'volatility': 0.0,
                'volume_ratio': 1.0,
                'news_score': 0.0,
                'ml_confidence': 0.5
            }
    
    def predict(self, features: Dict) -> Tuple[float, float]:
        """
        Предсказать вероятность успеха сделки
        
        Args:
            features: словарь с фичами
        
        Returns:
            (probability, confidence) - вероятность успеха и уверенность
        
        Graceful Failure: возвращает (0.5, 0.0) при ошибке
        """
        if not self.enabled or not self.model:
            return 0.5, 0.0  # Нейтральный результат
        
        try:
            # Если модель еще не обучена (< 50 samples), возвращаем нейтральный
            if self.learning_count < 50:
                return 0.5, 0.0
            
            # Предсказание
            proba = self.model.predict_proba_one(features)
            
            # Вероятность класса 1 (Win)
            win_proba = proba.get(1, 0.5)
            
            # Confidence = разница между вероятностями
            confidence = abs(proba.get(1, 0.5) - proba.get(0, 0.5))
            
            self.predictions_count += 1
            
            return float(win_proba), float(confidence)
        
        except Exception as e:
            print(f"⚠️ SelfLearner: Prediction error: {e}")
            return 0.5, 0.0  # Нейтральный результат при ошибке
    
    def learn(self, features: Dict, result: int) -> bool:
        """
        Обучить модель на результате сделки
        
        Args:
            features: фичи при входе в сделку
            result: 1 = Win (TP), 0 = Loss (SL)
        
        Returns:
            True если обучение прошло успешно
        
        Graceful Failure: возвращает False при ошибке, но не крашит
        """
        if not self.enabled:
            print(f"⚠️ SelfLearner: Not enabled")
            return False
        
        if self.model is None:
            print(f"⚠️ SelfLearner: No model")
            return False
        
        try:
            # Обучаем модель
            self.model.learn_one(features, result)
            
            # Обновляем метрику
            if self.metric:
                # Делаем предсказание для метрики
                y_pred = self.model.predict_one(features)
                self.metric.update(result, y_pred)
            
            # Статистика
            self.learning_count += 1
            if result == 1:
                self.wins += 1
            else:
                self.losses += 1
            
            # Сохраняем модель каждые 10 обучений
            if self.learning_count % 10 == 0:
                self._save_model()
            
            return True
        
        except Exception as e:
            print(f"⚠️ SelfLearner: Learning error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_stats(self) -> Dict:
        """Получить статистику обучения"""
        if not self.enabled:
            return {'enabled': False}
        
        accuracy = self.metric.get() if self.metric else 0.0
        win_rate = (self.wins / self.learning_count * 100) if self.learning_count > 0 else 0.0
        
        return {
            'enabled': True,
            'predictions': self.predictions_count,
            'learned_samples': self.learning_count,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'model_accuracy': accuracy,
            'ready': self.learning_count >= 50
        }


# Singleton
_self_learner = None

def get_self_learner() -> SelfLearner:
    """Получить singleton экземпляр SelfLearner"""
    global _self_learner
    if _self_learner is None:
        _self_learner = SelfLearner()
    return _self_learner
