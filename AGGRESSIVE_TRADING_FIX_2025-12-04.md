# Агрессивная Настройка Торговли - 4 декабря 2025, 22:00 UTC

## ❌ ПРОБЛЕМА

**Второй день без сделок - система СЛИШКОМ консервативная!**

- Последняя сделка: 18:10 UTC (4 декабря)
- Прошло: ~4 часа без сделок
- ML даёт BUY сигналы (60-75% conf)
- Но Gatekeeper блокирует: Historical WR 0%

---

## ✅ РЕШЕНИЕ: Агрессивная Настройка v5.0

### 1. Futures Brain - Радикальное Снижение Порогов

**Файл:** `core/futures_brain.py`

**Изменения:**
```python
# БЫЛО (v4.0):
'conservative': {'min_confidence': 65, 'require_ta': True}
'balanced': {'min_confidence': 50, 'require_ta': True}
'aggressive': {'min_confidence': 40, 'require_ta': False}
min_score_to_trade = 3

# СТАЛО (v5.0):
'conservative': {'min_confidence': 60, 'require_ta': True}   # -5%
'balanced': {'min_confidence': 45, 'require_ta': False}      # -5% + убрано TA
'aggressive': {'min_confidence': 35, 'require_ta': False}    # -5%
min_score_to_trade = 2  # Снижено с 3!
```

**Эффект:**
- Balanced теперь НЕ требует TA подтверждения
- Aggressive пропускает сигналы от 35%
- Достаточно Score 2 (один Balanced агент)

### 2. TA Penalty - Смягчение

**Файл:** `core/ai_brain_local.py`

**Изменения:**
```python
# БЫЛО:
if not ta_confirms:
    final_confidence = ml_confidence * 0.75  # -25%

# СТАЛО:
if not ta_confirms:
    final_confidence = ml_confidence * 0.90  # -10%
```

**Эффект:**
- ML 60% → TA не подтверждает → было 45%, стало 54%
- ML 75% → TA не подтверждает → было 56%, стало 67%

### 3. CHOP Threshold - Повышение

**Файл:** `core/ai_brain_local.py`

**Изменения:**
```python
# БЫЛО:
self.chop_threshold = 60.0  # CHOP > 60 = флэт

# СТАЛО:
self.chop_threshold = 65.0  # CHOP > 65 = флэт
```

**Эффект:**
- CHOP 60-65 теперь пропускается (раньше блокировалось)

### 4. Historical WR - Исключение для Сильных Сигналов

**Файл:** `core/ai_brain_local.py`

**Изменения:**
```python
# БЫЛО:
if historical_wr < 25%:
    SKIP

# СТАЛО:
if historical_wr < 25% AND ml_confidence < 70%:
    SKIP
elif historical_wr < 25% AND ml_confidence >= 70%:
    OVERRIDE - пропускаем!
```

**Эффект:**
- ML 75% conf → даже с WR 0% → ПРОПУСКАЕТСЯ
- ML 60% conf → WR 0% → блокируется

---

## 📊 Ожидаемый Результат

### До изменений (v4.0):
- ML: BUY 60% → TA penalty → 45% → Self-Learning → 43%
- Aggressive требует 40% → НЕТ
- Balanced требует 50% + TA → НЕТ
- Score: 0/6 → SKIP

### После изменений (v5.0):
- ML: BUY 60% → TA penalty → 54% → Self-Learning → 51%
- Aggressive требует 35% → ДА (вес 1)
- Balanced требует 45% без TA → ДА (вес 2)
- Score: 3/6 → **TRADE!**

### Для сильных сигналов:
- ML: BUY 75% → TA penalty → 67% → Self-Learning → 64%
- Aggressive: ДА (вес 1)
- Balanced: ДА (вес 2)
- Conservative: ДА (вес 3)
- Score: 6/6 → **STRONG TRADE!**
- Historical WR 0% → OVERRIDE (ML очень уверен)

---

## ⚠️ Риски

**Агрессивная настройка увеличивает риски:**

1. **Больше ложных входов:**
   - Пропускаем сигналы с conf 35-45%
   - Не требуем TA подтверждения для Balanced
   - Ожидаемый Win Rate: 30-40% (было 40-50%)

2. **Игнорируем плохие паттерны:**
   - Historical WR 0% пропускается если ML > 70%
   - Риск повторить прошлые ошибки

3. **Больше сделок в флэте:**
   - CHOP 60-65 теперь пропускается
   - Риск входов в боковике

**Защита сохранена:**
- ✅ Fee check (профит > 2× комиссия)
- ✅ CHOP > 65 блокируется
- ✅ Score >= 2 (минимум 1 агент)
- ✅ Self-Learning влияние снижено до 5%

---

## 🎯 Целевые Метрики

**Ожидаемая производительность:**
- Сделок в день: 8-15 (было 0-2)
- Win Rate: 30-40% (было 40-50%)
- Avg PnL: +$0.30 - $0.80 net (было +$0.80 - $1.50)
- Цель: активная торговля, накопление опыта

**Мониторинг через 4-6 часов:**
```bash
# Количество сделок
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT COUNT(*) as total, 
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
       ROUND(SUM(pnl)::numeric, 2) as total_pnl
FROM trades WHERE status = 'CLOSED' AND entry_time > NOW() - INTERVAL '6 hours';
"
```

---

## 🚀 Деплой

**Выполнено:**
1. ✅ Futures Brain: пороги снижены на 5%, min_score = 2
2. ✅ TA penalty: 25% → 10%
3. ✅ CHOP threshold: 60 → 65
4. ✅ Historical WR: исключение для ML > 70%
5. ✅ Файлы скопированы на сервер
6. ✅ Контейнер пересобран
7. ✅ Бот перезапущен

**Время деплоя:** 22:00 UTC, 4 декабря 2025

---

## 📝 История Версий

**v1.0:** Conservative 60%, Balanced 55%, Aggressive 40% → 0% WR  
**v2.0:** Conservative 75%, Balanced 60%, Aggressive 55% → 100% SKIP  
**v3.0:** Conservative 70%, Balanced 55%, Aggressive 45% → 100% SKIP  
**v4.0:** Conservative 65%, Balanced 50%, Aggressive 40% → 100% SKIP  
**v5.0 (ТЕКУЩАЯ):** Conservative 60%, Balanced 45%, Aggressive 35%, Score >= 2 → **АКТИВНАЯ ТОРГОВЛЯ**

---

## ✅ СТАТУС

**ЗАВЕРШЕНО** - Агрессивная настройка применена, бот перезапущен.

Ожидаем первые сделки в течение 30-60 минут.

**Если через 2 часа всё равно нет сделок:**
- Проверить логи: что блокирует?
- Возможно нужно отключить Gatekeeper полностью
- Или снизить пороги ещё больше (но это очень рискованно)
