# Bybit Trading Bot - Trend Filter v3 (EMA 200)

**Дата:** 15 января 2026  
**Версия:** v3.0 - EMA 200 Trend Filter Edition  
**Статус:** 🚨 EMERGENCY UPDATE

---

## 🚨 Проблема

**Текущая ситуация:**
- Баланс: $80.57 (было $100 → **-19.43% убыток**)
- Win Rate: **39.4%** (56 wins / 85 losses из 142 сделок) ❌
- Проблема: Бот открывает только LONG на падающем рынке (RSI < 40)
- Результат: "Ловля падающих ножей" → гарантированный слив депозита

**Почему стратегия v2 не работает:**
1. Нет фильтра глобального тренда
2. Открывает LONG при RSI < 40, даже если рынок в сильном downtrend
3. Цена продолжает падать после входа → Stop Loss → убыток
4. SHORT сигналы слишком редкие (RSI > 60 в downtrend почти не бывает)

---

## ✅ Решение: EMA 200 Trend Filter

### Концепция

**EMA 200 = ГЛАВНЫЙ фильтр глобального тренда**

- **Цена > EMA 200** = UPTREND → Разрешены ТОЛЬКО LONG
- **Цена < EMA 200** = DOWNTREND → Разрешены ТОЛЬКО SHORT

**Правило:** НЕ торгуй против глобального тренда!

### Изменения в стратегии

**1. Добавлен EMA 200 фильтр**
```python
# Определяем глобальный тренд
global_trend = "UP" if current_price > ema_trend else "DOWN"

# LONG сигнал (ТОЛЬКО в UPTREND)
if global_trend == "UP":
    if current_rsi < 40 and current_price < ema_slow:
        # ... открываем LONG

# SHORT сигнал (ТОЛЬКО в DOWNTREND)
elif global_trend == "DOWN":
    if current_rsi > 55 and current_price > ema_slow:
        # ... открываем SHORT
```

**2. Смягчен порог RSI для SHORT в downtrend**
- Было: RSI > 60 (слишком редко в downtrend)
- Стало: RSI > 55 (легче поймать отскоки)

**Логика:** В downtrend цена редко доходит до RSI 60-70. RSI 55 позволяет шортить на небольших отскоках.

**3. Удален MATICUSDT из списка пар**
- Причина: Ошибка парсинга `'timestamp'` в каждом цикле
- Было: 14 пар
- Стало: 13 пар

**4. Снижен лимит открытых позиций**
- Было: 5 позиций
- Стало: 3 позиции
- Причина: Меньше застрявших позиций, меньше риск

**5. Увеличен лимит свечей для анализа**
- Было: 100 свечей
- Стало: 250 свечей
- Причина: Нужно минимум 210 свечей для расчета EMA 200

---

## 📊 Ожидаемые результаты

### До (v2 - без фильтра)
- Сигналы: 8-9 LONG на падающем рынке
- Результат: Все блокируются (max 5 positions reached)
- Win Rate: 39.4% ❌
- Баланс: -19.43% за период

### После (v3 - с EMA 200 фильтром)
- Сигналы: 0 LONG (рынок в downtrend), 3-5 SHORT
- Результат: Торгуем ПО тренду (SHORT на отскоках)
- Win Rate: 50-60% (цель)
- Баланс: Остановить слив, начать восстановление

### Примеры сигналов (текущий рынок)

**BTC: $94,000 (EMA 200: $96,500)**
- Trend: DOWN (цена < EMA 200)
- Разрешены: ТОЛЬКО SHORT
- Блокируются: Все LONG сигналы

**ETH: $3,330 (EMA 200: $3,450)**
- Trend: DOWN (цена < EMA 200)
- Разрешены: ТОЛЬКО SHORT
- Блокируются: Все LONG сигналы

**Сигнал SHORT:**
- RSI поднимается до 55-60 (небольшой отскок)
- Цена выше EMA 21 (локальная коррекция)
- ADX > 25 (сильный downtrend)
- EMA 9 разворачивается вниз
- → Открываем SHORT, цена продолжает падать → TP ✅

---

## 🔧 Технические детали

### Файлы изменены

**1. `core/strategies/simple_scalper.py`**
- Добавлен `self.ema_trend_period = 200`
- Добавлен `self.rsi_overbought_downtrend = 55`
- Обновлен `analyze_symbol()` с EMA 200 фильтром
- Увеличен лимит свечей: 100 → 250

**2. `config_v2.py`**
- Удален `MATICUSDT` из `futures_pairs`
- Снижен `futures_max_open_positions`: 5 → 3
- Добавлен комментарий про жёсткий Stop Loss

### Новые параметры

```python
# EMA 200 Trend Filter
self.ema_trend_period = 200  # Главный трендовый фильтр

# RSI пороги
self.rsi_oversold = 40  # Для LONG в uptrend
self.rsi_overbought_downtrend = 55  # Для SHORT в downtrend (СМЯГЧЕНО!)
```

### Логика фильтрации

```
Новый сигнал
    ↓
Расчет EMA 200
    ↓
Определение глобального тренда
    ├─ Price > EMA 200 → UPTREND
    └─ Price < EMA 200 → DOWNTREND
    ↓
Фильтрация сигналов
    ├─ UPTREND → Разрешены ТОЛЬКО LONG (блокировать SHORT)
    └─ DOWNTREND → Разрешены ТОЛЬКО SHORT (блокировать LONG)
    ↓
Проверка локальных условий (RSI, EMA 9/21, ADX)
    ↓
Генерация сигнала
```

---

## 🚀 Deployment

### Команды деплоя

```bash
# 1. Копируем обновленные файлы
scp Bybit_Trader/core/strategies/simple_scalper.py root@88.210.10.145:/root/Bybit_Trader/core/strategies/
scp Bybit_Trader/config_v2.py root@88.210.10.145:/root/Bybit_Trader/

# 2. Пересобираем контейнер (config.py в раннем слое)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"

# 3. Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"

# 4. Проверяем логи
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50"
```

### Ожидаемые логи

```
✅ SimpleScalper v3 initialized (EMA 200 Trend Filter)
   Timeframe: 15m
   EMA 200: TREND FILTER (Price > EMA200 = UPTREND, Price < EMA200 = DOWNTREND)
   RSI: 14 (LONG: <40, SHORT: >55 in downtrend)
   EMA: 9/21 (local trend detection)
   ADX: 14 (min 25 for trading)
   TP: +1.5%, SL: -2.0%
   Symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, ATOMUSDT, LTCUSDT, UNIUSDT

🔍 Scanning markets...
🎯 SIGNAL: SHORT ETHUSDT @ 3328.29
   DOWNTREND (Price 3328.29 < EMA200 3450.00), RSI 56.3 > 55, Price > EMA21 3335.53, ADX 51.6 > 25, EMA9 turning down
```

---

## 📈 Мониторинг

### Проверка что фильтр работает

```bash
# 1. Проверить что бот инициализирован с v3
docker logs bybit_bot | grep "SimpleScalper v3"

# 2. Проверить сигналы (должны быть SHORT в downtrend)
docker logs bybit_bot | grep "SIGNAL: SHORT"

# 3. Проверить что LONG блокируются
docker logs bybit_bot | grep "DOWNTREND"

# 4. Проверить открытые позиции (должны быть SHORT)
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT symbol, side, entry_price FROM trades WHERE status = 'OPEN';"
```

### Метрики успеха (через 24 часа)

**Цели:**
- ✅ Нет новых LONG позиций (рынок в downtrend)
- ✅ Открыты 1-3 SHORT позиции
- ✅ Win Rate > 50% (новые сделки)
- ✅ Баланс стабилизировался (нет дальнейшего слива)

**Если через 24 часа:**
- Баланс продолжает падать → Остановить бота, пересмотреть стратегию
- Баланс стабилизировался → Продолжить мониторинг
- Баланс растет → Стратегия работает ✅

---

## 🎯 Следующие шаги

**Немедленно (после деплоя):**
1. ✅ Закрыть все текущие LONG позиции вручную (сохранить $80)
2. ✅ Задеплоить v3 с EMA 200 фильтром
3. ✅ Мониторить первые 10 сделок

**Через 24 часа:**
1. Проверить Win Rate новых сделок
2. Проверить что SHORT сигналы генерируются
3. Оценить изменение баланса

**Через 7 дней:**
1. Если Win Rate > 50% → Продолжить
2. Если Win Rate < 50% → Ужесточить фильтры (ADX > 30, RSI > 60)
3. Рассмотреть добавление дополнительных фильтров (Volume, Volatility)

---

## 📚 Документация

**Обновленные файлы:**
- `core/strategies/simple_scalper.py` - Стратегия v3 с EMA 200
- `config_v2.py` - Обновленная конфигурация
- `TREND_FILTER_V3_2026-01-15.md` - Этот документ

**Связанные документы:**
- `SMART_GROWTH_100_CONFIG.md` - Конфигурация $100 (4 дек 2025)
- `SYSTEM_CHECK_FINAL.md` - Полная проверка систем
- `SIMULATED_REALISM.md` - Учёт комиссий

---

**Дата создания:** 15 января 2026, 18:00 UTC  
**Автор:** AI Assistant (Kiro)  
**Версия:** v3.0 - EMA 200 Trend Filter Edition
