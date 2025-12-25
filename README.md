# Bybit Trading Bot 🤖

Автоматический торговый бот для Bybit Futures с AI анализом, ML предсказаниями и Multi-Agent системой принятия решений.

## 🎯 Ключевые особенности

- **Hybrid AI System**: Gemini 2.5 Flash (primary) + Algion GPTFree (fallback) для стратегического анализа
- **ML Predictions**: LSTM модель + Self-Learning (River ARF) с точностью 90%+
- **Multi-Agent Decision**: 6 агентов с взвешенным голосованием
- **7-Level Filtering**: От Strategic Brain до Fee Profitability Check
- **Limit Orders**: Maker стратегия (0.02% fee vs 0.055% Taker)
- **Real-Time Dashboard**: Neural HUD с визуализацией AI решений
- **Adaptive Strategy**: Автоматическое переключение Trend Following ↔ Mean Reversion
- **Risk Management**: Trailing Stop, Emergency Brake, Position Limits

## 📊 Текущая производительность

- **Баланс**: $201.42 (+101% от стартовых $100)
- **Win Rate**: 64.9% (137 wins / 74 losses из 211 закрытых сделок)
- **Всего сделок**: 498 (включая phantom closes и открытые позиции)
- **Режим**: Demo Trading (Bybit Testnet)
- **Стратегия**: Adaptive (Trend Following + Mean Reversion)

## 🏗️ Архитектура

### Технологический стек

- **Язык**: Python 3.10+
- **База данных**: PostgreSQL 15 (Docker)
- **ORM**: SQLAlchemy (Async)
- **Dashboard**: Flask (порт 8585)
- **ML**: TensorFlow 2.18 (LSTM), Scikit-learn, River (online learning)
- **AI Models**:
  - **Strategic Brain**: Gemini 2.5 Flash (primary) + Algion GPTFree (fallback)
  - **Local Brain**: LSTM v2 + Self-Learning ARF
  - **News Brain**: CryptoPanic API + VADER Sentiment

### Docker контейнеры

```yaml
bybit_bot        # Основной торговый бот (hybrid_loop.py)
bybit_dashboard  # Web интерфейс (Flask, порт 8585)
bybit_sync       # Синхронизация позиций с биржей
bybit_monitor    # Мониторинг позиций и SL/TP
bybit_db         # PostgreSQL база данных
```

## 🧠 AI Decision System (7 уровней фильтрации)

### Level 0: Strategic Brain (Gemini 2.5 Flash)
- Анализирует глобальный режим рынка раз в 30 минут
- **BULL_RUSH** → только LONG позиции
- **BEAR_CRASH** → только SHORT позиции
- **SIDEWAYS** → оба направления разрешены
- **UNCERTAIN** → торговля с повышенной осторожностью
- **Primary**: Gemini 2.5 Flash (2 API ключа с ротацией)
- **Fallback**: Algion GPTFree (gpt-4.1, gpt-3.5-turbo, gpt-4o-mini)

### Level 1: Trading Hours Check
- Проверка торговых часов (по умолчанию 24/7)
- Настраивается через `trading_hours_enabled`

### Level 2: CHOP Filter (Gatekeeper)
- **CHOP > 50** → флэт → активируется Mean Reversion
- **CHOP ≤ 45** → тренд → активируется Trend Following
- Зона 45-50: гистерезис (сохраняем текущий режим)

### Level 3: Pattern Filter (Historical Win Rate)
- Анализ 1,000 исторических свечей
- Поиск топ-10 похожих паттернов
- **Win Rate < 25%** → SKIP (плохой паттерн)

### Level 4: ML Confidence Check
- LSTM v2 предсказание направления цены
- Self-Learning ARF (9,690+ samples, 90.49% accuracy)
- **Confidence < 55%** → SKIP

### Level 5: Fee Profitability Check
- Расчёт комиссий: Maker 0.02% / Taker 0.055%
- **Gross Profit < 1.5× Total Fees** → SKIP
- Минимальный TP: ~0.4-0.8%

### Level 6: Futures Brain Multi-Agent
- **Conservative** (вес 3): confidence > 75%
- **Balanced** (вес 2): confidence > 60%
- **Aggressive** (вес 1): confidence > 55%
- **Score < 3/6** → SKIP

### Level 7: BTC Correlation Filter
- "King BTC Rule" - папа решает всё
- Блокирует LONG по альткоинам когда BTC падает (-0.3%+)
- Блокирует SHORT по альткоинам когда BTC растёт (+0.3%+)

## 🎮 Adaptive Strategy Selector

### Trend Following (CHOP ≤ 45)
- Следование за трендом
- RSI, MACD, EMA индикаторы
- Динамическое плечо 2-7x

### Mean Reversion (CHOP > 50)
- Торговля от экстремумов
- **BUY**: RSI < 30 (oversold)
- **SELL**: RSI > 70 (overbought)
- Проверка BTC корреляции для безопасности

## 💰 Limit Order Strategy (Maker Fee Optimization)

- **Order Type**: LIMIT (по умолчанию)
- **Maker Fee**: 0.02% (экономия 63% vs Taker)
- **Timeout**: 60 секунд
- **Fallback**: Market order если Limit не исполнился
- **Ожидаемая экономия**: $4.50-$13.50 в месяц

## 🚀 Быстрый старт

### 1. Настройка .env

```bash
cp .env.example .env
# Отредактируйте .env с вашими API ключами
```

**Необходимые ключи:**
```env
# Bybit API (Demo или Live)
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
BYBIT_TESTNET=true

# Gemini API (2 ключа для ротации моделей)
GOOGLE_API_KEY_2=your_key_2
GOOGLE_API_KEY_3=your_key_3

# Algion GPTFree - fallback для Strategic Brain
ALGION_BEARER_TOKEN=your_token

# CryptoPanic (опционально - для новостей)
CRYPTOPANIC_API_KEY=your_key

# Telegram (опционально)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 2. Запуск на сервере

```bash
# SSH на сервер
ssh root@88.210.10.145

# Переход в проект
cd /root/Bybit_Trader

# Запуск всех контейнеров
docker-compose up -d

# Проверка логов
docker logs bybit_bot -f
```

### 3. Dashboard

**Neural HUD**: http://88.210.10.145:8585/brain
- Real-time AI визуализация
- Strategic Brain reasoning
- ML predictions по каждому символу
- Gatekeeper статусы

**Main Dashboard**: http://88.210.10.145:8585
- Баланс и статистика
- Открытые позиции
- История сделок

## 📁 Структура проекта

```
Bybit_Trader/
├── core/
│   ├── hybrid_loop.py           # Главный торговый цикл
│   ├── bybit_api.py             # Bybit API v5 клиент
│   ├── strategic_brain.py       # Gemini 2.5 Flash + Algion
│   ├── ai_brain_local.py        # LSTM + Self-Learning
│   ├── futures_brain.py         # Multi-Agent система
│   ├── news_brain.py            # CryptoPanic + VADER
│   ├── ml_predictor_v2.py       # LSTM модель v2
│   ├── self_learning.py         # River ARF online learning
│   ├── scenario_tester.py       # Pattern matching
│   ├── strategic_compliance.py  # Закрытие позиций при смене режима
│   ├── state.py                 # GlobalBrainState (Neural HUD)
│   ├── sync_positions.py        # Синхронизация с биржей
│   └── position_monitor.py      # Мониторинг SL/TP
├── database/
│   ├── models.py                # SQLAlchemy модели
│   └── db.py                    # Database engine
├── web/
│   ├── app.py                   # Flask API
│   └── templates/
│       ├── index.html           # Main dashboard
│       └── brain.html           # Neural HUD
├── ml_training/
│   └── models/
│       └── bybit_lstm_model_v2.h5  # LSTM модель
├── ml_data/
│   └── self_learner.pkl         # Self-Learning модель
├── config.py                    # Конфигурация
├── requirements.txt             # Python зависимости
├── Dockerfile                   # Docker образ
└── docker-compose.yml           # Docker Compose конфигурация
```

## 🔧 Конфигурация (config.py)

### Основные параметры

```python
# Баланс и риски
futures_virtual_balance: float = 100.0  # Стартовый капитал
futures_leverage: int = 3               # Плечо 3x (SAFE MODE)
futures_risk_per_trade: float = 0.05    # 5% от баланса в маржу
futures_margin_mode: 'ISOLATED'         # Изолированная маржа

# Лимиты позиций
futures_max_open_positions: int = 1     # Макс. 1 позиция (SAFE MODE)
futures_min_confidence: float = 0.60    # Мин. 60% для LONG
futures_min_confidence_short: float = 0.60  # Мин. 60% для SHORT

# Стопы
stop_loss_pct: float = 1.5              # -1.5%
take_profit_pct: float = 3.0            # +3.0% (R:R = 1:2)

# Trailing Stop
trailing_stop_enabled: bool = True
trailing_activation_pct: float = 0.8    # Активация при +0.8%
trailing_callback_pct: float = 0.4      # Дистанция 0.4%

# Emergency Brake
hard_stop_loss_percent: float = 0.02    # 2% движения = EXIT
max_hold_time_minutes: int = 120        # 2 часа макс. (Zombie Killer)

# Limit Orders
order_type: 'LIMIT'                     # Maker стратегия
order_timeout_seconds: int = 60         # Таймаут 60s
maker_fee_rate: float = 0.0002          # 0.02%
taker_fee_rate: float = 0.00055         # 0.055%

# Торговые пары
futures_pairs: list = ["SOLUSDT"]       # SAFE MODE: только SOL
```

### Adaptive Strategy

```python
# CHOP пороги (с гистерезисом)
chop_flat_threshold: float = 50.0       # >= 50 = FLAT (Mean Reversion)
chop_trend_threshold: float = 45.0      # <= 45 = TREND (Trend Following)

# Mean Reversion параметры
rsi_oversold: int = 30                  # RSI < 30 = BUY
rsi_overbought: int = 70                # RSI > 70 = SELL
mean_reversion_min_confidence: float = 0.70
mean_reversion_btc_safety: bool = True  # Проверять BTC тренд

# BTC Correlation Filter
btc_correlation_enabled: bool = True
btc_correlation_threshold: float = 0.3  # 0.3% изменение BTC
btc_correlation_candles: int = 2        # 2 свечи (30 минут)
```

## 🔧 Команды управления

### Локально (только редактирование кода)
```bash
# Редактируем код в IDE
# НЕ запускаем Docker локально!
```

### На сервере

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск конкретного сервиса
docker-compose restart bot

# Логи
docker logs bybit_bot -f
docker logs bybit_dashboard -f
docker logs bybit_sync -f

# Пересборка после изменений
docker-compose build bot
docker-compose up -d bot

# Полная пересборка (если что-то сломалось)
docker-compose stop bot
docker rm -f bybit_bot
docker-compose build --no-cache bot
docker-compose up -d bot

# База данных
docker exec -it bybit_db psql -U bybit_user -d bybit_trader

# Проверка баланса
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT 100.0 + SUM(pnl) - SUM(fee_entry + fee_exit) as current_balance
FROM trades WHERE status = 'CLOSED' AND market_type = 'futures';
"
```

### Копирование файлов на сервер

```bash
# Один файл
scp Bybit_Trader/core/file.py root@88.210.10.145:/root/Bybit_Trader/core/

# Несколько файлов
scp Bybit_Trader/core/*.py root@88.210.10.145:/root/Bybit_Trader/core/
```

## 📊 Мониторинг

### Проверка здоровья системы

```bash
# Все контейнеры
docker ps | grep bybit

# Статистика сделок
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(pnl)::numeric, 2) as total_pnl,
    ROUND(AVG(pnl)::numeric, 2) as avg_pnl
FROM trades WHERE status = 'CLOSED' AND market_type = 'futures';
"

# Maker Fill Rate (Limit Orders)
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT 
    extra_data->>'order_type' as order_type,
    COUNT(*) as count,
    ROUND(AVG(fee_entry)::numeric, 4) as avg_entry_fee
FROM trades 
WHERE status = 'CLOSED' AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours'
GROUP BY extra_data->>'order_type';
"
```

### Ключевые метрики

- **CHOP < 50** - рынок в тренде (Trend Following)
- **CHOP > 50** - рынок во флэте (Mean Reversion)
- **Score >= 3/6** - Multi-Agent согласие
- **Win Rate > 40%** - система работает хорошо
- **Maker Fill Rate > 70%** - экономия на комиссиях

## ⚠️ Важные правила

### Deployment Rules

1. **НЕ запускать локально** - только на сервере!
2. **НЕ создавать bash скрипты** - выполнять команды по одной через SSH
3. **Всегда пересобирать контейнер** после изменения Python кода
4. **Проверять логи** после каждого деплоя
5. **Делать backup БД** перед крупными изменениями

### Trading Rules

1. **Demo режим** - не используем реальные деньги до 500+ сделок
2. **Stop Loss обязателен** - защита от больших убытков
3. **Изолированная маржа** - риск только на одну позицию
4. **Не торговать против BTC** - King BTC Rule
5. **Следить за комиссиями** - минимальный TP должен покрывать 1.5× fees

## 🔐 Безопасность

- ❌ НИКОГДА не коммить `.env`
- ❌ НИКОГДА не хардкодить API ключи
- ✅ Всегда использовать `settings` из `config.py`
- ✅ Проверять `.gitignore` перед коммитом
- ✅ Использовать изолированную маржу
- ✅ Устанавливать Stop Loss на каждую позицию

## 📈 Roadmap

- [x] Базовая инфраструктура
- [x] Bybit API интеграция
- [x] Технический анализ
- [x] Strategic Brain (Gemini + Algion)
- [x] LSTM ML модель
- [x] Self-Learning (River ARF)
- [x] Multi-Agent система
- [x] Neural HUD Dashboard
- [x] Limit Orders (Maker strategy)
- [x] Adaptive Strategy Selector
- [x] BTC Correlation Filter
- [ ] Telegram Commander (в разработке)
- [ ] Backtesting система
- [ ] Live Trading (после 500+ Demo сделок)

## 📚 Документация

- [Bybit API v5](https://bybit-exchange.github.io/docs/v5/intro)
- [Steering Rules](.kiro/steering/polymarket-project.md)
- [Deployment Logs](DEPLOYMENT_*.md)
- [System Status](SYSTEM_STATUS_*.md)

## 🤝 Contributing

Этот проект создан для личного использования. Не используйте на реальных деньгах без тщательного тестирования!

## ⚖️ License

MIT License - используйте на свой риск!

---

**Последнее обновление**: 26 декабря 2025  
**Версия**: 2.0 (Adaptive Scalper + Limit Orders)  
**Статус**: Demo Trading (Bybit Testnet)
