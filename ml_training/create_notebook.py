"""
Скрипт для создания Jupyter Notebook для обучения LSTM модели
Запустить: python ml_training/create_notebook.py
"""
import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Bybit LSTM Price Prediction Model\n",
                "\n",
                "Обучение LSTM модели для предсказания цен криптовалют.\n",
                "\n",
                "**Датасет:** 43,560 записей, 5 пар, 32 фичи\n",
                "\n",
                "**Архитектура:** LSTM (2 слоя) + Dropout"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 1. Setup & Installation"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Установка библиотек\n",
                "!pip install -q tensorflow pandas scikit-learn matplotlib seaborn"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Импорты\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "from sklearn.preprocessing import MinMaxScaler\n",
                "from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score\n",
                "import tensorflow as tf\n",
                "from tensorflow.keras.models import Sequential\n",
                "from tensorflow.keras.layers import LSTM, Dense, Dropout\n",
                "from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau\n",
                "import joblib\n",
                "import warnings\n",
                "warnings.filterwarnings('ignore')\n",
                "\n",
                "print(f'TensorFlow: {tf.__version__}')\n",
                "print(f'GPU: {tf.config.list_physical_devices(\"GPU\")}')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Подключение Google Drive\n",
                "from google.colab import drive\n",
                "drive.mount('/content/drive')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 2. Data Loading"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Загрузка данных\n",
                "DATA_PATH = '/content/drive/MyDrive/Bybit_ML_Data/raw_data/'\n",
                "symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']\n",
                "dataframes = []\n",
                "\n",
                "for symbol in symbols:\n",
                "    df = pd.read_csv(DATA_PATH + f'klines_{symbol}_60.csv')\n",
                "    df['symbol'] = symbol\n",
                "    dataframes.append(df)\n",
                "    print(f'Loaded {symbol}: {len(df)} records')\n",
                "\n",
                "df_all = pd.concat(dataframes, ignore_index=True)\n",
                "print(f'\\nTotal: {len(df_all)} records')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["df_all.head()"]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 3. Preprocessing"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Выбор фичей\n",
                "features = [\n",
                "    'open', 'high', 'low', 'close', 'volume',\n",
                "    'rsi', 'macd', 'macd_signal', 'macd_histogram',\n",
                "    'bb_upper', 'bb_middle', 'bb_lower',\n",
                "    'atr', 'stoch_k', 'stoch_d',\n",
                "    'sma_20', 'sma_50', 'ema_12', 'ema_26',\n",
                "    'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos'\n",
                "]\n",
                "\n",
                "df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])\n",
                "df_all = df_all.sort_values('timestamp').reset_index(drop=True)\n",
                "\n",
                "X = df_all[features].values\n",
                "y = df_all['close'].values\n",
                "\n",
                "print(f'X: {X.shape}, y: {y.shape}')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Нормализация\n",
                "scaler_X = MinMaxScaler()\n",
                "scaler_y = MinMaxScaler()\n",
                "\n",
                "X_scaled = scaler_X.fit_transform(X)\n",
                "y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))\n",
                "\n",
                "print('Normalized')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Создание sequences\n",
                "def create_sequences(X, y, seq_length=60):\n",
                "    X_seq, y_seq = [], []\n",
                "    for i in range(len(X) - seq_length):\n",
                "        X_seq.append(X[i:i+seq_length])\n",
                "        y_seq.append(y[i+seq_length])\n",
                "    return np.array(X_seq), np.array(y_seq)\n",
                "\n",
                "SEQ_LENGTH = 60\n",
                "X_seq, y_seq = create_sequences(X_scaled, y_scaled, SEQ_LENGTH)\n",
                "print(f'Sequences: {X_seq.shape}')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Train/Val/Test split\n",
                "train_size = int(len(X_seq) * 0.70)\n",
                "val_size = int(len(X_seq) * 0.15)\n",
                "\n",
                "X_train = X_seq[:train_size]\n",
                "y_train = y_seq[:train_size]\n",
                "X_val = X_seq[train_size:train_size+val_size]\n",
                "y_val = y_seq[train_size:train_size+val_size]\n",
                "X_test = X_seq[train_size+val_size:]\n",
                "y_test = y_seq[train_size+val_size:]\n",
                "\n",
                "print(f'Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 4. Model"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# LSTM модель\n",
                "model = Sequential([\n",
                "    LSTM(128, return_sequences=True, input_shape=(SEQ_LENGTH, len(features))),\n",
                "    Dropout(0.2),\n",
                "    LSTM(64, return_sequences=False),\n",
                "    Dropout(0.2),\n",
                "    Dense(32, activation='relu'),\n",
                "    Dropout(0.1),\n",
                "    Dense(1, activation='linear')\n",
                "])\n",
                "\n",
                "model.compile(optimizer='adam', loss='mse', metrics=['mae'])\n",
                "model.summary()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 5. Training"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Callbacks\n",
                "callbacks = [\n",
                "    EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),\n",
                "    ModelCheckpoint('best_model.h5', monitor='val_loss', save_best_only=True),\n",
                "    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=0.00001)\n",
                "]"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Обучение\n",
                "history = model.fit(\n",
                "    X_train, y_train,\n",
                "    validation_data=(X_val, y_val),\n",
                "    epochs=100,\n",
                "    batch_size=32,\n",
                "    callbacks=callbacks,\n",
                "    verbose=1\n",
                ")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 6. Evaluation"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# График обучения\n",
                "plt.figure(figsize=(15, 5))\n",
                "plt.subplot(1, 2, 1)\n",
                "plt.plot(history.history['loss'], label='Train')\n",
                "plt.plot(history.history['val_loss'], label='Val')\n",
                "plt.title('Loss')\n",
                "plt.legend()\n",
                "plt.grid(True)\n",
                "\n",
                "plt.subplot(1, 2, 2)\n",
                "plt.plot(history.history['mae'], label='Train')\n",
                "plt.plot(history.history['val_mae'], label='Val')\n",
                "plt.title('MAE')\n",
                "plt.legend()\n",
                "plt.grid(True)\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Предсказания\n",
                "y_pred_scaled = model.predict(X_test)\n",
                "y_test_orig = scaler_y.inverse_transform(y_test)\n",
                "y_pred_orig = scaler_y.inverse_transform(y_pred_scaled)\n",
                "\n",
                "mse = mean_squared_error(y_test_orig, y_pred_orig)\n",
                "rmse = np.sqrt(mse)\n",
                "mae = mean_absolute_error(y_test_orig, y_pred_orig)\n",
                "r2 = r2_score(y_test_orig, y_pred_orig)\n",
                "mape = np.mean(np.abs((y_test_orig - y_pred_orig) / y_test_orig)) * 100\n",
                "\n",
                "print(f'RMSE: {rmse:.4f}')\n",
                "print(f'MAE: {mae:.4f}')\n",
                "print(f'R²: {r2:.4f}')\n",
                "print(f'MAPE: {mape:.2f}%')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# График предсказаний\n",
                "plt.figure(figsize=(15, 6))\n",
                "plt.plot(y_test_orig[:500], label='Actual', alpha=0.7)\n",
                "plt.plot(y_pred_orig[:500], label='Predicted', alpha=0.7)\n",
                "plt.title('Predicted vs Actual')\n",
                "plt.legend()\n",
                "plt.grid(True)\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["## 7. Export"]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Сохранение\n",
                "model.save('bybit_lstm_model.h5')\n",
                "joblib.dump(scaler_X, 'scaler_X.pkl')\n",
                "joblib.dump(scaler_y, 'scaler_y.pkl')\n",
                "\n",
                "import json\n",
                "metadata = {\n",
                "    'sequence_length': SEQ_LENGTH,\n",
                "    'features': features,\n",
                "    'metrics': {'rmse': float(rmse), 'mae': float(mae), 'r2': float(r2), 'mape': float(mape)}\n",
                "}\n",
                "with open('model_metadata.json', 'w') as f:\n",
                "    json.dump(metadata, f, indent=2)\n",
                "\n",
                "print('✅ Saved!')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Копирование в Drive\n",
                "!cp bybit_lstm_model.h5 /content/drive/MyDrive/Bybit_ML_Data/models/\n",
                "!cp scaler_X.pkl /content/drive/MyDrive/Bybit_ML_Data/models/\n",
                "!cp scaler_y.pkl /content/drive/MyDrive/Bybit_ML_Data/models/\n",
                "!cp model_metadata.json /content/drive/MyDrive/Bybit_ML_Data/models/\n",
                "print('✅ Copied to Drive!')"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        },
        "accelerator": "GPU"
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

# Сохраняем notebook
with open('ml_training/bybit_lstm_training.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print("✅ Notebook created: ml_training/bybit_lstm_training.ipynb")
