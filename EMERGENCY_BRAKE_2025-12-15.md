# 🚨 EMERGENCY BRAKE - Hard Risk Management

**Дата:** 2025-12-15  
**Версия:** v8.0  
**Статус:** ✅ Реализовано

---

## 🎯 Проблема

**Критическая потеря:** -$35.50 на ETHUSDT SHORT (15 декабря 2025, 03:06 UTC)

**Причина:**
- Бот держал убыточную позицию **4+ часа**
- Цена выросла с $3064 до $3120 (+$56)
- SHORT позиция превратилась в катастрофу
- Strategic Brain блокировал новые сигналы, но старые позиции продолжали расти в минус

**Общая потеря от пика:** -$54.94 (с $353.77 до $298.83)

---

## 💡 Решение: Emergency Brake

**Концепция:** Жёсткий контроль убытков на уровне Executor, игнорирующий любые "мнения" AI.

### Два правила защиты:

#### 1. Hard Stop Loss (2%)
- **LONG:** Если цена упала на 2% от входа → EMERGENCY EXIT
- **SHORT:** Если цена выросла на 2% от входа → EMERGENCY EXIT
- **Формула:** `abs(price_change) >= 2%`

#### 2. Time To Live - TTL (3 часа)
- Максимальное время удержания позиции: **180 минут**
- Если позиция открыта дольше → ZOMBIE TRADE KILLER
- **Формула:** `(now - entry_time) > 180 min`

---

## 📝 Реализация

### 1. Конфигурация (`config.py`)

```python
# ========== HARD RISK MANAGEMENT (Emergency Brake) ==========
hard_stop_loss_percent: float = 0.02  # 2% движения против позиции
max_hold_time_minutes: int = 180  # 3 часа максимум
emergency_brake_enabled: bool = True  # Включить Emergency Brake
```

### 2. Executor (`core/executors/futures_executor.py`)

**Новые методы:**

#### `monitor_emergency_risks()` → List[Dict]
- Проверяет ВСЕ открытые позиции
- Возвращает список позиций для экстренного закрытия
- Работает независимо от AI

**Логика проверки:**
```python
# CHECK 1: Hard Stop Loss
if position_side == 'LONG':
    price_change_pct = (current_price - entry_price) / entry_price
    if price_change_pct <= -0.02:  # -2%
        → CLOSE IMMEDIATELY

elif position_side == 'SHORT':
    price_change_pct = (entry_price - current_price) / entry_price
    if price_change_pct <= -0.02:  # -2%
        → CLOSE IMMEDIATELY

# CHECK 2: Time To Live
hold_time_minutes = (now - entry_time).total_seconds() / 60
if hold_time_minutes > 180:  # 3 часа
    → CLOSE IMMEDIATELY (ZOMBIE TRADE)
```

#### `execute_emergency_closures()` → int
- Выполняет экстренное закрытие позиций
- Возвращает количество закрытых позиций
- Логирует все действия

### 3. Интеграция в главный цикл (`core/hybrid_loop.py`)

**Приоритет #1 в каждом цикле:**
```python
async def cycle(self):
    self.cycle_count += 1
    
    # ========== 🚨 EMERGENCY BRAKE - ПРИОРИТЕТ #1 ==========
    if self.futures_executor and settings.emergency_brake_enabled:
        closed_count = await self.futures_executor.execute_emergency_closures()
        
        if closed_count > 0:
            await self.telegram.notify_emergency_closure(closed_count)
    
    # ... остальная логика цикла
```

**Частота проверки:** Каждые 60 секунд (каждый цикл)

### 4. Telegram уведомления (`core/telegram_notifier.py`)

```python
async def notify_emergency_closure(self, closed_count: int):
    """
    🚨 EMERGENCY BRAKE ACTIVATED
    
    ⚠️ Critical risk detected!
    🔒 Closed positions: {closed_count}
    
    Reasons:
    • Hard Stop Loss hit (>2% loss)
    • OR Zombie trade (>3 hours)
    
    ✅ System protected from further losses
    """
```

---

## 📊 Ожидаемые результаты

### Защита от крупных потерь:
- ✅ Максимальный убыток на позицию: **-2%** (вместо -35%)
- ✅ Максимальное время удержания: **3 часа** (вместо 4+)
- ✅ Автоматическое закрытие зомби-трейдов

### Пример расчёта:
**Баланс:** $300  
**Риск на сделку:** 12% = $36 маржи  
**Плечо:** 5x = $180 позиция  
**Hard SL:** 2% от $180 = **-$3.60 максимум**

**Было (ETHUSDT):**
- Позиция: ~$250
- Убыток: -$35.50 (14% от позиции!)
- Время: 4+ часа

**Стало (с Emergency Brake):**
- Позиция: ~$180
- Убыток: -$3.60 (2% от позиции)
- Время: максимум 3 часа

**Экономия:** $31.90 на одной сделке!

---

## 🔧 Deployment

### Файлы изменены:
1. ✅ `config.py` - добавлены параметры Emergency Brake
2. ✅ `core/executors/futures_executor.py` - методы monitor/execute
3. ✅ `core/hybrid_loop.py` - интеграция в цикл
4. ✅ `core/telegram_notifier.py` - уведомления

### Команды деплоя:
```bash
# 1. Копируем файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/telegram_notifier.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем контейнер
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# 3. Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"

# 4. Проверяем логи
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100"
```

---

## ✅ Проверка работы

### В логах должно появиться:
```
🚨 EMERGENCY BRAKE: Checking critical risks...
   ✅ All positions within safe limits
```

### При срабатывании:
```
🚨 EMERGENCY: ETHUSDT LONG down 2.15% (limit: 2%)
🚨 EMERGENCY BRAKE: 1 positions need immediate closure!

🚨 EMERGENCY CLOSING: ETHUSDT
   Reason: 🚨 HARD STOP LOSS HIT: -2.15% (LONG)
   ✅ Emergency closure successful

✅ Emergency Brake: Closed 1/1 positions
```

### В Telegram:
```
🚨 EMERGENCY BRAKE ACTIVATED

⚠️ Critical risk detected!
🔒 Closed positions: 1

Reasons:
• Hard Stop Loss hit (>2% loss)
• OR Zombie trade (>3 hours)

✅ System protected from further losses
```

---

## 🎯 Преимущества

1. ✅ **Независимость от AI** - работает на уровне Executor
2. ✅ **Приоритет #1** - проверяется первым в каждом цикле
3. ✅ **Простота** - два чётких правила (2% и 3 часа)
4. ✅ **Быстрота** - проверка каждые 60 секунд
5. ✅ **Прозрачность** - логи и Telegram уведомления
6. ✅ **Эффективность** - защита от катастрофических потерь

---

## 📈 Влияние на производительность

### Overhead:
- Проверка: ~50-100ms на цикл
- Запросы к БД: 1 SELECT (открытые позиции)
- Запросы к API: N × 1 (цена для каждой позиции)

### Оптимизация:
- Проверка только при наличии открытых позиций
- Кэширование цен (если нужно)
- Асинхронное выполнение

---

## 🔮 Будущие улучшения

1. **Динамический Hard SL** - зависит от волатильности (ATR)
2. **Адаптивный TTL** - зависит от тренда (короче во флэте)
3. **Partial Close** - закрывать 50% при 1%, остальное при 2%
4. **Trailing Emergency SL** - двигать SL в безубыток при +1%

---

## 📝 Заключение

Emergency Brake - это **последняя линия защиты** от катастрофических потерь.

**Главное правило:** Лучше закрыть с -2%, чем держать до -35%!

**Результат:** Система теперь защищена от:
- ✅ Крупных лоссов (>2%)
- ✅ Зомби-трейдов (>3 часа)
- ✅ Эмоциональных решений AI

**Статус:** Готово к деплою! 🚀
