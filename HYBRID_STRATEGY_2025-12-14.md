# 🔄 HYBRID STRATEGY SELECTOR - 14 декабря 2025

## Проблема
Бот работал только по стратегии **Trend Following** (ML + VADER), которая отлично работает на тренде, но молчит во флэте.

**Статистика последних 3 дней:**
- 9 декабря: 101 сделка, +$203.81 (ТРЕНД!)
- 10 декабря: 38 сделок, +$6.98
- 11 декабря: 2 сделки, +$2.78
- 12 декабря: 28 сделок, -$3.07 (флэт!)
- 13 декабря: 9 сделок, +$1.77

**Причина:** CHOP > 60 блокирует 95% сигналов (защита от убытков во флэте).

## Решение: Hybrid Strategy Selector

Бот теперь **автоматически выбирает стратегию** в зависимости от состояния рынка (индикатор CHOP).

### Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID STRATEGY SELECTOR                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  CHOP Index (14) → Определяет режим рынка                   │
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  CHOP < 60       │         │  CHOP >= 60      │          │
│  │  ТРЕНД           │         │  ФЛЭТ            │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                            │                     │
│           ▼                            ▼                     │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │ TREND FOLLOWING  │         │ MEAN REVERSION   │          │
│  │ (ML + VADER)     │         │ (RSI Ping-Pong)  │          │
│  └──────────────────┘         └──────────────────┘          │
│                                                               │
│  • ML Predictions    │         • RSI < 30 → BUY             │
│  • Pattern Matching  │         • RSI > 70 → SELL            │
│  • News Sentiment    │         • BTC Safety Check           │
│  • BTC Correlation   │         • Strategic Brain Veto       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Стратегия 1: TREND FOLLOWING (CHOP < 60)

**Когда:** Рынок в тренде (CHOP < 60)

**Логика:**
- ML модель (LSTM v2) предсказывает направление
- Pattern Matching анализирует исторические паттерны
- News Sentiment (VADER) корректирует уверенность
- BTC Correlation Filter блокирует неподходящие сигналы

**Цель:** Поймать сильное движение

**Пример:**
```
🚀 Mode: TREND (ML Follower) - CHOP: 45.3
🤖 ML Signal: BUY (conf: 68%, change: +1.2%)
📰 News Sentiment: GREED (score: 0.45)
✅ BTC Correlation: BTC trend OK (+0.8%)
✅ Final Decision: BUY (conf: 72%, risk: 5/10)
```

### Стратегия 2: MEAN REVERSION (CHOP >= 60)

**Когда:** Рынок во флэте (CHOP >= 60)

**Логика:**
- Игнорируем ML (он не работает во флэте)
- Смотрим только на RSI (14)
- **BUY Signal:**
  - RSI < 30 (oversold)
  - BTC не обваливается (> -0.5%)
  - Strategic Brain не в режиме UNCERTAIN
- **SELL Signal:**
  - RSI > 70 (overbought)
  - BTC не пампится (< +0.5%)
  - Strategic Brain не в режиме UNCERTAIN

**Цель:** Торговать отскоки (buy low, sell high)

**Пример:**
```
🔄 Mode: FLAT (Mean Reversion) - CHOP: 65.8
✅ Mean Reversion Signal: BUY (conf: 75%)
📊 Mean Reversion: Oversold (RSI: 28.3), BTC OK (+0.2%)
✅ Final Decision: BUY (conf: 75%, risk: 6/10)
```

## Конфигурация (config.py)

```python
# ========== HYBRID STRATEGY SELECTOR ==========
mean_reversion_enabled: bool = True  # Включить Mean Reversion во флэте
chop_flat_threshold: float = 60.0  # CHOP >= 60 = флэт
chop_trend_threshold: float = 60.0  # CHOP < 60 = тренд

# Mean Reversion параметры
rsi_oversold: int = 30  # RSI < 30 = перепродан (BUY)
rsi_overbought: int = 70  # RSI > 70 = перекуплен (SELL)
mean_reversion_min_confidence: float = 0.65  # Минимальная уверенность
mean_reversion_btc_safety: bool = True  # Проверять BTC тренд
```

## Безопасность (Gatekeepers)

### 1. Strategic Brain Veto
- **UNCERTAIN** → НЕ торгуем (даже во флэте)
- **BEAR_CRASH** → Только SHORT (Mean Reversion учитывает)
- **BULL_RUSH** → Только LONG (Mean Reversion учитывает)
- **SIDEWAYS** → Всё разрешено

### 2. BTC Correlation Filter
- **BUY Signal:** Блокируется если BTC падает > -0.5%
- **SELL Signal:** Блокируется если BTC растёт > +0.5%
- **Цель:** Не ловить "падающие ножи"

### 3. Confidence Threshold
- Минимальная уверенность: 65% (настраивается)
- Ниже порога → SKIP

## Ожидаемые результаты

### Сценарий 1: Тренд (CHOP < 60)
- **Стратегия:** Trend Following (как раньше)
- **Сделок в день:** 5-15
- **Win Rate:** 30-50%
- **Avg Trade:** +$0.50 - $1.00

### Сценарий 2: Флэт (CHOP >= 60)
- **Стратегия:** Mean Reversion (НОВОЕ!)
- **Сделок в день:** 3-8
- **Win Rate:** 40-60% (выше чем в тренде!)
- **Avg Trade:** +$0.30 - $0.80

### Итого
- **Больше сделок:** +50-100% активности
- **Меньше простоя:** Торгуем и в тренде, и во флэте
- **Лучший Win Rate:** Mean Reversion эффективнее во флэте

## Мониторинг

### SQL: Статистика по стратегиям
```sql
SELECT 
    extra_data->>'strategy' as strategy,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
    ROUND(SUM(pnl)::numeric, 2) as total_pnl
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours'
GROUP BY extra_data->>'strategy';
```

### SQL: Mean Reversion эффективность
```sql
SELECT 
    symbol,
    COUNT(*) as mr_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
    ROUND(AVG((extra_data->>'rsi')::float), 1) as avg_rsi_entry
FROM trades 
WHERE status = 'CLOSED' 
  AND extra_data->>'strategy' = 'MEAN_REVERSION'
  AND entry_time > NOW() - INTERVAL '24 hours'
GROUP BY symbol;
```

### Логи
```bash
# Проверить режим работы
docker logs bybit_bot --tail 100 | grep -E "(Mode: TREND|Mode: FLAT)"

# Проверить Mean Reversion сигналы
docker logs bybit_bot --tail 100 | grep "Mean Reversion"

# Проверить CHOP индекс
docker logs bybit_bot --tail 100 | grep "CHOP:"
```

## Deployment

### Файлы
- `config.py` - новые параметры
- `core/ai_brain_local.py` - Hybrid Strategy Selector

### Команды
```bash
# 1. Копируем файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересобираем (config.py в раннем слое - нужен --no-cache)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"

# 3. Проверяем логи
ssh root@88.210.10.145 "docker logs -f bybit_bot"
```

## Тестирование

### Тест 1: Проверка режима TREND
```bash
# Ожидаем: "🚀 Mode: TREND (ML Follower)"
# Когда: CHOP < 60
```

### Тест 2: Проверка режима FLAT
```bash
# Ожидаем: "🔄 Mode: FLAT (Mean Reversion)"
# Когда: CHOP >= 60
```

### Тест 3: Mean Reversion BUY
```bash
# Ожидаем: "✅ Mean Reversion Signal: BUY"
# Когда: CHOP >= 60, RSI < 30, BTC > -0.5%
```

### Тест 4: Mean Reversion SELL
```bash
# Ожидаем: "✅ Mean Reversion Signal: SELL"
# Когда: CHOP >= 60, RSI > 70, BTC < +0.5%
```

## Риски и Ограничения

### Риск 1: Ложные сигналы во флэте
**Митигация:** 
- Минимальная confidence 65%
- BTC Safety Check
- Strategic Brain Veto

### Риск 2: Переключение стратегий
**Митигация:**
- CHOP рассчитывается на 14 свечах (стабильно)
- Нет частых переключений

### Риск 3: Mean Reversion в сильном тренде
**Митигация:**
- CHOP < 60 → автоматически Trend Following
- Mean Reversion работает ТОЛЬКО при CHOP >= 60

## Выводы

✅ **Hybrid Strategy Selector** решает проблему простоя во флэте  
✅ **Mean Reversion** эффективен для RSI экстремумов  
✅ **Безопасность:** Strategic Brain + BTC Filter работают в обоих режимах  
✅ **Ожидаемый результат:** +50-100% активности, меньше простоя  

---

**Дата:** 2025-12-14  
**Версия:** v1.0  
**Статус:** Готов к деплою
