# 🎯 Aggressive Tuning - Исправление низкой активности торговли

**Дата:** 16 декабря 2025, 10:30 UTC  
**Проблема:** Бот почти не торгует, все сигналы SKIP, теряем деньги на комиссиях  
**Решение:** Снижение порогов фильтров для увеличения активности

---

## 🔍 Диагностика проблемы

### Симптомы
1. **Score 0/6** - никто из агентов не голосует
2. **Confidence 27-30%** - слишком низкий для входа
3. **Зомби-сделки** - 6 сделок с 0 PnL за 24 часа, потеряно $0.79 на комиссиях
4. **CHOP 58-65** - рынок во флэте, но Mean Reversion требует 65% confidence

### Статистика до исправления
- **Баланс:** $233.50 (было $100)
- **Profit:** +$133.50 (+133.5%)
- **Win Rate:** 68.3% (114 wins / 53 losses)
- **Последние 20 сделок:** много нулевых и мелких убытков
- **Futures Brain:** 2,904 решений, только 45 сделок (20 LONG + 25 SHORT)
- **Skip Rate:** 98.5% (2,859 SKIP из 2,904)

---

## ✅ Внесённые изменения

### 1. config.py - Снижение порогов confidence

**Было:**
```python
futures_min_confidence: float = 0.60  # 60%
futures_min_confidence_short: float = 0.60  # 60%
mean_reversion_min_confidence: float = 0.65  # 65%
```

**Стало:**
```python
futures_min_confidence: float = 0.50  # 50% (снижено с 60%)
futures_min_confidence_short: float = 0.50  # 50% (снижено с 60%)
mean_reversion_min_confidence: float = 0.50  # 50% (снижено с 65%)
```

**Эффект:** Больше сигналов проходят базовую проверку

---

### 2. config.py - Расширение зоны TREND

**Было:**
```python
chop_flat_threshold: float = 62.0  # CHOP >= 62 = FLAT
chop_trend_threshold: float = 58.0  # CHOP <= 58 = TREND
# Зона 58-62 = гистерезис
```

**Стало:**
```python
chop_flat_threshold: float = 65.0  # CHOP >= 65 = FLAT (повышено с 62)
chop_trend_threshold: float = 60.0  # CHOP <= 60 = TREND (повышено с 58)
# Зона 60-65 = гистерезис
```

**Эффект:** 
- CHOP 58-62 теперь считается TREND (было FLAT)
- TREND режим использует обычные пороги (50%), не Mean Reversion (65%)
- Больше сигналов в зоне 58-65

---

### 3. config.py - Снижение порога прибыльности

**Было:**
```python
min_profit_threshold_multiplier: float = 2.0  # 2x комиссия
min_profit_threshold_pct: float = 0.6  # 0.6% TP
```

**Стало:**
```python
min_profit_threshold_multiplier: float = 1.5  # 1.5x комиссия (снижено с 2.0)
min_profit_threshold_pct: float = 0.4  # 0.4% TP (снижено с 0.6%)
```

**Эффект:** Меньше сделок отклоняется из-за "слишком маленького профита"

---

### 4. futures_brain.py - Агрессивные пороги агентов

**Было:**
```python
'conservative': {
    'min_confidence': 60,  # 60%
},
'balanced': {
    'min_confidence': 45,  # 45%
},
'aggressive': {
    'min_confidence': 35,  # 35%
}
self.min_score_to_trade = 2  # нужно 2+ балла
```

**Стало:**
```python
'conservative': {
    'min_confidence': 55,  # 55% (снижено с 60%)
},
'balanced': {
    'min_confidence': 35,  # 35% (снижено с 45%)
},
'aggressive': {
    'min_confidence': 25,  # 25% (снижено с 35%)
}
self.min_score_to_trade = 1  # нужно 1+ балл (снижено с 2)
```

**Эффект:** 
- Aggressive agent голосует при confidence 25%+
- Достаточно 1 агента для входа (было 2)
- Raw Confidence 27% → Trading Confidence 30% → Aggressive голосует ✅

---

## 📊 Результаты после деплоя

### Первые 3 минуты работы

**До:**
- Total Decisions: 2,904
- LONGs: 20, SHORTs: 25, SKIPs: 2,859
- Skip Rate: 98.5%

**После:**
- Total Decisions: 12 (за 3 минуты!)
- LONGs: 0, SHORTs: 12, SKIPs: 0
- Skip Rate: 0% ✅
- Avg Confidence: 99.3%
- Aggressive agent: голосует на всех сигналах

### Открытые позиции
```
ETHUSDT SELL @ $2,924.97 (0.07 qty) - 07:55 UTC
SOLUSDT BUY  @ $125.97   (1.6 qty)  - 09:13 UTC
BNBUSDT SELL @ $859.90   (0.23 qty) - 10:17 UTC
```

### Попытки новых сделок
- ❌ BNBUSDT SHORT - position limit 1/1
- ❌ SOLUSDT SHORT - position limit 1/1
- ❌ ETHUSDT SHORT - position limit 1/1

**Вывод:** Бот активно ищет сигналы, но достигнут лимит 1 позиция на символ (правильное поведение!)

---

## ⚠️ Риски и мониторинг

### Потенциальные риски
1. **Overtrading** - слишком много сделок → больше комиссий
2. **Низкое качество сигналов** - confidence 25-35% может быть недостаточно
3. **Drawdown** - больше сделок = больше шанс на серию убытков

### Что мониторить
```sql
-- Win Rate (должен остаться > 60%)
SELECT 
    COUNT(*) FILTER (WHERE pnl > 0) as wins,
    COUNT(*) FILTER (WHERE pnl < 0) as losses,
    ROUND(COUNT(*) FILTER (WHERE pnl > 0)::numeric / COUNT(*) * 100, 1) as win_rate
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures' 
  AND entry_time > NOW() - INTERVAL '24 hours';

-- Средний PnL (должен быть > $0.50)
SELECT 
    ROUND(AVG(pnl - (fee_entry + fee_exit))::numeric, 2) as avg_net_pnl
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures' 
  AND entry_time > NOW() - INTERVAL '24 hours';

-- Количество сделок (ожидаем 10-20 в день)
SELECT COUNT(*) as trades_today
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures' 
  AND entry_time > NOW() - INTERVAL '24 hours';
```

---

## 🎯 Ожидаемые результаты

### Краткосрочные (24 часа)
- **Сделок в день:** 10-20 (было 5-10)
- **Win Rate:** 55-65% (было 68%, может снизиться)
- **Avg Trade:** +$0.30 - $0.80 net (было +$0.50 - $1.00)
- **Daily Profit:** +$3 - $12 (было +$2.50 - $10)

### Среднесрочные (7 дней)
- **Баланс:** $240 - $260 (сейчас $233.50)
- **Total Trades:** 70-140 (сейчас 440 за всё время)
- **Cumulative Profit:** +$6 - $26

### Критерии успеха
✅ Win Rate > 55%  
✅ Avg Net PnL > $0.30  
✅ Daily Profit > $2  
✅ Нет серий убытков > 5 подряд

### Критерии отката изменений
❌ Win Rate < 50% за 3 дня  
❌ Avg Net PnL < $0.10  
❌ Daily Loss > $5  
❌ Серия убытков > 8 подряд

---

## 📝 Следующие шаги

1. **Мониторинг 24 часа** - проверить Win Rate и Avg PnL
2. **Анализ качества сигналов** - какие confidence дают лучшие результаты
3. **Возможная тонкая настройка:**
   - Если Win Rate < 55% → поднять aggressive до 30%
   - Если слишком много сделок → поднять min_score_to_trade до 2
   - Если всё хорошо → оставить как есть

---

## 🔧 Откат изменений (если нужно)

```python
# config.py
futures_min_confidence: float = 0.60  # вернуть 60%
mean_reversion_min_confidence: float = 0.65  # вернуть 65%
chop_flat_threshold: float = 62.0  # вернуть 62
chop_trend_threshold: float = 58.0  # вернуть 58
min_profit_threshold_multiplier: float = 2.0  # вернуть 2.0

# futures_brain.py
'aggressive': {'min_confidence': 35}  # вернуть 35
self.min_score_to_trade = 2  # вернуть 2
```

---

**Статус:** ✅ Деплой успешен, бот активно торгует  
**Следующая проверка:** 17 декабря 2025, 10:30 UTC (через 24 часа)
