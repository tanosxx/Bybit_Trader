"""
Проверка статуса price_predictor в работающем боте
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем price_predictor который используется в loop
from core.price_predictor import get_price_predictor

predictor = get_price_predictor()

print("=== PRICE PREDICTOR STATUS ===\n")
print(f"Model loaded: {predictor.model is not None}")
print(f"Scaler X loaded: {predictor.scaler_X is not None}")
print(f"Scaler Y loaded: {predictor.scaler_y is not None}")
print(f"Is loaded: {predictor.is_loaded}")

print(f"\nPaths:")
print(f"  Model: {predictor.model_path}")
print(f"  Scaler X: {predictor.scaler_x_path}")
print(f"  Scaler Y: {predictor.scaler_y_path}")

if predictor.model:
    print(f"\n✅ Модель загружена!")
else:
    print(f"\n❌ Модель НЕ загружена!")

if predictor.scaler_X and predictor.scaler_y:
    print(f"✅ Scalers загружены!")
else:
    print(f"❌ Scalers НЕ загружены!")
