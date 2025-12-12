# Dynamic Strategy Scaler - Tier System - 12 декабря 2025

## 🎯 Концепция

**Dynamic Strategy Scaler** - система автоматического масштабирования торговой стратегии в зависимости от размера депозита.

### Проблема
- Баланс вырос с $100 до $377 (+277%)
- Но бот продолжал торговать с настройками для $100
- XRPUSDT (12.5% WR) и BTCUSDT (0% WR) съедали прибыль
- Нет автоматической адаптации к росту капитала

### Решение
**Tier-based система** с автоматическим переключением:
- **Tier 1 (Survival Mode):** $0-200 - Консервативная стратегия
- **Tier 2 (Growth Mode):** $200-600 - Сбалансированная стратегия
- **Tier 3 (Dominion Mode):** $600+ - Агрессивная стратегия

---

## 📊 Tier System

### Tier 1: Survival Mode ($0-200)
```json
{
  "name": "Survival Mode",
  "balance_range": "$0-200",
  "active_pairs": ["SOLUSDT", "ETHUSDT"],
  "max_open_positions": 3,
  "risk_per_trade": 12%,
  "min_confidence": 65%,
  "strategy": "Консервативная - только лучшие пары"
}
```

**Философия:**
- Фокус на выживании и стабильности
- Только топ-2 пары (SOL 60% WR, ETH 40% WR)
- Высокая уверенность (65%+)
- Минимум позиций (3)

---

### Tier 2: Growth Mode ($200-600)
```json
{
  "name": "Growth Mode",
  "balance_range": "$200-600",
  "active_pairs": ["SOLUSDT", "ETHUSDT", "BNBUSDT"],
  "max_open_positions": 5,
  "risk_per_trade": 10%,
  "min_confidence": 60%,
  "strategy": "Сбалансированная - рост капитала"
}
```

**Философия:**
- Баланс между ростом и безопасностью
- Добавляем BNB (25% WR, но стабильный)
- Средняя уверенность (60%+)
- Больше позиций (5)

**Текущий баланс $377 → Tier 2** ✅

---

### Tier 3: Dominion Mode ($600+)
```json
{
  "name": "Dominion Mode",
  "balance_range": "$600+",
  "active_pairs": ["SOLUSDT", "ETHUSDT", "BNBUSDT", "AVAXUSDT", "DOGEUSDT"],
  "max_open_positions": 7,
  "risk_per_trade": 8%,
  "min_confidence": 55%,
  "strategy": "Агрессивная - доминирование рынка"
}
```

**Философия:**
- Максимальная диверсификация
- Добавляем AVAX и DOGE (новые возможности)
- Низкая уверенность (55%+) - больше сделок
- Максимум позиций (7)

---

## 🚫 Исключённые пары

### XRPUSDT - УДАЛЁН ИЗ ВСЕХ TIER-ОВ
```
Причина: Низкий WinRate (12.5%)
Статистика: 168 сделок, только 21 win
Проблема: Много шума, мало профита ($21.77)
Комиссии: Съедают большую часть прибыли
Решение: Полное исключение из торговли
```

### BTCUSDT - УДАЛЁН ИЗ ТОРГОВЛИ
```
Причина: 0% WinRate (убыток)
Статистика: 2 сделки, обе убыточные (-$1.90)
Проблема: Система не умеет торговать BTC
Решение: Исключён из active_pairs
НО: Остаётся в symbols_to_scan для BTC Correlation Filter!
```

**Важно:** BTCUSDT сканируется для анализа корреляции, но не торгуется!

---

## 🏗️ Архитектура

### Файлы

**1. settings.json** - Конфигурация Tier-ов
```json
{
  "strategy_tiers": {
    "tier_1": {...},
    "tier_2": {...},
    "tier_3": {...}
  },
  "excluded_pairs": {
    "XRPUSDT": "Low WinRate...",
    "BTCUSDT": "0% WinRate..."
  },
  "scan_pairs": {
    "pairs": ["BTCUSDT", "ETHUSDT", ...]
  }
}
```

**2. core/strategy_scaler.py** - Логика масштабирования
```python
class StrategyScaler:
    def get_tier_for_balance(balance) -> Dict
    def update_strategy(balance) -> Dict
    def get_symbols_to_scan(active_pairs) -> List
    def is_pair_allowed(symbol) -> bool
```

**3. core/hybrid_loop.py** - Интеграция в главный цикл
```python
# Инициализация
self.strategy_scaler = get_strategy_scaler()

# В начале каждого цикла (каждые 10 минут)
strategy_update = self.strategy_scaler.update_strategy(current_balance)

if strategy_update['tier_changed']:
    # Обновляем настройки
    settings.futures_pairs = strategy_update['active_pairs']
    settings.futures_max_open_positions = strategy_update['max_open_positions']
    # ...
```

**4. core/telegram_notifier.py** - Уведомления
```python
async def notify_strategy_upgrade(tier_name, balance, active_pairs, max_positions)
```

---

## 🔄 Алгоритм работы

```
┌─────────────────────────────────────────────────────────────┐
│ STRATEGY SCALER - Цикл обновления (каждые 10 минут)        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ 1. Получить текущий баланс из БД      │
        │    current_balance = load_from_db()   │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ 2. Определить Tier для баланса        │
        │    tier = get_tier_for_balance()      │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ 3. Tier изменился?                    │
        └───────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
                   ДА              НЕТ
                    │               │
                    ▼               ▼
        ┌───────────────────────────────────────┐
        │ 4A. ОБНОВЛЕНИЕ НАСТРОЕК:              │
        │ - settings.futures_pairs              │
        │ - settings.max_open_positions         │
        │ - settings.risk_per_trade             │
        │ - settings.min_confidence             │
        └───────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────┐
        │ 5. Уведомление в Telegram             │
        │    "🚀 STRATEGY UPGRADE"               │
        └───────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────┐
        │ 6. Получить symbols_to_scan           │
        │    (active_pairs + BTCUSDT)           │
        └───────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────┐
        │ 7. Продолжить торговый цикл           │
        │    с новыми настройками               │
        └───────────────────────────────────────┘
```

---

## 🧪 Тестирование

### Тестовый скрипт: test_strategy_scaler.py

```bash
# Запуск теста
docker exec bybit_bot python3 test_strategy_scaler.py
```

**Тестовые сценарии:**
- $50 → Tier 1 (SOL, ETH)
- $150 → Tier 1 (SOL, ETH)
- $250 → Tier 2 (SOL, ETH, BNB)
- **$377 → Tier 2 (SOL, ETH, BNB)** ← Текущий баланс
- $500 → Tier 2 (SOL, ETH, BNB)
- $700 → Tier 3 (SOL, ETH, BNB, AVAX, DOGE)
- $1000 → Tier 3 (SOL, ETH, BNB, AVAX, DOGE)

**Проверки:**
- ✅ BTCUSDT в symbols_to_scan (для корреляции)
- ✅ XRPUSDT исключён из всех Tier-ов
- ✅ BTCUSDT исключён из active_pairs
- ✅ Правильные настройки для каждого Tier

---

## 📈 Ожидаемые результаты

### До внедрения (текущее состояние):
```
Balance: $377
Active Pairs: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT (5)
Max Positions: 5
Risk per Trade: 12%
Win Rate: 28.1%
Problem: XRPUSDT (12.5% WR) и BTCUSDT (0% WR) тянут вниз
```

### После внедрения (Tier 2):
```
Balance: $377
Active Pairs: SOLUSDT, ETHUSDT, BNBUSDT (3)
Max Positions: 5
Risk per Trade: 10%
Expected Win Rate: 40%+ (только прибыльные пары)
Benefit: Фокус на качестве, не количестве
```

### Прогноз роста:
```
Tier 1 ($0-200):
  - Консервативная стратегия
  - Медленный рост
  - Фокус на выживании

Tier 2 ($200-600):
  - Сбалансированная стратегия
  - Стабильный рост
  - Оптимальный риск/доходность

Tier 3 ($600+):
  - Агрессивная стратегия
  - Быстрый рост
  - Максимальная диверсификация
```

---

## 🚀 Deployment

### Шаг 1: Копируем файлы
```bash
# Settings
scp Bybit_Trader/settings.json root@88.210.10.145:/root/Bybit_Trader/

# Strategy Scaler
scp Bybit_Trader/core/strategy_scaler.py root@88.210.10.145:/root/Bybit_Trader/core/

# Hybrid Loop (обновлённый)
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/

# Telegram Notifier (обновлённый)
scp Bybit_Trader/core/telegram_notifier.py root@88.210.10.145:/root/Bybit_Trader/core/

# Test script
scp Bybit_Trader/test_strategy_scaler.py root@88.210.10.145:/root/Bybit_Trader/
```

### Шаг 2: Тестируем
```bash
# Запускаем тест
ssh root@88.210.10.145 "docker exec bybit_bot python3 test_strategy_scaler.py"

# Проверяем что:
# - Tier 2 выбран для $377
# - XRPUSDT исключён
# - BTCUSDT в scan list, но не в active_pairs
```

### Шаг 3: Пересобираем контейнер
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"
ssh root@88.210.10.145 "docker stop bybit_bot && docker rm bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Шаг 4: Проверяем логи
```bash
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100 | grep -E '(STRATEGY|Tier|Active Pairs)'"
```

**Ожидаемый вывод:**
```
🎯 Strategy Scaler initialized
   Tiers loaded: 3
   Excluded pairs: XRPUSDT, BTCUSDT

🚀 STRATEGY UPGRADE: Tier Change Detected!
   Balance: $377.53
   Old Tier: None
   New Tier: Growth Mode (tier_2)
   Active Pairs: SOLUSDT, ETHUSDT, BNBUSDT
   Max Positions: 5
   Risk per Trade: 10%
```

---

## 💡 Преимущества

### 1. Автоматическая адаптация
- ✅ Стратегия меняется с ростом капитала
- ✅ Нет ручного вмешательства
- ✅ Оптимальные настройки для каждого уровня

### 2. Исключение убыточных пар
- ✅ XRPUSDT (12.5% WR) удалён
- ✅ BTCUSDT (0% WR) удалён из торговли
- ✅ Фокус на прибыльных парах (SOL 60%, ETH 40%)

### 3. Умное сканирование
- ✅ BTCUSDT сканируется для корреляции
- ✅ Но не торгуется (0% WR)
- ✅ BTC Correlation Filter работает

### 4. Масштабируемость
- ✅ Легко добавить новые Tier-ы
- ✅ Легко добавить новые пары
- ✅ Гибкая конфигурация через JSON

### 5. Прозрачность
- ✅ Уведомления в Telegram при смене Tier
- ✅ Детальные логи
- ✅ Статистика по всем Tier-ам

---

## 📊 Мониторинг

### Команды проверки:

**1. Текущий Tier:**
```bash
docker exec bybit_bot python3 -c "
from core.strategy_scaler import get_strategy_scaler
from core.executors.futures_executor import get_futures_executor
import asyncio

async def check():
    scaler = get_strategy_scaler()
    executor = get_futures_executor()
    balance = await executor.load_balance_from_db()
    result = scaler.update_strategy(balance)
    print(f'Balance: \${balance:.2f}')
    print(f'Tier: {result[\"tier_name\"]}')
    print(f'Active Pairs: {result[\"active_pairs\"]}')

asyncio.run(check())
"
```

**2. Статистика Tier-ов:**
```bash
docker exec bybit_bot python3 test_strategy_scaler.py
```

**3. Проверка исключённых пар:**
```bash
docker logs bybit_bot | grep -E "(XRPUSDT|BTCUSDT)" | tail -20
```

---

## 🎯 Итоги

### Что сделано:
1. ✅ Создан Tier System (3 уровня)
2. ✅ Исключены убыточные пары (XRP, BTC)
3. ✅ Автоматическое масштабирование
4. ✅ Интеграция в главный цикл
5. ✅ Уведомления в Telegram
6. ✅ Тестовый скрипт

### Текущий статус:
- **Balance:** $377.53
- **Tier:** Growth Mode (Tier 2)
- **Active Pairs:** SOLUSDT, ETHUSDT, BNBUSDT
- **Excluded:** XRPUSDT, BTCUSDT
- **Expected WR:** 40%+ (vs 28.1% сейчас)

### Следующие шаги:
1. Деплой на сервер
2. Мониторинг 24-48 часов
3. Анализ улучшения Win Rate
4. Добавление новых пар в Tier 3 (AVAX, DOGE)

---

**Дата:** 2025-12-12 22:30 UTC  
**Версия:** Strategy Scaler v1.0  
**Статус:** ✅ Готово к деплою
