# Bybit Trading Bot 🤖

Автоматический торговый бот для Bybit с AI анализом, техническими индикаторами и Multi-Agent System.

## 🎯 Особенности

- **Технический анализ**: RSI, MACD, Bollinger Bands, EMA
- **AI анализ**: Gemini 1.5 Flash (FREE tier!) + OpenRouter (Claude/GPT fallback)
- **Multi-Agent System**: Conservative, Balanced, Aggressive агенты
- **Risk Management**: Stop Loss, Take Profit, лимиты позиций
- **Виртуальный баланс**: Торговля на реальных данных без риска
- **Dashboard**: Streamlit интерфейс для мониторинга
- **Telegram**: Уведомления о сделках (опционально)

## 📊 Стратегия

- **Тип**: Scalping / Day Trading
- **Пары**: BTC/USDT, ETH/USDT
- **Размер позиции**: 10-20% от баланса
- **Stop Loss**: -2%
- **Take Profit**: +3%
- **Интервал**: 60 секунд

## 🚀 Быстрый старт

### 1. Настройка .env

```bash
cp .env.example .env
# Отредактируйте .env с вашими API ключами
```

### 2. Запуск на сервере

```bash
# SSH на сервер
ssh root@88.210.10.145

# Переход в проект
cd /root/Bybit_Trader

# Запуск
docker-compose up -d

# Логи
docker logs bybit_bot -f
```

### 3. Dashboard

Откройте в браузере: http://88.210.10.145:8585

## 📁 Структура проекта

```
Bybit_Trader/
├── core/
│   ├── bybit_api.py          # Bybit API v5
│   ├── technical_analyzer.py # RSI, MACD, BB
│   ├── ai_brain.py           # Gemini + OpenRouter
│   ├── trader.py             # Виртуальный трейдер
│   └── loop.py               # Главный цикл
├── database/
│   ├── models.py             # Trade, Candle, SystemLog
│   └── db.py                 # PostgreSQL
├── web/
│   └── dashboard.py          # Streamlit dashboard
├── memory-bank/              # Контекст проекта
├── .kiro/steering/           # Правила для AI
└── docker-compose.yml        # Docker конфигурация
```

## 🔧 Команды

### Локально (только редактирование)
```bash
# Редактируем код в IDE
```

### На сервере
```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Логи бота
docker logs bybit_bot -f

# Логи dashboard
docker logs bybit_dashboard -f

# БД
docker exec -it bybit_db psql -U bybit_user -d bybit_trader
```

### Копирование файлов
```bash
# Из Windows на сервер
scp file.py root@88.210.10.145:/root/Bybit_Trader/path/
```

## 📊 Мониторинг

- **Dashboard**: http://88.210.10.145:8585
- **PostgreSQL**: localhost:5435 (с сервера)
- **Логи**: `docker logs bybit_bot -f`

## ⚠️ Важно

1. **Виртуальный баланс** - не используем реальные деньги до 100+ сделок
2. **Gemini FREE tier** - может иметь rate limits
3. **Stop Loss обязателен** - защита от больших убытков
4. **Не запускать локально** - только на сервере!

## 🎓 Обучение

### Переиспользование кода из PolyAI_Simulator
- Multi-Agent System (будет добавлен)
- Position Sizer (будет добавлен)
- Risk Manager (будет добавлен)
- Telegram Notifier (будет добавлен)

## 📈 Целевые метрики

- Винрейт: >55%
- Средняя прибыль: +1.5% за сделку
- Средний убыток: -1.0% за сделку
- Risk/Reward: 1:1.5
- Месячная доходность: +10-20%

## 🔗 Документация

- [Bybit API v5](https://bybit-exchange.github.io/docs/v5/intro)
- [Memory Bank](memory-bank/)
- [Steering Rules](.kiro/steering/bybit-project.md)

## 📝 Roadmap

- [x] Базовая инфраструктура
- [x] Bybit API интеграция
- [x] Технический анализ
- [x] AI Brain (Gemini + OpenRouter)
- [x] Trading Loop
- [ ] Dashboard
- [ ] Multi-Agent System
- [ ] Telegram уведомления
- [ ] ML модель (LSTM)
- [ ] Backtesting

## 🤝 Contributing

Этот проект создан для личного использования. Не используйте на реальных деньгах без тщательного тестирования!

## ⚖️ License

MIT License - используйте на свой риск!
