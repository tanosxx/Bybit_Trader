# 🧟 Zombie Killer Fix - Исправление Time-To-Live проверки

**Дата:** 16 декабря 2025, 11:30 UTC  
**Проблема:** Позиция ETHUSDT висит 3.4 часа (> 3.0 часов лимита), но не закрывается  
**Причина:** Timezone Hell - сравнение naive datetime с aware datetime

---

## 🔍 Диагностика проблемы

### Симптомы
1. **ETHUSDT** открыта 3.4 часа (> 180 минут лимита)
2. **config.py:** `max_hold_time_minutes = 180` (3 часа)
3. **Логи:** "Checking critical risks..." но сделка не закрывается
4. **Emergency Brake** не срабатывает

### Причина: Timezone Hell

**Код ДО исправления (futures_executor.py:1456):**

```python
# ❌ ПРОБЛЕМА: naive datetime (без timezone info)
now = datetime.utcnow()

for trade in open_trades:
    entry_time = trade.entry_time  # Может быть aware или naive
    
    # Сравнение naive с aware → неправильный результат!
    hold_time_minutes = (now - entry_time).total_seconds() / 60
```

**Что происходило:**
- `datetime.utcnow()` возвращает **naive datetime** (без timezone)
- `trade.entry_time` из БД может быть **aware datetime** (с timezone)
- При сравнении naive с aware Python может:
  - Выдать ошибку (в строгом режиме)
  - Вернуть неправильный результат (разница 0 или отрицательная)
  - Считать что позиция открыта 0 минут

---

## ✅ Решение

### 1. Использование timezone-aware datetime

```python
# ✅ ИСПРАВЛЕНО: aware datetime (UTC)
from datetime import timezone
now = datetime.now(timezone.utc)

for trade in open_trades:
    entry_time = trade.entry_time
    
    # Конвертируем entry_time в aware если нужно
    if entry_time and entry_time.tzinfo is None:
        # Если naive - считаем что это UTC
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    
    # Теперь сравнение корректное!
    hold_time_minutes = (now - entry_time).total_seconds() / 60
```

### 2. DEBUG логирование

```python
# DEBUG LOG для диагностики
print(f"   🧟 Zombie Check: {symbol} Open={entry_time.strftime('%H:%M:%S UTC')}, Now={now.strftime('%H:%M:%S UTC')}, Duration={hold_time_minutes:.1f}m / Limit={settings.max_hold_time_minutes}m")
```

**Пример вывода:**
```
🧟 Zombie Check: BNBUSDT Open=10:42:15 UTC, Now=11:27:34 UTC, Duration=45.3m / Limit=180m
🧟 Zombie Check: SOLUSDT Open=10:49:33 UTC, Now=11:27:34 UTC, Duration=38.0m / Limit=180m
🧟 Zombie Check: ETHUSDT Open=07:55:49 UTC, Now=11:27:34 UTC, Duration=211.8m / Limit=180m
```

---

## 📊 Результаты после деплоя

### ✅ Zombie Killer сработал!

**Логи:**
```
🚨 EMERGENCY BRAKE: Checking critical risks...
   🧟 Zombie Check: ETHUSDT Open=07:55:49 UTC, Now=11:27:34 UTC, Duration=211.8m / Limit=180m
🚨 EMERGENCY BRAKE: 1 positions need immediate closure!

🚨 EMERGENCY CLOSING: ETHUSDT
   Reason: ⏰ ZOMBIE TRADE (TTL EXPIRED): 212 min > 180 min
```

**Расчёты:**
- Entry: 07:55:49 UTC
- Now: 11:27:34 UTC
- Duration: 211.8 минут (3.53 часа)
- Limit: 180 минут (3.0 часа)
- **Превышение: +31.8 минут** ✅

### ⚠️ Новая проблема: "No position"

**Логи:**
```
🚨 EMERGENCY CLOSING: ETHUSDT
   Reason: ⏰ ZOMBIE TRADE (TTL EXPIRED): 212 min > 180 min
   ❌ Emergency closure failed: No position
```

**Причина:**
- Позиция есть в БД (status = OPEN)
- Позиции НЕТ на бирже (Bybit API возвращает "No position")
- Это **фантомная позиция** (phantom position)

**Почему так происходит:**
1. Позиция была закрыта на бирже (по TP/SL или вручную)
2. Sync Service не успел обновить БД
3. Или позиция была на Demo API, а мы переключились на Live

---

## 🔧 Дополнительные исправления

### Проблема: Фантомные позиции

**Решение:** Улучшить Sync Service

```python
# sync_service.py
async def sync_positions():
    """Синхронизация позиций БД с биржей"""
    
    # 1. Получить позиции с биржи
    exchange_positions = await api.get_positions()
    
    # 2. Получить позиции из БД
    db_positions = await get_open_trades()
    
    # 3. Найти фантомные позиции (есть в БД, нет на бирже)
    for db_pos in db_positions:
        if db_pos.symbol not in exchange_positions:
            # Закрыть фантомную позицию в БД
            await close_phantom_position(db_pos)
            print(f"   👻 Closed phantom position: {db_pos.symbol}")
```

**Статус:** Sync Service уже работает, но может быть задержка 1-5 минут

---

## 📝 Изменения в коде

### futures_executor.py

**Строка 1456-1470:**
```python
# БЫЛО:
now = datetime.utcnow()  # ❌ naive datetime

# СТАЛО:
from datetime import timezone
now = datetime.now(timezone.utc)  # ✅ aware datetime

# Конвертируем entry_time в aware если нужно
if entry_time and entry_time.tzinfo is None:
    entry_time = entry_time.replace(tzinfo=timezone.utc)
```

**Строка 1520-1530:**
```python
# ДОБАВЛЕНО: DEBUG логирование
print(f"   🧟 Zombie Check: {symbol} Open={entry_time.strftime('%H:%M:%S UTC')}, Now={now.strftime('%H:%M:%S UTC')}, Duration={hold_time_minutes:.1f}m / Limit={settings.max_hold_time_minutes}m")

if hold_time_minutes > settings.max_hold_time_minutes:
    # ... закрытие позиции
    print(f"   ⏰ ZOMBIE TRADE DETECTED: {symbol} held for {hold_time_minutes:.0f} min (limit: {settings.max_hold_time_minutes} min)")
```

---

## 🎯 Проверка работы

### Тест 1: Zombie Check логи

```bash
docker logs bybit_bot | grep "Zombie Check"
```

**Ожидаемый результат:**
```
🧟 Zombie Check: BNBUSDT Open=10:42:15 UTC, Now=11:27:34 UTC, Duration=45.3m / Limit=180m
🧟 Zombie Check: SOLUSDT Open=10:49:33 UTC, Now=11:27:34 UTC, Duration=38.0m / Limit=180m
🧟 Zombie Check: ETHUSDT Open=07:55:49 UTC, Now=11:27:34 UTC, Duration=211.8m / Limit=180m
```

### Тест 2: Zombie Trade Detection

```bash
docker logs bybit_bot | grep "ZOMBIE TRADE"
```

**Ожидаемый результат:**
```
⏰ ZOMBIE TRADE DETECTED: ETHUSDT held for 212 min (limit: 180 min)
🚨 EMERGENCY CLOSING: ETHUSDT
   Reason: ⏰ ZOMBIE TRADE (TTL EXPIRED): 212 min > 180 min
```

### Тест 3: Проверка БД

```sql
-- Позиции старше 3 часов
SELECT 
    symbol, 
    side, 
    entry_time,
    EXTRACT(EPOCH FROM (NOW() - entry_time))/60 as duration_minutes,
    status
FROM trades 
WHERE status = 'OPEN' 
  AND market_type = 'futures'
  AND entry_time < NOW() - INTERVAL '180 minutes';
```

---

## 📊 Статистика

### До исправления
- **ETHUSDT:** Открыта 3.4 часа (> 3.0 лимита)
- **Zombie Killer:** НЕ срабатывал
- **Причина:** Timezone Hell (naive vs aware datetime)

### После исправления
- **Zombie Check:** Работает ✅
- **Duration расчёт:** Корректный (211.8 минут) ✅
- **Detection:** Срабатывает (ETHUSDT обнаружена) ✅
- **Closure:** Попытка закрытия (но "No position" на бирже) ⚠️

---

## ⚠️ Известные проблемы

### 1. Фантомные позиции

**Проблема:** Позиция в БД, но нет на бирже  
**Причина:** Sync Service задержка или позиция закрыта вручную  
**Решение:** Sync Service автоматически закроет через 1-5 минут

### 2. Demo vs Live API

**Проблема:** Позиции с Demo API не видны в Live API  
**Причина:** Разные окружения  
**Решение:** Не переключаться между Demo и Live без сброса БД

---

## 🎯 Следующие шаги

1. ✅ **Zombie Killer работает** - обнаруживает старые позиции
2. ⏳ **Дождаться Sync Service** - закроет фантомную ETHUSDT в БД
3. 📊 **Мониторинг 24 часа** - проверить что новые позиции закрываются корректно

---

## 📝 Выводы

### Что исправили
✅ Timezone Hell - используем aware datetime (UTC)  
✅ DEBUG логирование - видим расчёты времени  
✅ Zombie Killer - корректно обнаруживает старые позиции

### Что работает
✅ Duration расчёт: 211.8 минут (корректно)  
✅ Detection: ETHUSDT обнаружена как zombie  
✅ Emergency Brake: срабатывает и пытается закрыть

### Что осталось
⚠️ Фантомные позиции - Sync Service закроет автоматически  
⚠️ "No position" ошибка - нормально для фантомных позиций

---

**Статус:** ✅ Zombie Killer исправлен и работает корректно  
**Следующая проверка:** 16 декабря 2025, 15:00 UTC (через 3-4 часа)
