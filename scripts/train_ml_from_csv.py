"""
Обучение ML модели на всех исторических данных из CSV
Запускать на сервере: docker exec bybit_bot python scripts/train_ml_from_csv.py
"""
import sys
sys.path.append('/app')

import os
import pandas as pd
import numpy as np
from datetime import datetime

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import joblib


def load_all_data(data_dir="/data/ml_export"):
    """Загрузить все CSV файлы"""
    print(f"\n📂 Loading data from {data_dir}...")
    
    all_data = []
    symbols = []
    
    for filename in os.listdir(data_dir):
        if filename.endswith('.csv') and filename.startswith('klines_'):
            filepath = os.path.join(data_dir, filename)
            symbol = filename.split('_')[1]  # BTCUSDT
            
            print(f"   Loading {filename}...")
            df = pd.read_csv(filepath)
            df['symbol'] = symbol
            all_data.append(df)
            symbols.append(symbol)
            print(f"      {len(df)} records")
    
    # Объединяем все данные
    combined_df = pd.concat(all_data, ignore_index=True)
    
    print(f"\n✅ Loaded {len(combined_df)} total records from {len(symbols)} symbols")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Date range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
    
    return combined_df, symbols


def prepare_features(df):
    """Подготовить фичи для обучения"""
    print(f"\n🔧 Preparing features...")
    
    # Фичи которые будем использовать
    feature_cols = [
        'open', 'high', 'low', 'close', 'volume',
        'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
        'atr', 'stoch_k', 'stoch_d', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'
    ]
    
    # Проверяем что все фичи есть
    missing = [col for col in feature_cols if col not in df.columns]
    if missing:
        print(f"❌ Missing columns: {missing}")
        return None, None
    
    # Удаляем NaN
    df_clean = df.dropna(subset=feature_cols + ['close'])
    print(f"   Removed {len(df) - len(df_clean)} rows with NaN")
    
    X = df_clean[feature_cols].values
    y = df_clean['close'].values.reshape(-1, 1)
    
    print(f"✅ Features prepared: {X.shape}")
    
    return X, y


def create_sequences(X, y, sequence_length=60):
    """Создать последовательности для LSTM"""
    print(f"\n🔄 Creating sequences (length={sequence_length})...")
    
    X_seq, y_seq = [], []
    
    for i in range(len(X) - sequence_length):
        X_seq.append(X[i:i + sequence_length])
        y_seq.append(y[i + sequence_length])
    
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)
    
    print(f"✅ Created {len(X_seq)} sequences")
    print(f"   X shape: {X_seq.shape}")
    print(f"   y shape: {y_seq.shape}")
    
    return X_seq, y_seq


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


def main():
    """Главная функция"""
    print("="*60)
    print("🤖 Training ML Model on All Historical Data")
    print("="*60)
    
    # Параметры
    SEQUENCE_LENGTH = 60
    EPOCHS = 100
    BATCH_SIZE = 32
    VALIDATION_SPLIT = 0.2
    
    # 1. Загружаем данные
    df, symbols = load_all_data()
    
    if df is None or len(df) == 0:
        print("❌ No data loaded")
        return
    
    # 2. Подготавливаем фичи
    X, y = prepare_features(df)
    
    if X is None:
        print("❌ Failed to prepare features")
        return
    
    # 3. Нормализация
    print(f"\n📏 Normalizing data...")
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y)
    
    print(f"✅ Data normalized")
    
    # 4. Создаём последовательности
    X_seq, y_seq = create_sequences(X_scaled, y_scaled, SEQUENCE_LENGTH)
    
    # 5. Train/Test split
    split_idx = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]
    
    print(f"\n📊 Train/Test split:")
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test:  {len(X_test)} samples")
    
    # 6. Строим модель
    model = build_model((SEQUENCE_LENGTH, X.shape[1]))
    
    # 7. Обучение
    print(f"\n🎓 Training model...")
    print(f"   Epochs: {EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Early stopping: patience=10")
    
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early_stop],
        verbose=1
    )
    
    # 8. Оценка
    print(f"\n📈 Evaluating model...")
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    
    print(f"   Train Loss: {train_loss:.6f}, MAE: {train_mae:.6f}")
    print(f"   Test Loss:  {test_loss:.6f}, MAE: {test_mae:.6f}")
    
    # 9. Сохранение
    print(f"\n💾 Saving model...")
    
    os.makedirs("/data/ml_models", exist_ok=True)
    
    # Сохраняем с версией
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = f"/data/ml_models/v_{timestamp}"
    os.makedirs(version_dir, exist_ok=True)
    
    model.save(f"{version_dir}/bybit_lstm_model.h5")
    joblib.dump(scaler_X, f"{version_dir}/scaler_X.pkl")
    joblib.dump(scaler_y, f"{version_dir}/scaler_y.pkl")
    
    # Копируем в current
    model.save("/data/ml_models/bybit_lstm_model.h5")
    joblib.dump(scaler_X, "/data/ml_models/scaler_X.pkl")
    joblib.dump(scaler_y, "/data/ml_models/scaler_y.pkl")
    
    # Сохраняем метаданные
    metadata = {
        'version': timestamp,
        'symbols': symbols,
        'total_samples': len(X_seq),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'sequence_length': SEQUENCE_LENGTH,
        'features': X.shape[1],
        'epochs_trained': len(history.history['loss']),
        'train_loss': float(train_loss),
        'train_mae': float(train_mae),
        'test_loss': float(test_loss),
        'test_mae': float(test_mae)
    }
    
    import json
    with open(f"{version_dir}/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    with open("/data/ml_models/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Model saved to:")
    print(f"   Current: /data/ml_models/")
    print(f"   Version: {version_dir}/")
    
    # 10. Тестовые предсказания для каждого символа
    print(f"\n🧪 Testing predictions for each symbol...")
    
    for symbol in symbols:
        # Берём последние данные для этого символа
        symbol_data = df[df['symbol'] == symbol].tail(SEQUENCE_LENGTH + 1)
        
        if len(symbol_data) < SEQUENCE_LENGTH + 1:
            print(f"   {symbol}: Not enough data")
            continue
        
        X_test_symbol, y_test_symbol = prepare_features(symbol_data)
        if X_test_symbol is None:
            continue
        
        X_test_scaled = scaler_X.transform(X_test_symbol)
        last_sequence = X_test_scaled[-SEQUENCE_LENGTH:].reshape(1, SEQUENCE_LENGTH, X.shape[1])
        
        pred_scaled = model.predict(last_sequence, verbose=0)
        predicted_price = scaler_y.inverse_transform(pred_scaled)[0][0]
        actual_price = y_test_symbol[-1][0]
        
        change_pct = ((predicted_price - actual_price) / actual_price) * 100
        
        print(f"   {symbol}:")
        print(f"      Actual:    ${actual_price:,.2f}")
        print(f"      Predicted: ${predicted_price:,.2f}")
        print(f"      Change:    {change_pct:+.2f}%")
    
    print("\n" + "="*60)
    print("✅ Training completed!")
    print("="*60)


if __name__ == "__main__":
    main()
