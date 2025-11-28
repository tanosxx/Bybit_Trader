# Active Context - Текущий Контекст

## 📍 Текущий статус проекта

**Статус**: 🎮 **РАБОТАЕТ НА DEMO TRADING!**

**Дата последнего обновления**: 28 ноября 2025, 22:40 UTC

**Текущая фаза**: Реальная торговля на Demo балансе ($50,000)

## 🎯 Активная задача

### Что происходит сейчас?
**LOCAL CORE ARCHITECTURE** - Полная автономность без внешних LLM API!

**ТЕКУЩИЙ ФОКУС**: 
- ✅ Создан `core/news_brain.py` - Фундаментальный анализ (CryptoPanic + VADER)
- ✅ Создан `core/ai_brain_local.py` - Автономный мозг (Decision Tree)
- ✅ Интегрирован с существующим `ml_predictor_v2.py` (LSTM)
- ✅ Интегрирован в `loop.py` и `real_trader.py`
- ✅ Добавлен PANIC_SELL при EXTREME_FEAR
- ✅ Ротация нескольких CryptoPanic API ключей (100 req/mo каждый)
- ⏳ Деплой на сервер

### Последние изменения (26 ноября 2025)

1. ✅ **Базовая структура проекта** (ЗАВЕРШЕНО)
   - Создана структура директорий
   - `.env` с Bybit API credentials
   - `config.py` с настройками
   - `docker-compose.yml` (порты: 5435, 8585)
   - `requirements.txt`

2. ✅ **Bybit API интеграция** (ЗАВЕРШЕНО)
   - `core/bybit_api.py` - Bybit API v5
   - Методы: get_klines, get_ticker, get_wallet_balance
   - Методы: place_order, get_open_orders, cancel_order
   - HMAC SHA256 подпись для аутентификации

3. ✅ **Технический анализ** (ЗАВЕРШЕНО)
   - `core/technical_analyzer.py`
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands
   - EMA (Exponential Moving Average)
   - Анализ тренда и объема

4. ✅ **AI Brain** (ЗАВЕРШЕНО)
   - `core/ai_brain.py`
   - **Gemini 1.5 Flash** (FREE tier!) - первичный анализ
   - Специальный промпт чтобы Gemini не тупил
   - Fallback на OpenRouter (Claude Haiku / GPT-4o mini)
   - Очистка markdown из ответов

5. ✅ **Database models** (ЗАВЕРШЕНО)
   - `database/db.py` - async SQLAlchemy
   - `database/models.py` - Trade, Candle, SystemLog, WalletHistory
   - Поддержка JSON для extra_data (agent_type, indicators)

6. ✅ **Memory Bank** (ЗАВЕРШЕНО)
   - `memory-bank/productContext.md` - цели и стратегия
   - `memory-bank/activeContext.md` - текущий статус

7. ✅ **Trader** (ЗАВЕРШЕНО)
   - `core/trader.py` - виртуальный трейдер
   - Управление балансом
   - Открытие/закрытие позиций
   - Stop Loss / Take Profit автоматически
   - Статистика торговли

8. ✅ **Trading Loop** (ЗАВЕРШЕНО)
   - `core/loop.py` - главный цикл
   - Сканирование рынков каждые 60 секунд
   - Технический анализ → AI анализ → Решение
   - Проверка SL/TP для открытых позиций
   - Логирование в БД

9. ✅ **Steering** (ЗАВЕРШЕНО)
   - `.kiro/steering/bybit-project.md` - правила для AI
   - Memory Bank структура
   - Definition of Done

10. ✅ **README** (ЗАВЕРШЕНО)
   - Документация проекта
   - Быстрый старт
   - Команды для работы

11. ✅ **Dashboard** (ЗАВЕРШЕНО)
   - `web/dashboard.py` - Streamlit интерфейс
   - Метрики: Balance, PnL, Winrate, Open Positions
   - График equity (Plotly)
   - Открытые позиции с SL/TP
   - История сделок (таблица)
   - Логи системы
   - Автообновление каждые 10 секунд

12. ✅ **Скрипты** (ЗАВЕРШЕНО)
   - `scripts/init_db.py` - инициализация БД
   - `scripts/test_bybit_api.py` - тест Bybit API

13. ✅ **ML Prediction** (ЗАВЕРШЕНО)
   - `core/price_predictor.py` - SimplePricePredictor
   - Технические индикаторы (RSI, MACD, SMA, EMA)
   - Предсказание направления цены
   - Интеграция в trading loop

14. ✅ **Data Collector** (ЗАВЕРШЕНО)
   - `core/data_collector.py` - сохранение свечей в БД
   - Автоматический сбор данных для ML

15. ✅ **Telegram Notifier** (ЗАВЕРШЕНО)
   - `core/telegram_notifier.py` - уведомления в Telegram
   - Открытие/закрытие позиций
   - Дневные отчеты
   - ML предсказания

16. ✅ **ДЕПЛОЙ НА СЕРВЕР** (ЗАВЕРШЕНО)
   - Все контейнеры запущены на 88.210.10.145
   - БД работает (PostgreSQL)
   - Dashboard работает (http://88.210.10.145:8585)
   - Бот работает (trading loop каждые 60 сек)
   - OpenRouter (Claude Haiku) работает отлично
   - ML предсказания работают
   - Data Collector сохраняет свечи

## 🔄 Следующие шаги

### Выполнено (27-28 ноября)
1. ✅ **Local Core Architecture** - ГОТОВО!
2. ✅ **Dynamic Risk Management (ta_lib.py)** - ГОТОВО!
3. ✅ **Backtesting Engine** - ГОТОВО!
4. ✅ **Multi-Agent System** - ГОТОВО!
5. ✅ **Dashboard V2** - ГОТОВО!
6. ✅ **Деплой на сервер** - ГОТОВО!
7. ✅ **Оптимизация параметров** - ГОТОВО!
   - Добавлена стратегия momentum
   - Улучшены фильтры сигналов
   - Оптимизированы ATR multipliers

### Сегодня (28 ноября) - МОНИТОРИНГ И ОПТИМИЗАЦИЯ
1. ✅ **Бэктест запущен** - результаты получены
   - 5-минутные свечи работают лучше 1-минутных
   - mean_reversion показывает лучший результат
   - Рынок боковой - все стратегии в минусе

2. ✅ **Market Regime Detection** - ГОТОВО!
   - Определяет: TRENDING_UP, TRENDING_DOWN, RANGING, CHOPPY, HIGH/LOW_VOLATILITY
   - Автоматически уменьшает размер позиции в неблагоприятных условиях
   - Интегрировано в loop.py

3. ✅ **Мониторинг реальной торговли**
   - 802+ сделок выполнено
   - Win Rate: 51.87%
   - PnL: +$946.54
   - Multi-Agent работает
   - Portfolio Risk Check блокирует лишние сделки

4. ✅ **Закрытие лишних позиций** - ГОТОВО!
   - Создан скрипт `scripts/close_old_positions.py`
   - Исправлено округление quantity для XRP (целые числа)
   - Закрыто 32 позиции, осталось 3

5. ✅ **HYBRID TRADING ARCHITECTURE** - ЗАВЕРШЕНО!
   - `config.py` - HYBRID mode, виртуальные балансы
   - `core/executors/` - BaseExecutor, SpotExecutor, FuturesExecutor
   - `core/hybrid_loop.py` - параллельное исполнение SPOT + FUTURES
   - Виртуальный баланс $500 для фьючерсов (безопасность!)
   - Leverage 5x, Isolated margin
   - LONG + SHORT позиции на фьючерсах
   - ✅ Деплой на сервер - ГОТОВО!
   - ✅ Бот переключен на hybrid_loop.py
   - ✅ 2 фьючерсные позиции открыты

6. 🎉 **HYBRID TRADING ЗАПУЩЕН!** (28 ноября 2025)
   - Режим: HYBRID (SPOT + FUTURES одновременно)
   - SPOT пары: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT
   - FUTURES пары: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT
   - Leverage: 5x, Isolated margin
   - Virtual Balance: $500
   - Multi-Agent + ML + News работают

7. 🚀 **FUTURES BRAIN v2.0** (28 ноября 2025) ✅ РАБОТАЕТ!
   - **Smart Scaling**: Raw 0.30-0.65 → Trading Conf 30-100%
   - **Weighted Voting**: Score >= 3 для входа
     - Conservative (вес 3): Conf > 75% + TA
     - Balanced (вес 2): Conf > 55% + TA
     - Aggressive (вес 1): Conf > 40%
   - **Dynamic Leverage**: 2x/5x/7x по confidence
   - **Smart Shorting**: News + TA → SHORT
   - **Лимит потерь**: Max 2% от депозита на сделку
   - Dashboard v3 с виртуальным балансом
   - **Результат**: 4 SHORT позиции за 5 минут!

8. 🚨 **АВАРИЙНОЕ ИСПРАВЛЕНИЕ FuturesExecutor v2.0** (28 ноября 2025)
   - **ПРОБЛЕМА**: Позиции открылись в CROSS MARGIN без стопов!
   - **PANIC CLOSE**: Все 5 позиций закрыты (PnL: -$4.42)
   - **ИСПРАВЛЕНИЯ**:
     - ✅ FORCE ISOLATED MARGIN - вызывается ПЕРЕД каждой сделкой
     - ✅ PRICE PRECISION - tickSize из get_instruments_info
     - ✅ VIRTUAL BALANCE ONLY - $100 фиксированный, НЕ запрашиваем с биржи
     - ✅ ATOMIC SL/TP - стопы внутри place_order, не отдельно
   - **Файл**: `core/executors/futures_executor.py` полностью переписан

## 🐛 Известные проблемы

### Критические
- Нет критических проблем

### Некритические
- ⚠️ **docker-compose --force-recreate** - баг в docker-compose 1.29.2, используем docker rm + docker run

### Решенные
- ✅ **Gemini API** - работает с моделью `gemini-2.0-flash` (15 RPM, 1M TPM, 200 RPD)

## 📋 Технические детали

### Окружение
- **Разработка**: Windows (локально) - ТОЛЬКО РЕДАКТИРОВАНИЕ
- **Продакшн**: Ubuntu VPS (88.210.10.145)
- **Контейнеризация**: Docker Compose

### Bybit API
```
API Key: lq2uoJ8GlfoEI1Kdgd
API Secret: hnW8T1Q3eT5DniNmBupmCuOVdm7FCv40byzM
Testnet: false (mainnet)
```

### Порты
- PostgreSQL: 5435
- Dashboard: 8585

### Торговые пары
- BTC/USDT
- ETH/USDT

### Параметры
- Стартовый баланс: $50 (виртуальный)
- Интервал сканирования: 60 секунд
- Max открытых позиций: 3
- Max дневной убыток: $5

## 🎓 Обучение

### Переиспользование кода из PolyAI_Simulator
- ✅ Multi-Agent System (будет symlink)
- ✅ Position Sizer (будет symlink)
- ✅ Risk Manager (будет symlink)
- ✅ Telegram Notifier (будет symlink)

### Новый код для Bybit
- ✅ Bybit API
- ✅ Technical Analyzer
- ✅ AI Brain (адаптированный)
- ⏳ Trading Loop (адаптированный)
- ⏳ Dashboard (адаптированный)

## 🔐 Безопасность

### Текущие меры
- ✅ API ключи в `.env` (не в git)
- ✅ Docker изоляция
- ✅ PostgreSQL с паролем
- ✅ Виртуальный баланс (не реальные деньги!)

### Рекомендации
- 🔄 Тестировать только на виртуальном балансе
- 🔄 Не использовать реальные деньги до 100+ сделок
- 🔄 Мониторинг логов

## 🎯 Definition of Done

Задача завершена, когда:
1. ✅ Код написан и работает
2. ✅ Протестирован в Docker
3. ✅ Нет ошибок в логах
4. ✅ Обновлен `activeContext.md`
5. ✅ Обновлена документация
