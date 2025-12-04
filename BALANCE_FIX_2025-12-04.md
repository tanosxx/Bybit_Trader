# Балансировка Торговой Системы - 4 декабря 2025

## ❌ ПРОБЛЕМА

**Симптомы:**
- За несколько часов работы: 0 сделок
- Все сигналы блокируются (100% SKIP)
- Gatekeeper пропускает, но Futures Brain блокирует
- Score: 0/6 (нужно 3+)

**Анализ логов:**
```
✅ Gatekeeper: PASSED (CHOP: 56.7, Historical WR: 40.0%)
✅ Fee check passed: Profitable: $3.47 net (after $1.09 fees)
✅ Final Decision: SELL (conf: 33%, risk: 8/10)
🧠 AI Decision: SELL
🎯 Confidence: 33%

🤖 MULTI-AGENT: SKIP (consensus: ❌)
   Score: 0/6 (need 3+)
```

**Причина:**
После исправления 0% Win Rate (FUTURES_BRAIN_FIX.md) система стала **СЛИШКОМ консервативной**:
- Conservative требует 75% confidence → ML даёт 33-56% → НЕТ
- Balanced требует 60% confidence → НЕТ
- Aggressive требует 55% confidence → иногда ДА (вес 1)
- Итого: Score 0-1, а нужно >= 3

**Дополнительная проблема:**
Gatekeeper блокирует паттерны с Historical WR < 40%, но Scenario Tester находит много паттернов с WR 10-30%.

---

## ✅ РЕШЕНИЕ

### 1. Балансировка Futures Brain

**Файл:** `Bybit_Trader/core/futures_brain.py`

**Изменения:**
```python
# БЫЛО (v2.0 - слишком строго):
'conservative': {'min_confidence': 75}  # Почти никогда не срабатывает
'balanced': {'min_confidence': 60}      # Редко срабатывает
'aggressive': {'min_confidence': 55}    # Иногда срабатывает (вес 1)

# СТАЛО (v3.0 - сбалансировано):
'conservative': {'min_confidence': 70}  # Снижено на 5%
'balanced': {'min_confidence': 55}      # Снижено на 5% - основной фильтр
'aggressive': {'min_confidence': 45}    # Снижено на 10% - даём шанс слабым сигналам
```

**Логика:**
- Conservative (вес 3): Очень сильные сигналы (70%+)
- Balanced (вес 2): Средние сигналы (55%+) + TA подтверждение
- Aggressive (вес 1): Слабые сигналы (45%+) без TA

**Возможные комбинации для Score >= 3:**
1. Conservative (3) = 3 ✅
2. Balanced (2) + Aggressive (1) = 3 ✅
3. Conservative (3) + Balanced (2) = 5 ✅
4. Conservative (3) + Aggressive (1) = 4 ✅

### 2. Смягчение Gatekeeper

**Файл:** `Bybit_Trader/core/ai_brain_local.py`

**Изменения:**
```python
# БЫЛО:
self.historical_wr_threshold = 40.0  # Блокирует WR < 40%

# СТАЛО:
self.historical_wr_threshold = 30.0  # Блокирует только WR < 30%
```

**Логика:**
- WR < 30% = очень плохой паттерн → SKIP
- WR 30-40% = средний паттерн → ПРОПУСТИТЬ (дать шанс)
- WR > 40% = хороший паттерн → ПРОПУСТИТЬ

---

## 🎯 Ожидаемый Результат

**До изменений:**
- 100% SKIP
- 0 сделок за несколько часов
- Score: 0/6

**После изменений:**
- Balanced + Aggressive = Score 3 (при conf 55%+)
- Conservative = Score 3 (при conf 70%+)
- Gatekeeper пропускает паттерны с WR 30-40%
- Ожидаемая частота сделок: 3-8 в день

**Защита от 0% Win Rate сохранена:**
- ✅ Минимум Score 3 (нужно 2 агента)
- ✅ TA подтверждение для Balanced и Conservative
- ✅ CHOP фильтр (> 60 = флэт)
- ✅ Fee check (профит > 2× комиссия)
- ✅ Gatekeeper блокирует WR < 30%

---

## 📊 Мониторинг

**Проверка через 2-4 часа:**
```bash
# Количество сделок
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT COUNT(*) as total, 
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
FROM trades WHERE status = 'CLOSED';
"

# Логи Futures Brain
docker logs bybit_bot | grep "Score:"

# Gatekeeper статистика
docker logs bybit_bot | grep "Gatekeeper:"
```

**Целевые метрики:**
- Сделок: 3-8 в день
- Win Rate: 35-50%
- Avg PnL: +$0.50 - $1.50 net
- Score: 3-6 (не 0!)

---

## 🚀 Деплой

**Выполнено:**
1. ✅ Обновлён `futures_brain.py` (пороги агентов)
2. ✅ Обновлён `ai_brain_local.py` (Gatekeeper порог)
3. ✅ Файлы скопированы на сервер
4. ✅ Контейнер удалён и пересобран
5. ✅ Бот перезапущен

**Команды:**
```bash
scp Bybit_Trader/core/futures_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot && docker rm -f bybit_bot && docker-compose build bot && docker-compose up -d bot"
```

---

## 📝 История Изменений

**v1.0 (до 4 декабря):**
- Conservative: 60%, Balanced: 55%, Aggressive: 40%
- Результат: 0% Win Rate (20 сделок, все в минус)

**v2.0 (4 декабря, утро):**
- Conservative: 75%, Balanced: 60%, Aggressive: 55%
- Gatekeeper: WR < 40%
- Результат: 100% SKIP, 0 сделок

**v3.0 (4 декабря, вечер) - ТЕКУЩАЯ:**
- Conservative: 70%, Balanced: 55%, Aggressive: 45%
- Gatekeeper: WR < 30%
- Ожидаемый результат: 3-8 сделок/день, WR 35-50%

---

## ✅ СТАТУС

**ЗАВЕРШЕНО** - Система сбалансирована, бот перезапущен.

Мониторинг через 2-4 часа для оценки эффективности.
