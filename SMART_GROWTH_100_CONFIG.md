# Smart Growth $100 - Финальная Конфигурация
## 4 декабря 2025, 23:00 UTC

---

## 🎯 СТРАТЕГИЯ: Smart Growth $100

**Цель:** Максимальная выживаемость депозита при умеренном разгоне

**Депозит:** $100  
**Плечо:** 5x (Buying Power $500)  
**Риск на сделку:** 12% ($12 маржи = $60 позиция)  
**Макс. позиций:** 5 (занято $60, буфер $40)

---

## 📊 КОНФИГУРАЦИЯ (config.py)

### 1. Мани-Менеджмент

```python
# FUTURES Settings - SMART GROWTH $100
futures_virtual_balance: float = 100.0  # $100 стартовый капитал
futures_leverage: int = 5  # Плечо 5x (Buying Power $500)
futures_risk_per_trade: float = 0.12  # 12% от баланса в маржу = $12
futures_margin_mode: 'ISOLATED'  # Изолированная маржа

# Position Limits
futures_max_open_positions: int = 5  # Макс. 5 позиций (5 × $12 = $60, буфер $40)
```

**Расчёт:**
- Маржа на сделку: $100 × 12% = $12
- Позиция с плечом 5x: $12 × 5 = $60
- Макс. занятая маржа: 5 × $12 = $60
- Drawdown Buffer: $100 - $60 = $40 (40%)

### 2. Trailing Stop (Быстрый Безубыток)

```python
# TRAILING STOP Settings - SMART GROWTH $100
trailing_stop_enabled: bool = True
trailing_activation_pct: float = 0.8  # Активация при +0.8% профита
trailing_callback_pct: float = 0.4  # Откат 0.4% → закрытие в плюс
```

**Логика:**
- Цена прошла +0.8% → активируем трейлинг
- Цена откатилась на 0.4% → закрываем в плюс
- Минимальный профит: +0.4% (после комиссий ~+0.28%)

### 3. Gatekeeper Фильтры (Строгие)

```python
# Gatekeeper - SMART GROWTH $100
chop_threshold: float = 60.0  # CHOP > 60 = флэт → SKIP
historical_wr_threshold: float = 25.0  # Historical WR < 25% → SKIP

# Минимальные confidence
futures_min_confidence: float = 0.60  # 60% для LONG
futures_min_confidence_short: float = 0.65  # 65% для SHORT (опаснее)
```

**Правила:**
- CHOP > 60 → SKIP (не торгуем шум)
- Historical WR < 25% → SKIP (плохие паттерны)
- LONG требует 60% confidence
- SHORT требует 65% confidence (шорты опаснее)

### 4. Fee Simulation (Реализм)

```python
# SIMULATED REALISM - SMART GROWTH $100
estimated_fee_rate: float = 0.0006  # 0.06% Taker fee
min_profit_threshold_multiplier: float = 2.0  # Профит >= 2× комиссия
min_profit_threshold_pct: float = 0.6  # Минимальный TP 0.6%
simulate_fees_in_demo: bool = True
```

**Проверки:**
1. TP < 0.6% → SKIP (не входим ради копеек)
2. Gross Profit < 2× Fees → SKIP (не окупает комиссию)

---

## 🛡️ ЛОГИКА AI BRAIN (ai_brain_local.py)

### Decision Tree (6 уровней)

```
1. Trading Hours Check (24/7 - отключен)
   ↓
2. Gatekeeper Level 1: CHOP Filter
   - CHOP > 60 → SKIP (флэт)
   ↓
3. Gatekeeper Level 2: Pattern Filter
   - Historical WR < 25% → SKIP (плохие паттерны)
   - ИСКЛЮЧЕНИЕ: ML confidence >= 60% → OVERRIDE
   ↓
4. ML Confidence Check
   - LONG: confidence < 60% → SKIP
   - SHORT: confidence < 65% → SKIP
   ↓
5. Fee Profitability Check (NEW!)
   - TP < 0.6% → SKIP (слишком мало)
   - Gross Profit < 2× Fees → SKIP (не окупает)
   ↓
6. Futures Brain Multi-Agent
   - Score < 2 → SKIP
   - Conservative (вес 3): conf > 60%
   - Balanced (вес 2): conf > 45%
   - Aggressive (вес 1): conf > 35%
```

### Ключевые Изменения

**1. Разные пороги для LONG/SHORT:**
```python
# LONG (покупка)
if ml_decision == 'BUY' and ml_confidence < 0.60:
    SKIP  # Требуем 60%

# SHORT (продажа)
if ml_decision == 'SELL' and ml_confidence < 0.65:
    SKIP  # Требуем 65% (шорты опаснее)
```

**2. Минимальный TP 0.6%:**
```python
# Проверка 1: TP слишком мал?
if tp_pct < 0.6:
    SKIP  # Не входим ради копеек
```

**3. Fee Profitability:**
```python
# Проверка 2: Окупает ли комиссию?
if gross_profit < 2 × total_fees:
    SKIP  # Не окупает
```

**4. TA Penalty смягчён:**
```python
# Было: -25% если TA не подтверждает
# Стало: -10%
if not ta_confirms:
    final_confidence = ml_confidence * 0.90  # -10%
```

---

## 📈 ОЖИДАЕМАЯ ПРОИЗВОДИТЕЛЬНОСТЬ

### Целевые Метрики

**Сделок в день:** 5-10  
**Win Rate:** 35-45%  
**Avg Trade:** +$0.50 - $1.20 net  
**Месячная цель:** +$15 - $30 (+15-30%)

### Защита Депозита

**Максимальная просадка:** 40% ($40 буфер)  
**Trailing Stop:** Активация +0.8%, откат 0.4%  
**Isolated Margin:** Ликвидация только одной позиции  
**Fee Simulation:** Реалистичная статистика

### Risk/Reward

**Типичная сделка:**
- Entry: $60 (с плечом 5x)
- Маржа: $12 (12% от депозита)
- SL: -1.5% = -$0.90 (7.5% от маржи)
- TP: +3.0% = +$1.80 (15% от маржи)
- R:R: 1:2

**После комиссий:**
- Fees: ~$0.14 (0.12% roundtrip)
- Net SL: -$1.04
- Net TP: +$1.66
- R:R: 1:1.6

---

## 🚀 ДЕПЛОЙ

### Файлы Обновлены

1. ✅ `config.py`:
   - futures_virtual_balance = 100.0
   - futures_risk_per_trade = 0.12
   - futures_max_open_positions = 5
   - trailing_activation_pct = 0.8
   - trailing_callback_pct = 0.4
   - min_profit_threshold_pct = 0.6
   - futures_min_confidence = 0.60
   - futures_min_confidence_short = 0.65

2. ✅ `ai_brain_local.py`:
   - CHOP threshold = 60.0 (строго)
   - Разные пороги для LONG (60%) / SHORT (65%)
   - Проверка минимального TP 0.6%
   - Fee profitability check
   - TA penalty смягчён: -25% → -10%

3. ✅ `futures_brain.py`:
   - Conservative: 60%
   - Balanced: 45% (без TA)
   - Aggressive: 35%
   - min_score_to_trade = 2

### Команды Деплоя

```bash
# 1. Копируем файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/futures_brain.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем контейнеры
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot && docker rm -f bybit_bot && docker-compose build bot && docker-compose up -d bot"
```

---

## ✅ ПРОВЕРКА ПОСЛЕ ДЕПЛОЯ

### 1. Проверить баланс

```bash
docker logs bybit_bot | grep "Virtual Balance"
# Ожидаем: Virtual Balance: $100.0
```

### 2. Проверить фильтры

```bash
docker logs bybit_bot | grep "Gatekeeper"
# Ожидаем: CHOP threshold: 60.0
# Ожидаем: Historical WR threshold: 25.0%
```

### 3. Проверить сделки через 2-4 часа

```bash
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "
SELECT COUNT(*) as total, 
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
       ROUND(SUM(pnl)::numeric, 2) as total_pnl
FROM trades WHERE status = 'CLOSED' AND entry_time > NOW() - INTERVAL '4 hours';
"
```

---

## 📝 ИТОГОВАЯ СТРАТЕГИЯ

**Smart Growth $100** - это баланс между:
- ✅ Безопасностью (40% буфер, Isolated Margin, строгие фильтры)
- ✅ Активностью (5-10 сделок/день, агрессивные пороги)
- ✅ Реализмом (учёт комиссий, минимальный TP 0.6%)
- ✅ Защитой прибыли (Trailing Stop +0.8%/0.4%)

**Цель:** Не потерять депозит, медленно расти, накопить опыт для перехода на Real Trading.

---

**Время:** 23:00 UTC, 4 декабря 2025  
**Статус:** ✅ Конфигурация готова к деплою  
**Следующий шаг:** Деплой на сервер и мониторинг 2-4 часа
