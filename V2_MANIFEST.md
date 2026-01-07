# 🚀 Bybit Trading Bot v2.0 - Simple Profit Edition

## 🎯 Философия

**v1 (Legacy):** Сложная ML система с 7 уровнями фильтрации, множеством AI агентов
**v2 (Current):** Простая математическая стратегия RSI Grid - Mean Reversion

**Принцип:** Простота = Прибыль

---

## 📊 Что изменилось

### ❌ Удалено (Archived в `_archive_v1/`)

1. **ML Models:**
   - LSTM v2 neural network
   - Self-Learning ARF (River)
   - Scenario Tester (pattern matching)
   
2. **AI Agents:**
   - Strategic Brain (Gemini 2.5 Flash)
   - Local Brain (ML predictions)
   - Futures Brain (Multi-agent consensus)
   - Strategic Compliance
   
3. **Complex Systems:**
   - 7-level decision filtering
   - News sentiment analysis
   - Pattern matching на 1000 свечей
   - Gatekeeper filters
   
4. **Folders:**
   - `ml_training/` - ML модели и обучение
   - `ml_models/` - Сохранённые модели
   - `ml_data/` - Данные для обучения
   - `ml_export/` - Экспортированные свечи
   - `memory-bank/` - Контекст для AI

### ✅ Добавлено

1. **Simple RSI Grid Strategy** (`core/strategies/simple_scalper.py`)
   - RSI (14) для определения перепроданности/перекупленности
   - Bollinger Bands (20, 2) для подтверждения
   - Фиксированные TP/SL без трейлинга
   - Таймфрейм: 15 минут

2. **Simplified Main Loop** (`main.py`)
   - Прямой цикл: Scan → Signal → Execute
   - Без сложной логики фильтрации
   - Минимальные зависимости

3. **Clean Config** (`config_v2.py`)
   - Только необходимые параметры
   - Убраны все ML настройки
   - Параметры RSI/BB стратегии

---

## 🎲 Стратегия: RSI Grid (Mean Reversion)

### Логика

**LONG сигнал:**
- RSI < 30 (перепроданность)
- Цена <= Нижняя полоса Боллинджера

**SHORT сигнал:**
- RSI > 70 (перекупленность)
- Цена >= Верхняя полоса Боллинджера

**Выход:**
- Take Profit: +1.5%
- Stop Loss: -2.0%
- Без трейлинга (фиксированные уровни)

### Параметры

```python
# RSI
rsi_period = 14
rsi_oversold = 30
rsi_overbought = 70

# Bollinger Bands
bb_period = 20
bb_std = 2.0

# Risk Management
take_profit_pct = 1.5  # +1.5%
stop_loss_pct = 2.0    # -2.0%
leverage = 3           # 3x
risk_per_trade = 0.05  # 5% баланса
```

### Торговые пары

- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT

---

## 📁 Структура проекта v2

```
Bybit_Trader/
├── _archive_v1/              # Архив v1 системы
│   ├── ai_brain_local.py
│   ├── futures_brain.py
│   ├── strategic_brain.py
│   ├── ml_training/
│   ├── ml_models/
│   └── ...
│
├── core/
│   ├── strategies/
│   │   └── simple_scalper.py    # ✨ NEW: RSI Grid Strategy
│   ├── executors/
│   │   └── futures_executor.py  # Исполнение ордеров
│   ├── telegram_commander.py    # Telegram управление
│   └── risk_manager.py          # Риск-менеджмент
│
├── database/
│   └── db_manager.py            # База данных
│
├── web/
│   ├── app.py                   # Dashboard
│   └── templates/
│
├── main.py                      # ✨ NEW: Упрощённый main loop
├── config_v2.py                 # ✨ NEW: Чистая конфигурация
├── requirements.txt             # Зависимости (убраны ML библиотеки)
├── docker-compose.yml           # Docker setup
└── V2_MANIFEST.md              # Этот файл
```

---

## 🚀 Запуск v2

### 1. Подготовка

```bash
# Убедитесь что вы на ветке v2-simple-profit
git branch
# Должно показать: * v2-simple-profit

# Проверьте что старая система архивирована
ls _archive_v1/
# Должны увидеть: ml_training/, ml_models/, ai_brain_local.py, etc.
```

### 2. Обновление зависимостей

```bash
# Удалите старые ML библиотеки из requirements.txt
# Оставьте только:
# - pybit
# - pandas
# - numpy
# - pydantic
# - pydantic-settings
# - asyncpg
# - sqlalchemy
# - python-telegram-bot
```

### 3. Обновление конфигурации

```bash
# Переименуйте config_v2.py в config.py
mv config_v2.py config.py

# Или обновите импорты в коде:
# from config_v2 import settings
```

### 4. Запуск на сервере

```bash
# Скопируйте файлы на сервер
scp -r Bybit_Trader/ root@88.210.10.145:/root/Bybit_Trader_v2/

# Подключитесь к серверу
ssh root@88.210.10.145

# Перейдите в папку
cd /root/Bybit_Trader_v2

# Запустите Docker
docker-compose up -d

# Проверьте логи
docker logs bybit_bot -f
```

---

## 📊 Ожидаемые результаты

### v1 (Legacy) Performance
- **Trades:** 652
- **Win Rate:** 59.2%
- **ROI:** +54.4% ($100 → $154.44)
- **Complexity:** Высокая (7 фильтров, ML, агенты)

### v2 (Target) Performance
- **Trades:** 100-200/месяц (больше сигналов)
- **Win Rate:** 55-65% (цель)
- **ROI:** 30-50%/месяц (цель)
- **Complexity:** Низкая (чистая математика)

### Преимущества v2
1. ✅ **Простота** - легко понять и отладить
2. ✅ **Скорость** - нет ML вычислений
3. ✅ **Надёжность** - меньше точек отказа
4. ✅ **Прозрачность** - понятная логика сигналов
5. ✅ **Масштабируемость** - легко добавить новые пары

---

## 🔧 Troubleshooting

### Проблема: Нет сигналов

**Причина:** Рынок не в экстремальных зонах (RSI 30-70)

**Решение:**
- Подождать волатильности
- Или снизить пороги RSI (25/75)

### Проблема: Много ложных сигналов

**Причина:** Флэтовый рынок

**Решение:**
- Добавить фильтр CHOP > 60 (флэт)
- Или увеличить период BB (20 → 30)

### Проблема: Слишком частые SL

**Причина:** SL слишком близко (-2%)

**Решение:**
- Увеличить SL до -2.5% или -3%
- Или уменьшить leverage (3x → 2x)

---

## 📝 TODO для v2.1

- [ ] Добавить CHOP filter (флэт фильтр)
- [ ] Добавить Volume filter (объём)
- [ ] Добавить Trailing Stop (опционально)
- [ ] Добавить Multi-timeframe analysis (15m + 1h)
- [ ] Добавить Backtesting на исторических данных
- [ ] Добавить Performance dashboard

---

## 🎓 Уроки из v1

1. **Сложность ≠ Прибыль**
   - 7 фильтров не дали 70% winrate
   - ML модели требуют постоянного обучения
   - Агенты добавляют латентность

2. **Простые стратегии работают**
   - Mean reversion - проверенная временем
   - RSI + BB - классическая комбинация
   - Фиксированные TP/SL - понятный риск

3. **Фокус на исполнении**
   - Быстрое размещение ордеров
   - Надёжный мониторинг позиций
   - Корректное закрытие по TP/SL

---

## 📚 Ссылки

- **v1 Legacy Tag:** `v1.0-legacy`
- **v1 Branch:** `main`
- **v2 Branch:** `v2-simple-profit`
- **Database Backup:** `backup_v1_final_20260107_214532.sql`

---

**Дата создания:** 7 января 2026  
**Версия:** v2.0.0  
**Статус:** 🚧 В разработке

**Следующий шаг:** Тестирование на Demo, затем переход на Real Trading
