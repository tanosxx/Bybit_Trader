# Active Context - Текущий Контекст

## 📍 Текущий статус проекта

**Статус**: 🚧 **В разработке - базовая инфраструктура**

**Дата последнего обновления**: 26 ноября 2025

**Текущая фаза**: Создание базовой инфраструктуры

## 🎯 Активная задача

### Что происходит сейчас?
Создаем базовую инфраструктуру Bybit Trading Bot с переиспользованием кода из PolyAI_Simulator.

**ТЕКУЩИЙ ФОКУС**: Создание core модулей и trading loop

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

## 🔄 Следующие шаги

### Сегодня (26 ноября) - ДЕПЛОЙ!
1. ⏳ **Деплой на сервер**
   - Копирование файлов на 88.210.10.145
   - Запуск в Docker
   - Инициализация БД
   - Тест Bybit API
   - Тест Gemini API
   - Первый цикл торговли!

2. ⏳ **Мониторинг**
   - Проверка логов
   - Проверка Dashboard (http://88.210.10.145:8585)
   - Первые сделки

### Завтра (27 ноября)
1. ⏳ **Multi-Agent System** - переиспользовать из PolyAI_Simulator
2. ⏳ **Position Sizer** - динамический размер позиций
3. ⏳ **Risk Manager** - управление рисками
4. ⏳ **Telegram Notifier** - уведомления

### Через 2-3 дня
1. ⏳ **Тестирование на виртуальном балансе**
2. ⏳ **Сбор статистики**
3. ⏳ **Оптимизация параметров**

## 🐛 Известные проблемы

### Критические
- Нет критических проблем

### Некритические
- ⚠️ **Gemini может иногда тупить** - есть fallback на OpenRouter
- ⚠️ **Нужно протестировать Bybit API** - пока не запускали

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
