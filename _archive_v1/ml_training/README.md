# Bybit LSTM Training - Google Colab

## 📋 Инструкция по обучению модели

### Шаг 1: Подготовка Google Drive

1. Откройте Google Drive
2. Создайте структуру папок:
```
Bybit_ML_Data/
├── raw_data/          # CSV файлы (уже загружены)
├── models/            # Сюда сохранятся обученные модели
└── notebooks/         # Сюда можно скопировать notebook
```

### Шаг 2: Загрузка Notebook в Colab

**Вариант A: Через GitHub**
1. Загрузите `bybit_lstm_training.ipynb` на GitHub
2. Откройте Google Colab: https://colab.research.google.com/
3. File → Open Notebook → GitHub → вставьте URL

**Вариант B: Прямая загрузка**
1. Откройте Google Colab: https://colab.research.google.com/
2. File → Upload Notebook
3. Выберите `bybit_lstm_training.ipynb`

**Вариант C: Через Google Drive**
1. Загрузите `bybit_lstm_training.ipynb` в Google Drive
2. Откройте файл → Open with → Google Colaboratory

### Шаг 3: Настройка GPU

1. В Colab: Runtime → Change runtime type
2. Hardware accelerator → **GPU** (T4)
3. Save

### Шаг 4: Запуск обучения

1. Запустите все ячейки по порядку (Runtime → Run all)
2. При первом запуске разрешите доступ к Google Drive
3. Дождитесь завершения обучения (~1-2 часа)

### Шаг 5: Проверка результатов

После обучения проверьте метрики:
- **RMSE** < 100 - хорошо
- **MAE** < 50 - отлично
- **R²** > 0.8 - отлично
- **MAPE** < 5% - отлично

### Шаг 6: Скачивание модели

Файлы автоматически сохранятся в Google Drive:
```
Bybit_ML_Data/models/
├── bybit_lstm_model.h5      # Обученная модель
├── scaler_X.pkl              # Scaler для фичей
├── scaler_y.pkl              # Scaler для таргета
└── model_metadata.json       # Метаданные
```

Скачайте эти файлы на локальный компьютер.

### Шаг 7: Загрузка на VPS

```bash
# Локально (Windows)
scp bybit_lstm_model.h5 root@88.210.10.145:/root/Bybit_Trader/ml_models/
scp scaler_X.pkl root@88.210.10.145:/root/Bybit_Trader/ml_models/
scp scaler_y.pkl root@88.210.10.145:/root/Bybit_Trader/ml_models/
scp model_metadata.json root@88.210.10.145:/root/Bybit_Trader/ml_models/

# На сервере
ssh root@88.210.10.145
docker cp /root/Bybit_Trader/ml_models/bybit_lstm_model.h5 bybit_bot:/data/ml_models/
docker cp /root/Bybit_Trader/ml_models/scaler_X.pkl bybit_bot:/data/ml_models/
docker cp /root/Bybit_Trader/ml_models/scaler_y.pkl bybit_bot:/data/ml_models/
docker cp /root/Bybit_Trader/ml_models/model_metadata.json bybit_bot:/data/ml_models/
```

## 📊 Архитектура модели

```
Input: (60, 26) - 60 timesteps × 26 features
    ↓
LSTM(128) + Dropout(0.2)
    ↓
LSTM(64) + Dropout(0.2)
    ↓
Dense(32, relu) + Dropout(0.1)
    ↓
Dense(1, linear)
    ↓
Output: Predicted price
```

## 🎯 Фичи (26 колонок)

**OHLCV (5):**
- open, high, low, close, volume

**Технические индикаторы (14):**
- RSI, MACD (3), Bollinger Bands (3)
- ATR, Stochastic (2), SMA (2), EMA (2)

**Временные фичи (6):**
- hour_sin/cos, day_sin/cos, month_sin/cos

## ⚙️ Гиперпараметры

- **Sequence Length**: 60 timesteps
- **Batch Size**: 32
- **Epochs**: 100 (с early stopping)
- **Optimizer**: Adam
- **Loss**: MSE
- **Train/Val/Test**: 70/15/15

## 🔧 Troubleshooting

### Проблема: Out of Memory
**Решение:** Уменьшите batch_size до 16

### Проблема: Модель не сходится
**Решение:** 
- Увеличьте epochs до 150
- Уменьшите learning rate

### Проблема: Overfitting
**Решение:**
- Увеличьте Dropout до 0.3
- Уменьшите количество нейронов

## 📈 Ожидаемые результаты

При правильном обучении:
- Training loss: 0.001-0.005
- Validation loss: 0.002-0.008
- Test MAPE: 2-5%
- R²: 0.85-0.95

## 🚀 Следующие шаги

После успешного обучения:
1. Скачайте модель из Google Drive
2. Загрузите на VPS сервер
3. Интегрируйте в торгового бота (Task 4.1)
4. Тестируйте предсказания
5. Мониторьте accuracy в dashboard
