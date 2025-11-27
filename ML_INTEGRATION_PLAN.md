# 🤖 ML Integration Plan - Bybit Trader

## 📋 Что сделано

✅ Создан полный spec в `.kiro/specs/bybit-ml-integration/`:
- **requirements.md** - 8 требований с acceptance criteria
- **design.md** - Детальная архитектура системы
- **tasks.md** - 27 задач для реализации
- **README.md** - Обзор проекта

## 🎯 Главная идея

Интегрировать LSTM модель для предсказания цен криптовалют:
1. Собираем максимум исторических данных с Bybit API
2. Экспортируем в CSV с техническими индикаторами (RSI, MACD, BB)
3. Обучаем LSTM модель в Google Colab (бесплатный GPU)
4. Загружаем модель на VPS сервер
5. Бот использует ML предсказания + AI анализ для торговли
6. Dashboard показывает ML метрики и accuracy

## 🏗️ Архитектура

```
VPS Server (Docker) → Bybit API → PostgreSQL
         ↓
   Export to CSV
         ↓
   Google Drive (Bybit_ML_Data/)
         ↓
   Google Colab (GPU Training)
         ↓
   Trained Model (.h5)
         ↓
   Upload to VPS
         ↓
   ML Predictor → Real Trader → Dashboard
```

## 📦 Компоненты

### 1. Data Collection (Bybit API расширение)
- `get_trade_history_full()` - история сделок
- `get_closed_pnl_history()` - история PnL
- `get_wallet_transactions()` - движение средств
- `get_klines_historical()` - исторические свечи

### 2. Data Export
- `scripts/export_historical_data.py`
- Расчет RSI, MACD, Bollinger Bands
- Временные фичи (hour, day_of_week, month)
- Экспорт в CSV

### 3. Google Colab Training
- `ml_training/bybit_lstm_training.ipynb`
- LSTM архитектура (2 слоя + Dropout)
- 60 timesteps sequence
- Train/Val/Test split (70/15/15)
- Early stopping

### 4. ML Predictor
- `core/ml_predictor.py`
- Загрузка модели и scaler
- Real-time предсказания
- Confidence calculation

### 5. Integration
- Модификация `real_trader.py`
- Комбинирование ML + AI решений
- Настраиваемые веса (default 50/50)

### 6. Dashboard
- Секция "🤖 ML Predictions"
- Predicted vs Actual график
- Model Accuracy метрики
- Последние предсказания

## 📊 Google Drive структура

Нужно создать папку:
```
Google Drive/
└── Bybit_ML_Data/
    ├── raw_data/          # Сюда загружаем CSV
    ├── models/            # Сюда сохраняем обученные модели
    └── notebooks/         # Сюда копируем Colab notebook
```

## ⏱️ Оценка времени

### Разработка (3 недели)
- **Week 1:** Data Collection + Export + Colab setup (5 дней)
- **Week 2:** Training + ML Predictor + Dashboard (5 дней)
- **Week 3:** Testing + Documentation + Deployment (5 дней)

### Операционное время
- Сбор данных: 10-30 минут
- Экспорт в CSV: 2-5 минут
- Обучение модели: 1-2 часа (на GPU)
- Деплой: 30 минут

## 🚀 Workflow (после разработки)

### Первый запуск:
```bash
# 1. На сервере: собрать данные
docker exec -it bybit_trader_app python scripts/collect_historical_data.py

# 2. На сервере: экспорт в CSV
docker exec -it bybit_trader_app python scripts/export_historical_data.py

# 3. Локально: скачать CSV
scp root@88.210.10.145:/path/to/data/ml_export/*.csv ./

# 4. Загрузить CSV в Google Drive (Bybit_ML_Data/raw_data/)

# 5. Открыть Colab notebook и обучить модель (1-2 часа)

# 6. Скачать модель (.h5 + scaler.pkl)

# 7. Загрузить на сервер
scp bybit_lstm_model.h5 root@88.210.10.145:/path/to/data/ml_models/current/
scp scaler.pkl root@88.210.10.145:/path/to/data/ml_models/current/

# 8. Включить ML
# В .env: ML_ENABLED=true
docker-compose restart app

# 9. Проверить dashboard
# http://88.210.10.145:8501
```

### Переобучение (каждые 7 дней):
```bash
# 1. Экспорт новых данных
docker exec -it bybit_trader_app python scripts/export_historical_data.py

# 2. Загрузить в Google Drive

# 3. Переобучить в Colab

# 4. Загрузить новую модель на сервер

# 5. Перезапустить бота
```

## 📈 Метрики успеха

- ✅ Model Accuracy > 60% на test set
- ✅ Prediction Latency < 2 секунд
- ✅ Улучшение winrate на 5-10%
- ✅ Снижение drawdown на 10-15%
- ✅ Увеличение среднего PnL на 10-20%

## 🔧 Конфигурация

Новые настройки в `.env`:
```env
ML_ENABLED=true
ML_MODEL_PATH=/data/ml_models/bybit_lstm_model.h5
ML_SCALER_PATH=/data/ml_models/scaler.pkl
ML_CONFIDENCE_THRESHOLD=0.65
ML_WEIGHT=0.5  # 50% ML, 50% AI
```

## 📝 Следующие шаги

1. **Прочитать spec:** `.kiro/specs/bybit-ml-integration/README.md`
2. **Начать с Phase 1:** Расширение Bybit API (Task 1.1)
3. **Следовать tasks.md:** 27 задач по порядку
4. **Тестировать на сервере:** Всё в Docker!

## ⚠️ Важные правила

- ❌ **НИКОГДА** не запускать локально
- ✅ **ВСЕГДА** работать на сервере (88.210.10.145)
- ✅ Локально только редактирование кода
- ✅ Все запуски, тесты - в Docker на сервере

## 📚 Документация

После реализации будет создана:
- `docs/ML_GUIDE.md` - Руководство пользователя
- `docs/ML_ARCHITECTURE.md` - Техническая документация

---

**Готов начинать?** Открой `.kiro/specs/bybit-ml-integration/tasks.md` и начни с Task 1.1! 🚀
