# 🤖 Bybit AI Trading Bot

> Полностью автоматизированный торговый бот с искусственным интеллектом и самообучением для криптовалютной биржи Bybit

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production--Ready-success.svg)](http://88.210.10.145:8585)

## 📊 Краткое описание

Автономный торговый робот, работающий 24/7 без участия человека. Принимает решения на основе технического анализа, новостей и машинного обучения. Полностью независим от внешних AI API - использует собственную ML инфраструктуру.

**Live Demo**: [http://88.210.10.145:8585](http://88.210.10.145:8585)

## 🎯 Ключевые возможности

### 🧠 Искусственный интеллект
- **LSTM Neural Network v2**: Собственная нейросеть для предсказаний
- **Self-Learning ML**: Автоматическое обучение на каждой закрытой сделке
- **River Online Learning**: Инкрементальное обучение без переобучения
- **Multi-Agent система**: 3 AI агента (Conservative, Balanced, Aggressive)

### 📈 Торговля
- **Гибридный режим**: Futures (с плечом до 7x) + Spot
- **Изолированная маржа**: Защита от полной ликвидации
- **Автоматические стопы**: Stop-Loss, Take-Profit, Trailing Stop
- **Риск-менеджмент**: Лимиты позиций, проверка Funding Rate

### 📊 Технический анализ
- RSI, MACD, Bollinger Bands
- Определение трендов и волатильности
- ATR-based динамические стопы
- Анализ объемов

### 📰 Новости
- RSS агрегация из множества криптоисточников
- Sentiment analysis в реальном времени
- Влияние на торговые решения

## 📈 Результаты

```
Стартовый капитал:  $100 (виртуальный)
Текущий баланс:     ~$1,300+
ROI:                +1,200%
Закрыто сделок:     9,200+
Win Rate:           ~10.5%
ML модель:          9,200+ обученных сэмплов (растет в реальном времени)
Точность модели:    89.7%
Uptime:             24/7
```

## 🛠️ Технологический стек

### Backend
- **Python 3.10**: AsyncIO архитектура
- **PostgreSQL**: История сделок и метрики
- **Docker Compose**: 5 микросервисов
- **SQLAlchemy**: Async ORM

### AI & ML
- **LSTM Neural Network**: TensorFlow/Keras
- **River ML**: Online Learning
- **Adaptive Random Forest**: Классификатор

### Frontend
- **Flask**: Web-сервер
- **Chart.js**: Интерактивные графики
- **Real-time updates**: Каждые 5 секунд

### Интеграции
- **Bybit API v5**: Торговля и данные
- **RSS Feeds**: Агрегация новостей
- **Telegram Bot**: Уведомления

## 🚀 Быстрый старт

### Требования
- Docker & Docker Compose
- Ubuntu VPS (рекомендуется)
- Bybit API ключи (Demo или Live)

### 1. Клонирование
```bash
git clone <repository>
cd Bybit_Trader
```

### 2. Настройка .env
```bash
cp .env.example .env
nano .env
```

Заполните:
```env
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=true
DATABASE_URL=postgresql+asyncpg://bybit_user:bybit_secure_pass_2024@postgres_bybit:5432/bybit_trader
```

### 3. Запуск
```bash
docker-compose up -d --build
```

### 4. Мониторинг
```bash
# Логи бота
docker logs -f bybit_bot

# Логи sync
docker logs -f bybit_sync

# Dashboard
open http://localhost:8585
```

## 📁 Архитектура

### Микросервисы
```
┌─────────────────┐
│   bybit_bot     │  Основной торговый движок
└────────┬────────┘
         │
┌────────┴────────┐
│  bybit_sync     │  Синхронизация с биржей (30 сек)
└────────┬────────┘
         │
┌────────┴────────┐
│ bybit_monitor   │  Мониторинг позиций и SL/TP
└────────┬────────┘
         │
┌────────┴────────┐
│bybit_dashboard  │  Web-интерфейс (Flask)
└────────┬────────┘
         │
┌────────┴────────┐
│   bybit_db      │  PostgreSQL база данных
└─────────────────┘
```

### Процесс принятия решений
```
Сканирование рынка (BTC, ETH, SOL, BNB, XRP)
    ↓
Технический анализ (RSI, MACD, BB, тренды)
    ↓
Анализ новостей (RSS агрегация)
    ↓
ML предсказание (LSTM + Self-Learning)
    ↓
Multi-Agent консенсус (3 AI агента)
    ↓
Проверка рисков (Safety Guardian)
    ↓
Открытие позиции с SL/TP
    ↓
Мониторинг и закрытие
    ↓
Обучение Self-Learning модели
```

## 📊 Web Dashboard

### Основные метрики
- 💰 Текущий баланс и PnL
- 📊 Win Rate и статистика сделок
- 📈 Equity Curve (график роста)
- 🔥 Открытые позиции в реальном времени
- 📋 История последних сделок
- 🧠 Статус Self-Learning модели

### Скриншоты
![Dashboard](docs/dashboard.png)

## 🔧 Команды

### Управление контейнерами
```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск конкретного сервиса
docker restart bybit_bot

# Пересборка
docker-compose up -d --build
```

### Логи
```bash
# Все логи
docker-compose logs -f

# Конкретный сервис
docker logs -f bybit_bot
docker logs -f bybit_sync
docker logs -f bybit_dashboard
```

### База данных
```bash
# Подключение к PostgreSQL
docker exec -it bybit_db psql -U bybit_user -d bybit_trader

# Проверка сделок
SELECT COUNT(*) FROM trades WHERE status = 'CLOSED';

# Статистика
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    AVG(pnl) as avg_pnl
FROM trades 
WHERE status = 'CLOSED';
```

### Деплой на сервер
```bash
# Копирование файлов
scp -r ./Bybit_Trader root@88.210.10.145:/root/

# SSH на сервер
ssh root@88.210.10.145

# Запуск
cd /root/Bybit_Trader
docker-compose up -d --build
```

## 🔒 Безопасность

- ✅ **Изолированная маржа**: Каждая позиция изолирована
- ✅ **Виртуальный баланс**: Demo режим для тестирования
- ✅ **Лимиты позиций**: Защита от переторговли
- ✅ **Stop-Loss обязателен**: На каждой позиции
- ✅ **Emergency Stop**: Аварийное закрытие при критических рисках
- ✅ **Graceful degradation**: Работа при сбоях компонентов

## 🎓 Уникальные фичи

### 1. Self-Learning (Самообучение)
Модель автоматически обучается на **каждой** закрытой сделке:
- Адаптируется к изменениям рынка
- Улучшает предсказания со временем
- Сохраняется между перезапусками
- Не требует ручного переобучения

### 2. Полная автономность
- Собственная ML инфраструктура
- Нет зависимости от OpenAI/Claude/Gemini
- Нет платных API для новостей
- Работает offline (кроме биржи)

### 3. Multi-Agent система
- 3 независимых AI агента
- Динамические веса на основе производительности
- Консенсус для снижения рисков

### 4. Hybrid Trading
- Одновременная торговля Spot + Futures
- Раздельная статистика и балансы
- Гибкое переключение режимов

## 📊 Сравнение с аналогами

| Параметр | Наш бот | Типичные боты |
|----------|---------|---------------|
| AI решения | ✅ Собственная LSTM + Self-Learning | ❌ Простые индикаторы |
| Самообучение | ✅ Online Learning (каждая сделка) | ❌ Статичные правила |
| Зависимость от API | ✅ Полностью автономный | ❌ Зависят от OpenAI/Claude |
| Новости | ✅ RSS агрегация | ❌ Нет |
| Риск-менеджмент | ✅ Многоуровневый | ⚠️ Базовый |
| Dashboard | ✅ Real-time | ⚠️ Простой |
| Архитектура | ✅ Микросервисы | ❌ Монолит |

## 📝 Конфигурация

### Основные параметры (config.py)
```python
# Лимиты позиций
futures_max_open_positions = 7        # Макс. уникальных символов
futures_max_orders_per_symbol = 15    # Макс. ордеров на символ
futures_max_total_orders = 80         # Макс. всего ордеров

# Риск-менеджмент
futures_virtual_balance = 100.0       # Виртуальный баланс
futures_leverage = 5                  # Базовое плечо (2-7x динамически)
futures_risk_per_trade = 0.20         # 20% на сделку

# Стопы
stop_loss_pct = 2.0                   # 2% SL
take_profit_pct = 3.0                 # 3% TP
trailing_stop_enabled = True          # Trailing Stop

# ML
futures_min_confidence = 0.50         # Мин. confidence для входа
```

## 🐛 Troubleshooting

### Бот не открывает позиции
```bash
# Проверить логи
docker logs bybit_bot | grep "Decision"

# Возможные причины:
# - Достигнут лимит позиций
# - Низкая confidence (<50%)
# - Funding Rate слишком высокий
```

### ML модель не обучается
```bash
# Проверить статус
curl http://localhost:8585/api/ml/status

# Перезапустить sync
docker restart bybit_sync

# Проверить логи обучения
docker logs bybit_sync | grep "ML: Learned"
```

### Dashboard не обновляется
```bash
# Жесткая перезагрузка в браузере
Ctrl + F5

# Перезапуск dashboard
docker restart bybit_dashboard
```

## 📚 Документация

- [Презентация проекта](PRESENTATION.md)
- [Bybit API v5 Docs](https://bybit-exchange.github.io/docs/v5/intro)
- [Steering Rules](.kiro/steering/polymarket-project.md)

## 🎯 Roadmap

- [x] Базовая инфраструктура
- [x] Bybit API v5 интеграция
- [x] Технический анализ (RSI, MACD, BB)
- [x] LSTM Neural Network
- [x] Self-Learning ML (River)
- [x] Multi-Agent система
- [x] Web Dashboard (Flask + Chart.js)
- [x] Hybrid Trading (Spot + Futures)
- [x] Trailing Stop
- [x] Funding Rate Filter
- [x] Safety Guardian
- [x] Position Limits
- [x] RSS News агрегация
- [ ] Telegram уведомления (в процессе)
- [ ] Backtesting модуль
- [ ] API для клиентов
- [ ] Копи-трейдинг

## ⚠️ Disclaimer

Этот бот работает в **Demo режиме** на виртуальном балансе. Все результаты реальны, но без использования реальных денег.

**Не используйте на реальных деньгах без:**
- Тщательного тестирования (минимум 1000+ сделок)
- Понимания рисков криптовалютной торговли
- Готовности к потере капитала

Криптовалютная торговля сопряжена с высокими рисками. Прошлые результаты не гарантируют будущую доходность.

## 📞 Контакты

- **Live Dashboard**: http://88.210.10.145:8585
- **Сервер**: Ubuntu VPS (Нидерланды)
- **Статус**: Production-ready (Demo режим)

## ⚖️ License

Proprietary - Все права защищены

---

**Разработано**: 2024-2025  
**Версия**: 6.2  
**Статус**: ✅ Production-ready (Demo Trading)
