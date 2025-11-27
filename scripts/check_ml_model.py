"""
Проверка ML модели
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from core.ml_predictor import get_ml_predictor

async def check():
    ml = get_ml_predictor()
    
    # Загружаем модель
    await ml.load_model()
    
    print("=== ML MODEL STATUS ===\n")
    print(f"Model loaded: {ml.model is not None}")
    print(f"Model path: {ml.model_path}")
    print(f"Scaler X loaded: {ml.scaler_X is not None}")
    print(f"Scaler Y loaded: {ml.scaler_y is not None}")
    print(f"Is loaded: {ml.is_loaded}")
    
    if ml.model:
        print(f"\n✅ LSTM модель загружена успешно!")
        print(f"   Sequence length: {ml.sequence_length}")
        print(f"   Features: {len(ml.features)}")
    else:
        print(f"\n❌ Модель НЕ загружена")

asyncio.run(check())


