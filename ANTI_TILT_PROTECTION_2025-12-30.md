# 🛡️ Anti-Tilt Protection - Circuit Breaker & Loss Cooldown

**Дата:** 30 декабря 2025  
**Версия:** v9.0  
**Статус:** ✅ Готово к деплою

---

## 🎯 Проблема

Анализ недельной статистики (23-30 декабря) выявил две критические проблемы:

### 1. "Тильт" бота (Over-Trading)
- **26 декабря:** 22 сделки за день → убыток -$16.60 (-16% от баланса!)
- Бот не останавливается при серии убытков
- Продолжает торговать даже когда рынок против него

### 2. "Удушение" прибыли (Premature Breakeven)
- **20% сделок** закрываются в Breakeven (PnL = 0)
- Trailing Stop активируется слишком рано (0.8% профита)
- Цена не успевает "подышать" → ложные срабатывания

### Статистика за неделю:
- **Всего сделок:** 104
- **Win Rate:** 40.4% (недостаточно для прибыльности)
- **Breakeven:** 21 сделка (20.2%)
- **Net PnL:** -$12.48
- **Худший день:** 26 дек (-$16.60)

---

## 🛠️ Решение

### 1. Daily Loss Limit (Circuit Breaker)

**Концепция:** Блокировка торговли при превышении дневного лимита убытков.

**Параметры:**
```python
daily_loss_limit_enabled: bool = True
max_daily_loss_percent: float = 0.03  # 3% от баланса
```

**Логика:**
1. Считаем Net PnL за сегодня (с 00:00 UTC)
2. Если убыток > 3% от баланса → **БЛОКИРОВКА**
3. Торговля возобновляется в 00:00 UTC следующего дня

**Пример:**
- Баланс: $178
- Лимит убытков: $5.34 (3%)
- Если за день потеряли > $5.34 → торговля остановлена до завтра

**Логирование:**
```
⛔ DAILY LOSS LIMIT REACHED!
   Today's Loss: $6.20 (limit: $5.34)
   Trading halted until 2025-12-31 00:00 UTC (8.5h remaining)
```

---

### 2. Loss Cooldown (Anti-Whipsaw)

**Концепция:** Пауза после убыточной сделки на конкретной паре.

**Параметры:**
```python
loss_cooldown_enabled: bool = True
loss_cooldown_minutes: int = 45  # 45 минут
```

**Логика:**
1. Сделка на SOLUSDT закрылась с убытком
2. Блокируем SOLUSDT на 45 минут
3. Другие пары торгуются нормально
4. Через 45 минут SOLUSDT снова доступен

**Пример:**
- 10:00 - SOLUSDT SHORT закрылся с -$2.50
- 10:00-10:45 - SOLUSDT заблокирован
- 10:45 - SOLUSDT снова доступен

**Логирование:**
```
⏸️  SOLUSDT in COOLDOWN after loss ($-2.50)
   Last loss: 10:00:15 UTC
   Wait 42.3 minutes (until 10:45:00 UTC)
```

**Цель:** Предотвратить серию убытков на "пиле" (whipsaw).

---

### 3. Ослабление Trailing Stop

**Было:**
```python
trailing_activation_pct: float = 0.8  # Активация при +0.8%
trailing_callback_pct: float = 0.4    # Дистанция 0.4%
```

**Стало:**
```python
trailing_activation_pct: float = 1.0  # Активация при +1.0% (УВЕЛИЧЕНО)
trailing_callback_pct: float = 0.5    # Дистанция 0.5% (УВЕЛИЧЕНО)
```

**Эффект:**
- Цена должна вырасти на **1.0%** (вместо 0.8%) для активации трейлинга
- Больше "воздуха" для цены → меньше ложных срабатываний
- Меньше Breakeven сделок (цель: с 20% до 10%)

---

## 📁 Изменённые файлы

### 1. `config.py`
**Добавлено:**
```python
# ========== ANTI-TILT PROTECTION (Circuit Breaker) - 30.12.2025 ==========
daily_loss_limit_enabled: bool = True
max_daily_loss_percent: float = 0.03  # 3% от баланса

# ========== LOSS COOLDOWN (Anti-Whipsaw) - 30.12.2025 ==========
loss_cooldown_enabled: bool = True
loss_cooldown_minutes: int = 45  # 45 минут пауза

# ========== TRAILING STOP Settings - ANTI-TILT UPDATE ==========
trailing_activation_pct: float = 1.0  # УВЕЛИЧЕНО с 0.8%
trailing_callback_pct: float = 0.5    # УВЕЛИЧЕНО с 0.4%
```

### 2. `core/risk_manager.py` (НОВЫЙ)
**Функции:**
- `check_daily_loss_limit()` - проверка дневного лимита
- `check_loss_cooldown()` - проверка cooldown на паре
- `can_open_position()` - комплексная проверка перед открытием
- `register_loss()` - регистрация убытка для cooldown

**Singleton:**
```python
from core.risk_manager import get_risk_manager
risk_manager = get_risk_manager()
```

### 3. `core/hybrid_loop.py`
**Интеграция:**
```python
# Импорт
from core.risk_manager import get_risk_manager

# Инициализация
self.risk_manager = get_risk_manager()

# Проверка перед открытием позиции
if self.risk_manager:
    can_trade, reason = await self.risk_manager.can_open_position(
        session=session,
        symbol=symbol,
        current_balance=current_balance
    )
    
    if not can_trade:
        print(f"\n{reason}")
        return  # Пропускаем сигнал
```

---

## 🚀 Deployment

### Шаг 1: Копируем файлы на сервер
```bash
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/risk_manager.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/
```

### Шаг 2: Пересобираем контейнер
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"
```

### Шаг 3: Перезапускаем бота
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Шаг 4: Проверяем логи
```bash
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100 | grep -E '(Risk Manager|DAILY LOSS|COOLDOWN)'"
```

**Ожидаемый вывод:**
```
✅ Risk Manager initialized
   📊 Daily Loss Limit: 3.0% of balance
   ⏸️  Loss Cooldown: 45 minutes per symbol
   Risk Manager: ✅ Enabled (Anti-Tilt Protection)
```

---

## 📊 Ожидаемые результаты

### До изменений (23-30 дек):
- **Сделок в день:** 5-33 (нестабильно)
- **Win Rate:** 40.4%
- **Breakeven:** 20.2%
- **Худший день:** -$16.60 (26 дек)
- **Net PnL за неделю:** -$12.48

### После изменений (цель):
- **Сделок в день:** 3-10 (стабильно)
- **Win Rate:** 50%+ (цель)
- **Breakeven:** 10% (снижено с 20%)
- **Худший день:** -$5.34 максимум (Circuit Breaker)
- **Net PnL за неделю:** положительный

### Ключевые метрики:

**1. Circuit Breaker эффективность:**
- Если бы был активен 26 декабря:
  - Убыток: -$5.34 (вместо -$16.60)
  - Сэкономлено: **$11.26**

**2. Loss Cooldown эффективность:**
- Предотвращает серии убытков на одной паре
- Цель: снизить количество подряд идущих losses с 3-4 до 1-2

**3. Trailing Stop эффективность:**
- Breakeven сделки: с 20% до 10%
- Больше прибыльных сделок доходят до TP

---

## 🔍 Мониторинг

### SQL: Проверка Daily Loss Limit
```sql
-- Убыток за сегодня
SELECT 
    ROUND(SUM(pnl - fee_entry - fee_exit)::numeric, 2) as today_net_pnl,
    COUNT(*) as trades_today
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND exit_time >= CURRENT_DATE;
```

### SQL: Проверка Loss Cooldown
```sql
-- Последние убытки по парам
SELECT 
    symbol,
    ROUND(pnl::numeric, 2) as loss,
    exit_time,
    NOW() - exit_time as time_since_loss
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND pnl < 0
ORDER BY exit_time DESC
LIMIT 10;
```

### SQL: Breakeven сделки
```sql
-- Процент Breakeven сделок
SELECT 
    COUNT(*) FILTER (WHERE pnl = 0) as breakeven_count,
    COUNT(*) as total_trades,
    ROUND(COUNT(*) FILTER (WHERE pnl = 0)::numeric / COUNT(*) * 100, 1) as breakeven_pct
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND exit_time > NOW() - INTERVAL '7 days';
```

---

## 🎯 Цели на следующую неделю (31 дек - 6 янв)

1. **Win Rate:** 50%+ (сейчас 40.4%)
2. **Breakeven:** <10% (сейчас 20.2%)
3. **Daily Loss:** не более -$5.34 в любой день
4. **Net PnL:** положительный за неделю
5. **Стабильность:** 3-10 сделок в день (не 22!)

---

## 📝 Примечания

### Отключение защиты (если нужно):
```python
# В config.py
daily_loss_limit_enabled: bool = False  # Отключить Circuit Breaker
loss_cooldown_enabled: bool = False     # Отключить Loss Cooldown
```

### Настройка параметров:
```python
# Более жёсткий лимит (2% вместо 3%)
max_daily_loss_percent: float = 0.02

# Более длинный cooldown (60 минут вместо 45)
loss_cooldown_minutes: int = 60

# Более консервативный trailing (1.5% вместо 1.0%)
trailing_activation_pct: float = 1.5
```

---

**Статус:** ✅ Готово к деплою  
**Приоритет:** 🔴 КРИТИЧЕСКИЙ (защита от тильта)  
**Тестирование:** Мониторинг 7 дней (31 дек - 6 янв)
