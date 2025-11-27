"""
Скрипт для переобучения ML модели с текущей версией TensorFlow
Запускать на сервере: docker exec bybit_bot python scripts/retrain_ml_model.py
"""
import sys
sys.path.append('/app')

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from sklearn.preprocessing import MinMaxScaler
import joblib

from core.bybit_api import get_bybit_api
from core.indicators import add_all_indicators


async def collect_training_data(symbol: str, days: int = 90):
    """Собрать данные для обучения"""
    print(f"\n📊 Collecting {days} days of data for {symbol}...")
    
    api = get_bybit_api()
    
    # Просто используем get_klines с максимальным лимитом
    # Для 90 дней нужно ~2160 свечей (60 мин), но API даёт максимум 200
    # Поэтому возьмём что есть
    klines = await api.get_klines(
        symbol=symbol,
        interval="60",
        limit=200
    )
    
    if not klines:
        print("❌ Failed to collect data")
        return []
    
    print(f"✅ Collected {len(klines)} candles (last ~8 days)")
    return klines


def prepare_features(klines):
    """Подготовить фичи"""
    print("\n🔧 Preparing features...")
    
    df = pd.DataFrame(klines)
    
    # Добавляем индикаторы
    df = add_all_indicators(df)
    
    # Временные фичи
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
    
    print(f"✅ Prepared {len(df)} samples")
    return df


def create_sequences(data, target, sequence_length=60):
    """Создать последовательности для LSTM"""
    print(f"\n🔄 Creating sequences (length={sequence_length})...")
    
    X, y = [], []
    
    for i in range(len(data) - sequence_length):
        X.append(data[i:i + sequence_length])
        y.append(target[i + sequence_length])
    
    X = np.array(X)
    y = np.array(y).reshape(-1, 1)
    
    print(f"✅ Created {len(X)} sequences")
    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    
    return X, y


def build_model(input_shape):
    """Построить LSTM модель"""
    print(f"\n🏗️  Building model...")
    
    model = Sequential([
        Input(shape=input_shape),
        LSTM(128, return_sequences=True),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )
    
    print(f"✅ Model built")
    model.summary()
    
    return model


async def main():
    """Главная функция"""
    print("="*60)
    print("🤖 Retraining ML Model")
    print("="*60)
    
    # Параметры
    SYMBOL = "BTCUSDT"
    DAYS = 90  # Не используется, берём максимум из API
    SEQUENCE_LENGTH = 60
    EPOCHS = 20  # Уменьшено для быстрого обучения
    BATCH_SIZE = 16
    
    # Фичи
    features = [
        'open', 'high', 'low', 'close', 'volume',
        'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
        'atr', 'stoch_k', 'stoch_d', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
    ]
    
    # 1. Собираем данные
    klines = await collect_training_data(SYMBOL, DAYS)
    
    # 2. Подготавливаем фичи
    df = prepare_features(klines)
    
    # 3. Выбираем фичи и таргет
    X_data = df[features].values
    y_data = df['close'].values.reshape(-1, 1)
    
    # 4. Нормализация
    print("\n📏 Normalizing data...")
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_scaled = scaler_X.fit_transform(X_data)
    y_scaled = scaler_y.fit_transform(y_data)
    
    print(f"✅ Data normalized")
    
    # 5. Создаём последовательности
    X_seq, y_seq = create_sequences(X_scaled, y_scaled, SEQUENCE_LENGTH)
    
    # 6. Train/Test split
    split_idx = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]
    
    print(f"\n📊 Train/Test split:")
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test:  {len(X_test)} samples")
    
    # 7. Строим модель
    model = build_model((SEQUENCE_LENGTH, len(features)))
    
    # 8. Обучение
    print(f"\n🎓 Training model...")
    print(f"   Epochs: {EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1
    )
    
    # 9. Оценка
    print(f"\n📈 Evaluating model...")
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    
    print(f"   Train Loss: {train_loss:.6f}, MAE: {train_mae:.6f}")
    print(f"   Test Loss:  {test_loss:.6f}, MAE: {test_mae:.6f}")
    
    # 10. Сохранение
    print(f"\n💾 Saving model...")
    
    os.makedirs("/data/ml_models", exist_ok=True)
    
    model.save("/data/ml_models/bybit_lstm_model.h5")
    joblib.dump(scaler_X, "/data/ml_models/scaler_X.pkl")
    joblib.dump(scaler_y, "/data/ml_models/scaler_y.pkl")
    
    print(f"✅ Model saved to /data/ml_models/")
    
    # 11. Тестовое предсказание
    print(f"\n🧪 Testing prediction...")
    
    last_sequence = X_seq[-1:] 
    pred_scaled = model.predict(last_sequence, verbose=0)
    predicted_price = scaler_y.inverse_transform(pred_scaled)[0][0]
    actual_price = df['close'].iloc[-1]
    
    print(f"   Actual price:    ${actual_price:,.2f}")
    print(f"   Predicted price: ${predicted_price:,.2f}")
    print(f"   Difference:      {((predicted_price - actual_price) / actual_price * 100):+.2f}%")
    
    print("\n" + "="*60)
    print("✅ Retraining completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
