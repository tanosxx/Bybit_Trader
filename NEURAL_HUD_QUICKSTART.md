# Neural HUD - Quick Start 🚀

## Что это?

**Neural HUD** - визуализация "мозга" торгового бота в реальном времени.  
Видишь ВСЕ решения AI: Strategic Brain (Claude), ML predictions, Gatekeeper, News sentiment.

## Деплой за 30 секунд

```bash
# Запусти этот скрипт (он всё сделает сам)
./Bybit_Trader/DEPLOY_NEURAL_HUD.sh
```

Скрипт:
1. Скопирует файлы на сервер
2. Пересоберёт контейнеры
3. Запустит бот и dashboard
4. Покажет логи

## Открыть Neural HUD

**URL:** http://88.210.10.145:8585/brain

## Что увидишь

### 1. Strategic Brain (Генерал)
Крупный дисплей с режимом рынка:
- **BULL_RUSH** (зелёный) - только LONG
- **BEAR_CRASH** (красный) - только SHORT
- **SIDEWAYS** (оранжевый) - всё разрешено
- **UNCERTAIN** (серый) - не торгуем

### 2. Market Indicators (слева)
- **News Sentiment** - настроение рынка (-1 to +1)
- **Bot Status** - работает или нет
- **Last Scan** - когда последний раз сканировал
- **Total Decisions** - сколько решений принял
- **Active Positions** - сколько позиций открыто

### 3. Trading Pairs (справа)
Карточки для BTC, ETH, SOL, BNB, XRP:
- Текущая цена
- RSI и CHOP индикаторы
- ML решение (BUY/SELL/HOLD) + confidence
- Gatekeeper статус (PASS или BLOCK)

## Обновление данных

Страница обновляется **автоматически каждые 2 секунды**.  
Никаких перезагрузок не нужно!

## Проверка работы

### 1. Проверь API
```bash
curl http://88.210.10.145:8585/api/brain_live | jq .
```

Должен вернуть JSON с данными.

### 2. Проверь логи
```bash
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50 | grep GlobalBrainState"
```

Должны быть строки типа:
```
✅ GlobalBrainState updated: BTCUSDT CHOP=45.2
```

### 3. Открой в браузере
http://88.210.10.145:8585/brain

Должна загрузиться тёмная страница с неоновыми эффектами.

## Troubleshooting

### Проблема: Страница не загружается
```bash
# Проверь что dashboard работает
ssh root@88.210.10.145 "docker ps | grep dashboard"

# Проверь логи
ssh root@88.210.10.145 "docker logs bybit_dashboard"
```

### Проблема: Данные не обновляются
```bash
# Проверь что бот работает
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50"

# Должны быть строки "Local Brain analyzing..."
```

### Проблема: Показывает "INITIALIZING..."
Это нормально! Бот ещё не начал сканирование.  
Подожди 1-5 минут, данные появятся.

## Что дальше?

- **Документация:** `NEURAL_HUD_DEPLOYMENT.md`
- **Для разработчиков:** `NEURAL_HUD_INTEGRATION_GUIDE.md`
- **Полный отчёт:** `NEURAL_HUD_COMPLETE.md`

## Контакты

Вопросы? Проверь логи или документацию выше.

---

**Enjoy your Neural HUD! 🧠✨**
