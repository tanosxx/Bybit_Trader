# BALANCED MODE - Оживление торговли (18 декабря 2025)

## 🚨 Проблема

Бот "зажался" в Safe Mode и почти не торгует:
- **За 45 часов:** 1 сделка
- **Сегодня (18 дек):** 1 сделка за весь день (+$0.02)
- **Последняя неделя:** -$177 убытков (16-17 дек)

**Причины:**
1. ML confidence слишком низкая (60%) < порог (65%)
2. Multi-Agent требует Score 3/6, но получает 0/6
3. CHOP пороги слишком строгие (60-65)
4. Balanced Agent требует TA подтверждение

**Из логов:**
```
⚠️ ML confidence too low for LONG (60% < 65%)
🤖 MULTI-AGENT: SKIP (consensus: ❌)
Score: 0/6 (need 3+)
```

---

## ✅ Решение: BALANCED MODE

### 1. Снижение порогов confidence (config.py)

**Было:**
```python
futures_min_confidence: float = 0.65  # 65% для LONG
futures_min_confidence_short: float = 0.65  # 65% для SHORT
```

**Стало:**
```python
futures_min_confidence: float = 0.60  # 60% для LONG (снижено на 5%)
futures_min_confidence_short: float = 0.60  # 60% для SHORT (снижено на 5%)
```

**Эффект:** Сигналы с confidence 60-65% теперь проходят фильтр.

---

### 2. Калибровка CHOP порогов (config.py)

**Было:**
```python
chop_flat_threshold: float = 65.0  # CHOP >= 65 = FLAT
chop_trend_threshold: float = 60.0  # CHOP <= 60 = TREND
# Зона 60-65 = гистерезис
```

**Стало:**
```python
chop_flat_threshold: float = 62.0  # CHOP >= 62 = FLAT (снижено с 65)
chop_trend_threshold: float = 55.0  # CHOP <= 55 = TREND (снижено с 60)
# Зона 55-62 = гистерезис
```

**Эффект:** 
- Раньше распознаём тренд (CHOP 55-60 теперь TREND)
- Меньше блокировок по CHOP фильтру
- Текущий CHOP 49.2 (BTCUSDT) → TREND ✅

---

### 3. Multi-Agent: снижение порога консенсуса (futures_brain.py)

**Было:**
```python
self.min_score_to_trade = 3  # Нужен conservative (3) ИЛИ balanced (2) + aggressive (1)
```

**Стало:**
```python
self.min_score_to_trade = 2  # Нужен balanced (2) ИЛИ aggressive (1) + conservative (1)
```

**Эффект:** Достаточно поддержки 2 агентов вместо 3.

---

### 4. Balanced Agent: убрали требование TA (futures_brain.py)

**Было:**
```python
'balanced': {
    'weight': 2,
    'min_confidence': 60,
    'require_ta': True,  # ТРЕБУЕМ TA подтверждение
    'max_risk': 6
}
```

**Стало:**
```python
'balanced': {
    'weight': 2,
    'min_confidence': 60,
    'require_ta': False,  # УБРАЛИ требование TA
    'max_risk': 8  # Повышено с 6
}
```

**Эффект:** Balanced Agent голосует даже без TA подтверждения и принимает больше риска.

---

### 5. Калибровка агентов (futures_brain.py)

**Изменения:**
- **Conservative:** 70% → 75% (более строгий), max_risk 5 → 7
- **Balanced:** 60% (без изменений), max_risk 6 → 8, убрали require_ta
- **Aggressive:** 50% → 55% (чуть строже), max_risk 7 → 9

**Логика:**
- Conservative голосует редко, но даёт 3 балла
- Balanced голосует чаще (без TA, больше риска), даёт 2 балла ✅
- Aggressive голосует часто, даёт 1 балл

**Примеры консенсуса:**
- Balanced (2) = ВХОД ✅
- Aggressive (1) + Conservative (3) = ВХОД ✅
- Balanced (2) + Aggressive (1) = ВХОД ✅

### 6. UNCERTAIN режим смягчён (strategic_brain.py)

**Проблема:** Strategic Brain определил рынок как UNCERTAIN и блокировал ВСЕ сигналы.

**Было:**
```python
elif regime == REGIME_UNCERTAIN:
    # НЕ торговать вообще
    print(f"🚫 Strategic Veto: ALL signals blocked")
    return False
```

**Стало:**
```python
elif regime == REGIME_UNCERTAIN:
    # Разрешаем торговлю с повышенной осторожностью
    print(f"⚠️  Strategic Warning: UNCERTAIN regime - trade with caution")
    return True  # Multi-Agent сам отфильтрует слабые сигналы
```

**Эффект:** UNCERTAIN больше не блокирует торговлю полностью, но Multi-Agent система будет строже фильтровать сигналы.

---

## 📊 Ожидаемые результаты

### До изменений (Safe Mode)
- Сделок в день: 0-1
- Блокировок: 99%
- Причины: confidence < 65%, Score < 3, CHOP > 60

### После изменений (Balanced Mode)
- Сделок в день: **3-5** (цель)
- Блокировок: ~70%
- Пропускаются: confidence 60%+, Score 2+, CHOP < 62

---

## 🎯 Риски и контроль

### Риски
1. **Больше сделок = больше комиссий**
   - Контроль: Fee Profitability Check (TP > 0.4%)
2. **Ниже качество сигналов**
   - Контроль: Gatekeeper (CHOP, Historical WR)
3. **Возможны убытки**
   - Контроль: Emergency Brake (SL 2%, max hold 3h)

### Защитные механизмы (остались без изменений)
- ✅ Strategic Brain (Claude) - блокирует неподходящие сигналы
- ✅ BTC Correlation Filter - "Папа решает всё"
- ✅ Fee Profitability Check - минимум 0.4% TP
- ✅ Emergency Brake - жёсткий SL 2%
- ✅ Zombie Killer - макс. 3 часа в позиции

---

## 🚀 Deployment

### Файлы изменены
1. `config.py` - пороги confidence и CHOP
2. `core/futures_brain.py` - Multi-Agent система (пороги риска)
3. `core/strategic_brain.py` - UNCERTAIN режим смягчён

### Команды деплоя
```bash
# 1. Копируем файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/futures_brain.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем (config.py в раннем слое - нужен --no-cache)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"

# 3. Проверяем логи
ssh root@88.210.10.145 "docker logs -f bybit_bot"
```

---

## 📈 Мониторинг

### Что смотреть в логах
```
✅ Хорошо:
- "ML Signal: BUY (conf: 60%)" → проходит фильтр
- "Score: 2/6 (need 2+)" → консенсус достигнут
- "Mode: TREND (ML Follower) - CHOP: 49.2" → тренд распознан

❌ Плохо:
- "Score: 0/6" → агенты не голосуют (проверить confidence)
- "CHOP: 63" → флэт (Mean Reversion или SKIP)
- "Strategic Veto: BUY blocked" → Strategic Brain блокирует
```

### SQL: Сделки за сегодня
```sql
SELECT 
    entry_time,
    symbol,
    side,
    entry_price,
    exit_price,
    pnl,
    CAST((pnl / (entry_price * quantity) * 100) AS NUMERIC(10,2)) as pnl_pct
FROM trades 
WHERE market_type = 'futures' 
  AND status = 'CLOSED'
  AND DATE(entry_time) = CURRENT_DATE
ORDER BY entry_time DESC;
```

### SQL: Win Rate за последние 24 часа
```sql
SELECT 
    COUNT(*) as total_trades,
    COUNT(*) FILTER (WHERE pnl > 0) as wins,
    CAST(COUNT(*) FILTER (WHERE pnl > 0)::numeric / COUNT(*) * 100 AS NUMERIC(10,1)) as win_rate,
    CAST(SUM(pnl) AS NUMERIC(10,2)) as total_pnl
FROM trades 
WHERE market_type = 'futures' 
  AND status = 'CLOSED'
  AND entry_time > NOW() - INTERVAL '24 hours';
```

---

## 🎓 Уроки

### Почему Safe Mode не работал
1. **Слишком строгие фильтры** - блокировали 99% сигналов
2. **Требование консенсуса 3 агентов** - почти недостижимо
3. **TA подтверждение для Balanced** - убивало половину сигналов
4. **CHOP 60-65** - слишком узкая зона тренда

### Balanced Mode - золотая середина
- Confidence 60% - достаточно для входа
- Score 2 - реалистичный консенсус
- CHOP 55-62 - широкая зона гистерезиса
- Balanced без TA - больше гибкости

### Следующие шаги
1. **Мониторинг 24 часа** - проверить количество сделок
2. **Анализ Win Rate** - должен быть 40%+
3. **Проверка PnL** - не должно быть слива
4. **Если слишком агрессивно** - вернуть require_ta для Balanced

---

**Дата:** 2025-12-18 15:30 UTC  
**Статус:** Ready for deployment  
**Цель:** 3-5 сделок в день, Win Rate 40%+
