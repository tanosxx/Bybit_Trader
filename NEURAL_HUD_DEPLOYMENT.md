# Neural HUD - Deployment Guide

## 📋 Что сделано

Создана новая страница **Neural HUD** для визуализации процесса принятия решений ботом в реальном времени.

### Новые файлы:

1. **`core/state.py`** - GlobalBrainState (Singleton)
   - Хранит текущие "мысли" всех AI модулей в оперативной памяти
   - Обновляется в реальном времени при работе бота
   - НИКАКИХ запросов к БД - только in-memory данные

2. **`web/templates/brain.html`** - Frontend (Cyberpunk style)
   - Темная тема с неоновыми эффектами
   - Auto-refresh каждые 2 секунды
   - Визуализация Strategic Brain, News, ML predictions, Gatekeeper

3. **Обновлены существующие файлы:**
   - `core/strategic_brain.py` - добавлено обновление GlobalBrainState
   - `core/ai_brain_local.py` - добавлено обновление GlobalBrainState в ключевых точках
   - `web/app.py` - добавлены эндпоинты `/brain` и `/api/brain_live`

## 🎯 Что показывает Neural HUD

### 1. Strategic Brain (Генерал)
- Текущий режим рынка: BULL_RUSH / BEAR_CRASH / SIDEWAYS / UNCERTAIN
- Объяснение от Claude 3.5 Sonnet
- Крупный дисплей с цветовой индикацией

### 2. Market Indicators (Левая колонка)
- **News Sentiment**: VADER score (-1.0 to +1.0) с визуальной шкалой
- **Latest Headline**: Последняя новость
- **Bot Status**: ACTIVE / OFFLINE (зелёная/красная лампочка)
- **Last Scan**: Время последнего сканирования
- **Total Decisions**: Количество принятых решений
- **Active Positions**: Количество открытых позиций

### 3. Trading Pairs (Правая колонка)
Карточки для каждой монеты (BTC, ETH, SOL, BNB, XRP):
- **Текущая цена**
- **RSI** (индикатор перекупленности/перепроданности)
- **CHOP** (индикатор флэта)
- **ML Prediction**: BUY/SELL/HOLD + confidence (progress bar)
- **Predicted Change**: Ожидаемое изменение цены в %
- **Gatekeeper Status**: PASS (зелёный) или BLOCK: Reason (красный)
- **Position Indicator**: Если позиция открыта

## 🚀 Deployment Instructions

### 1. Копируем файлы на сервер

```bash
# Новый файл - GlobalBrainState
scp Bybit_Trader/core/state.py root@88.210.10.145:/root/Bybit_Trader/core/

# Обновлённые модули
scp Bybit_Trader/core/strategic_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/

# Flask app
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/

# HTML template
scp Bybit_Trader/web/templates/brain.html root@88.210.10.145:/root/Bybit_Trader/web/templates/
```

### 2. Пересобираем контейнеры

```bash
# Останавливаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot dashboard"

# Удаляем старые контейнеры (ОБЯЗАТЕЛЬНО!)
ssh root@88.210.10.145 "docker rm -f bybit_bot bybit_dashboard"

# Пересобираем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot dashboard"

# Запускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot dashboard"
```

### 3. Проверяем логи

```bash
# Логи бота (должны быть обновления GlobalBrainState)
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100"

# Логи dashboard
ssh root@88.210.10.145 "docker logs bybit_dashboard --tail 50"
```

### 4. Открываем Neural HUD

**URL:** http://88.210.10.145:8585/brain

Страница должна:
- Загрузиться с тёмной темой (Cyberpunk style)
- Показать "INITIALIZING..." в Strategic Brain
- Начать обновляться каждые 2 секунды
- Показать карточки для 5 монет (BTC, ETH, SOL, BNB, XRP)

## 🔍 Как работает интеграция

### Обновление данных в модулях:

**Strategic Brain** (`core/strategic_brain.py`):
```python
# После получения ответа от Claude
state = get_global_brain_state()
state.update_strategic(detected_regime, regime_raw[:200])
```

**AI Brain** (`core/ai_brain_local.py`):
```python
# При анализе CHOP
state.update_market_data(symbol, chop=chop)

# При получении ML сигнала
state.update_ml_prediction(symbol, ml_decision, ml_confidence, change_pct)

# При обновлении новостей
state.update_news(sentiment=news_data['score'], headline=headline, count=news_count)

# При проверке Gatekeeper
state.update_gatekeeper(symbol, f"BLOCK: CHOP {chop:.1f}")
```

### API Endpoint:

**`/api/brain_live`** возвращает:
```json
{
  "strategic": {
    "regime": "SIDEWAYS",
    "reason": "Market regime: SIDEWAYS",
    "last_update": "2025-12-05T12:00:00"
  },
  "news": {
    "sentiment": 0.15,
    "latest_headline": "Bitcoin holds above $40k",
    "count": 5,
    "last_update": "2025-12-05T12:00:00"
  },
  "market": {
    "chop_index": {"BTCUSDT": 45.2, "ETHUSDT": 52.1},
    "rsi_values": {"BTCUSDT": 58.3, "ETHUSDT": 62.1},
    "current_prices": {"BTCUSDT": 42150.50, "ETHUSDT": 2250.30}
  },
  "ml_predictions": {
    "BTCUSDT": {
      "decision": "BUY",
      "confidence": 0.68,
      "change_pct": 1.2,
      "timestamp": "2025-12-05T12:00:00"
    }
  },
  "gatekeeper": {
    "BTCUSDT": "PASS",
    "ETHUSDT": "BLOCK: CHOP 65.3"
  },
  "positions": {
    "active": ["BTCUSDT"],
    "count": 1
  },
  "system": {
    "bot_running": true,
    "last_scan": "2025-12-05T12:00:00",
    "total_decisions": 42
  }
}
```

## 🎨 Дизайн особенности

- **Cyberpunk theme**: Тёмный фон с неоновыми акцентами (#00ff88, #00ccff, #ff00ff)
- **Responsive**: Адаптируется под мобильные устройства
- **Animations**: Пульсация заголовка, мигание индикаторов
- **Color coding**:
  - BULL_RUSH: Зелёный градиент
  - BEAR_CRASH: Красный градиент
  - SIDEWAYS: Оранжевый градиент
  - UNCERTAIN: Серый градиент
- **Real-time updates**: Без перезагрузки страницы (AJAX)

## 🐛 Troubleshooting

### Проблема: Страница не загружается
**Решение:**
```bash
# Проверить логи dashboard
docker logs bybit_dashboard

# Проверить что файл brain.html скопирован
docker exec bybit_dashboard ls -la /app/web/templates/brain.html
```

### Проблема: Данные не обновляются
**Решение:**
```bash
# Проверить что бот работает
docker logs bybit_bot --tail 50 | grep "GlobalBrainState"

# Проверить API endpoint
curl http://88.210.10.145:8585/api/brain_live
```

### Проблема: Показывает "INITIALIZING..." постоянно
**Причина:** Бот ещё не начал сканирование или GlobalBrainState не обновляется

**Решение:**
```bash
# Проверить что бот активен
docker logs bybit_bot | grep "Local Brain analyzing"

# Дождаться первого сканирования (может занять до 5 минут)
```

## 📊 Performance

- **Memory overhead**: ~1-2 MB (GlobalBrainState в памяти)
- **API response time**: <10ms (нет запросов к БД)
- **Frontend refresh**: 2 секунды (настраивается в HTML)
- **No database load**: Все данные из оперативной памяти

## 🔮 Future Enhancements

Возможные улучшения:
1. **WebSocket** вместо polling для instant updates
2. **Historical charts** для ML confidence over time
3. **Sound alerts** при важных событиях (PANIC_SELL, BULL_RUSH)
4. **Mobile app** версия
5. **Customizable refresh rate** через UI
6. **Export data** в JSON/CSV для анализа

---

**Дата создания:** 2025-12-05  
**Версия:** 1.0  
**Статус:** Ready for deployment
