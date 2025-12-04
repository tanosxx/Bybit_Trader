# Simulated Realism - Учёт комиссий в Demo режиме

## 🎯 Цель

Подготовка к переходу на Real Trading с реалистичным учётом комиссий и спредов в Demo режиме.

## 📊 Что добавлено

### 1. Конфигурация комиссий (`config.py`)

```python
# Новые параметры
estimated_fee_rate: float = 0.0006  # 0.06% Taker fee (Bybit standard)
min_profit_threshold_multiplier: float = 2.0  # Минимальный профит = 2x комиссия
simulate_fees_in_demo: bool = True  # Учитывать комиссии в Demo
```

**Bybit Fees (Futures):**
- Maker: 0.02% (0.0002)
- Taker: 0.06% (0.0006) ← используем этот
- Funding Rate: 0.01% каждые 8 часов (уже учитывается в `funding_rate_filter`)

### 2. Функции расчёта комиссий

#### `calculate_fees(entry_value, exit_value)`
Рассчитывает комиссии для сделки:
- Entry Fee = Entry Value × 0.06%
- Exit Fee = Exit Value × 0.06%
- Total Fee = Entry Fee + Exit Fee

#### `calculate_net_pnl(gross_pnl, entry_value, exit_value)`
Рассчитывает чистый PnL:
- Gross PnL: как показывает биржа
- Fees: Entry Fee + Exit Fee
- Net PnL: Gross PnL - Fees (реально в карман)
- Fee Impact %: влияние комиссий на прибыль

#### `is_trade_profitable_after_fees(entry_price, take_profit, quantity, side)`
Проверяет прибыльность сделки:
- Рассчитывает Gross Profit
- Вычитает комиссии
- Проверяет: Net Profit > 0 AND Gross Profit >= 2× Fees
- Возвращает: is_profitable, gross_profit, net_profit, reason

### 3. Фильтр в AI Brain (`ai_brain_local.py`)

**Новый шаг в Decision Tree:**

```
ШАГ 4: FEE PROFITABILITY CHECK
├─ Рассчитываем TP на основе ML predicted_change_pct
├─ Проверяем: is_trade_profitable_after_fees()
├─ Если НЕ прибыльна → SKIP
└─ Если прибыльна → продолжаем
```

**Логика блокировки:**
- Если Gross Profit < 2× Total Fees → SKIP
- Если Net Profit <= 0 → SKIP
- Иначе → разрешаем вход

**Пример:**
```
Entry: $100, TP: $100.50 (+0.5%)
Entry Fee: $0.06, Exit Fee: $0.06
Total Fees: $0.12
Gross Profit: $0.50
Min Required: $0.24 (2× fees)
✅ PASS: $0.50 > $0.24
Net Profit: $0.38 (в карман)
```

### 4. Telegram уведомления (`telegram_notifier.py`)

**Обновлённый формат закрытия позиции:**

```
💰 TAKE PROFIT

#BTCUSDT (LONG)
📈 Exit: $93,500.00
💵 Gross PnL: +$15.50 (+1.5%)
💸 Fees: -$1.24
💰 Net PnL: +$14.26 (in pocket)
⏱️ Duration: 45m
```

**Показываем:**
- Gross PnL: валовая прибыль (как на бирже)
- Fees: сумма комиссий
- Net PnL: чистая прибыль (реально в карман)

## 📈 Влияние на торговлю

### До внедрения:
- Открывались сделки с TP +0.3-0.5%
- Не учитывались комиссии 0.12%
- Виртуальный профит не соответствовал реальному

### После внедрения:
- Блокируются сделки с TP < 0.24% (2× комиссия)
- Минимальный TP теперь ~0.5-0.8%
- Реалистичная оценка прибыльности

### Ожидаемый эффект:
- ✅ Меньше сделок (более строгий отбор)
- ✅ Выше качество входов
- ✅ Реалистичная статистика PnL
- ✅ Готовность к Real Trading

## 🔧 Настройка

### Включить/выключить симуляцию комиссий:
```python
# .env или config.py
SIMULATE_FEES_IN_DEMO=True  # Включить
SIMULATE_FEES_IN_DEMO=False  # Выключить (старое поведение)
```

### Изменить ставку комиссии:
```python
ESTIMATED_FEE_RATE=0.0006  # 0.06% (Taker)
ESTIMATED_FEE_RATE=0.0002  # 0.02% (Maker) - если используете лимитные ордера
```

### Изменить порог прибыльности:
```python
MIN_PROFIT_THRESHOLD_MULTIPLIER=2.0  # Минимум 2× комиссия (по умолчанию)
MIN_PROFIT_THRESHOLD_MULTIPLIER=3.0  # Минимум 3× комиссия (более строго)
```

## 📊 Пример расчёта

### Сделка 1: LONG BTCUSDT
```
Entry: $93,000 × 0.01 BTC = $930
TP: $93,500 × 0.01 BTC = $935
Gross Profit: $5.00 (+0.54%)

Entry Fee: $930 × 0.06% = $0.558
Exit Fee: $935 × 0.06% = $0.561
Total Fees: $1.119

Net Profit: $5.00 - $1.12 = $3.88 (+0.42%)
Min Required: $1.12 × 2 = $2.24

✅ PASS: $5.00 > $2.24
```

### Сделка 2: SHORT ETHUSDT (заблокирована)
```
Entry: $3,500 × 0.1 ETH = $350
TP: $3,510 × 0.1 ETH = $351
Gross Profit: $1.00 (+0.29%)

Entry Fee: $350 × 0.06% = $0.21
Exit Fee: $351 × 0.06% = $0.21
Total Fees: $0.42

Net Profit: $1.00 - $0.42 = $0.58 (+0.17%)
Min Required: $0.42 × 2 = $0.84

❌ BLOCKED: $1.00 < $0.84 (profit too small)
```

## 🚀 Деплой

```bash
# 1. Копируем обновлённые файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/telegram_notifier.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем контейнеры
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose stop bot
docker rm -f bybit_bot
docker-compose build bot
docker-compose up -d bot

# 3. Проверяем логи
docker logs -f bybit_bot
```

## 📝 Проверка работы

Смотрим в логах:
```
🧠 Local Brain analyzing BTCUSDT...
   📰 News Sentiment: NEUTRAL (score: 0.00)
   🤖 ML Signal: BUY (conf: 65%, change: +0.8%)
   📊 TA Confirmation: ✅ (strength: 70%)
   ✅ Fee check passed: Profitable: $2.15 net (after $0.84 fees)
   ✅ Final Decision: BUY (conf: 70%, risk: 5/10)
```

Или блокировка:
```
   ⚠️  Trade blocked: Profit too small: $0.50 < $0.84 (min required)
```

## 💡 Рекомендации

1. **Оставить включённым** `simulate_fees_in_demo=True` для реалистичной подготовки
2. **Не снижать** `min_profit_threshold_multiplier` ниже 2.0 (иначе будут убытки)
3. **Мониторить** Net PnL в Telegram - это реальная прибыль
4. **Сравнить** статистику до/после внедрения (Win Rate должен вырасти)

## 🎯 Готовность к Real Trading

После 1-2 дней работы с Simulated Realism:
- ✅ Проверить Net PnL > 0
- ✅ Проверить Win Rate > 40%
- ✅ Убедиться что нет сделок с TP < 0.5%
- ✅ Проверить что комиссии не съедают >30% прибыли

Если всё ОК → можно переходить на Real Trading с уверенностью!

---

**Дата внедрения:** 2025-12-04  
**Версия:** v1.0  
**Статус:** ✅ Ready for deployment
