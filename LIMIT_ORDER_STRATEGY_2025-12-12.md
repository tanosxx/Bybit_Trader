# LIMIT ORDER STRATEGY - Maker Fee Optimization
**Дата:** 12 декабря 2025  
**Версия:** FuturesExecutor v7.0  
**Статус:** ✅ Готово к деплою

---

## 🎯 ЦЕЛЬ

Снизить торговые комиссии с **0.055% (Taker)** до **0.02% (Maker)** путём перехода на Limit ордера.

**Экономия:** 0.035% на каждый вход = **63% снижение комиссий!**

---

## 📊 СРАВНЕНИЕ КОМИССИЙ

### Текущая стратегия (Market Orders - Taker)
- **Entry:** 0.055% × Entry Value
- **Exit:** 0.055% × Exit Value
- **Total:** ~0.11% на круг

**Пример:** Сделка $100
- Entry fee: $0.055
- Exit fee: $0.055
- **Total: $0.11**

### Новая стратегия (Limit Orders - Maker)
- **Entry:** 0.02% × Entry Value (Maker)
- **Exit:** 0.055% × Exit Value (Taker - закрытие всегда Market)
- **Total:** ~0.075% на круг

**Пример:** Сделка $100
- Entry fee: $0.02
- Exit fee: $0.055
- **Total: $0.075**

**Экономия:** $0.035 на сделку = **31.8% снижение общих комиссий!**

---

## 🔧 ТЕХНИЧЕСКИЕ ИЗМЕНЕНИЯ

### 1. Конфигурация (`config.py`)

Добавлены новые параметры:

```python
# ========== LIMIT ORDER SETTINGS (Maker Strategy) ==========
order_type: Literal['LIMIT', 'MARKET'] = 'LIMIT'  # Тип ордера по умолчанию
order_timeout_seconds: int = 60  # Таймаут для Limit ордеров
limit_order_fallback_to_market: bool = True  # Fallback на Market
maker_fee_rate: float = 0.0002  # 0.02% Maker fee
taker_fee_rate: float = 0.00055  # 0.055% Taker fee
```

### 2. Executor (`futures_executor.py`)

#### Новые методы:

**A. `cancel_all_active_orders(symbol)`**
- Очищает "зомби-ордера" перед новым сигналом
- Предотвращает конфликты и дублирование

**B. `get_best_prices(symbol)`**
- Получает Best Bid/Ask из стакана (orderbook)
- Используется для умного ценообразования

**C. `place_atomic_order()` - ОБНОВЛЁН**
- **Шаг А:** Очистка зомби-ордеров
- **Шаг Б:** Определение цены:
  - **LIMIT BUY:** Best Bid (становимся в очередь покупателей)
  - **LIMIT SELL:** Best Ask (становимся в очередь продавцов)
- **Шаг В:** Размещение ордера с `timeInForce: GTC`
- **Шаг Г:** Мониторинг исполнения (60s timeout)
- **Шаг Д:** Fallback на Market при таймауте

**D. `_wait_for_order_fill(symbol, order_id, timeout)`**
- Ждёт исполнения Limit ордера
- Проверяет статус каждые 2 секунды
- Возвращает `True` если исполнен, `False` если таймаут

**E. `_cancel_order(symbol, order_id)`**
- Отменяет зависший ордер

#### Обновлённые методы:

**F. `_save_trade()` - ОБНОВЛЁН**
- Принимает `order_type` и `limit_price`
- Рассчитывает правильную комиссию (Maker vs Taker)
- Сохраняет тип ордера в `extra_data`

**G. `_close_position()` - ОБНОВЛЁН**
- Использует правильную комиссию из `extra_data.order_type`
- Entry: Maker (0.02%) или Taker (0.055%)
- Exit: всегда Taker (0.055%)

---

## 🎮 ЛОГИКА РАБОТЫ

### Сценарий 1: Успешный Limit Order

```
1. Сигнал: BUY BTCUSDT @ $95,000
2. Очистка: cancel_all_active_orders("BTCUSDT")
3. Стакан: Best Bid = $94,999.5, Best Ask = $95,000.5
4. Limit Order: BUY @ $94,999.5 (Best Bid)
5. Ожидание: 60 секунд
6. Статус: Filled ✅
7. Результат: Вход по $94,999.5 (Maker fee 0.02%)
```

**Экономия:** $0.035 на сделку $100

### Сценарий 2: Таймаут → Fallback на Market

```
1. Сигнал: SELL ETHUSDT @ $3,500
2. Очистка: cancel_all_active_orders("ETHUSDT")
3. Стакан: Best Ask = $3,500.2
4. Limit Order: SELL @ $3,500.2 (Best Ask)
5. Ожидание: 60 секунд
6. Статус: Not Filled ⏰
7. Отмена: cancel_order()
8. Fallback: MARKET SELL @ $3,499.8
9. Результат: Вход по Market (Taker fee 0.055%)
```

**Результат:** Не потеряли сигнал, но заплатили Taker fee

### Сценарий 3: Стакан недоступен → Fallback

```
1. Сигнал: BUY SOLUSDT @ $180
2. Очистка: cancel_all_active_orders("SOLUSDT")
3. Стакан: ❌ Ошибка API
4. Fallback: MARKET BUY @ $180.05
5. Результат: Вход по Market (Taker fee 0.055%)
```

**Результат:** Безопасность важнее экономии

---

## 📈 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### Текущая производительность (Market Orders)
- **Сделок в день:** 5-15
- **Средняя комиссия:** $0.11 на сделку $100
- **Комиссии в день:** $0.55 - $1.65

### Прогноз с Limit Orders (70% Maker, 30% Taker)
- **Maker сделок:** 3-10 (70%)
- **Taker сделок:** 2-5 (30% - таймауты/фоллбэки)
- **Средняя комиссия:** $0.08 на сделку $100
- **Комиссии в день:** $0.40 - $1.20

**Экономия:** $0.15 - $0.45 в день = **$4.50 - $13.50 в месяц**

При балансе $379 это **1.2% - 3.6% дополнительной прибыли в месяц!**

---

## ⚠️ РИСКИ И МИТИГАЦИЯ

### Риск 1: Limit ордер не исполняется
**Митигация:**
- Таймаут 60 секунд
- Автоматический fallback на Market
- Не теряем сигнал

### Риск 2: Проскальзывание при fallback
**Митигация:**
- Fallback происходит быстро (после 60s)
- Рынок обычно не успевает сильно измениться
- Лучше войти по Taker, чем пропустить сигнал

### Риск 3: API ошибки (стакан недоступен)
**Митигация:**
- Graceful degradation на Market
- Логирование всех ошибок
- Система продолжает работать

### Риск 4: Зомби-ордера
**Митигация:**
- `cancel_all_active_orders()` перед каждым новым сигналом
- Очистка старых ордеров
- Нет конфликтов

---

## 🚀 DEPLOYMENT PLAN

### Шаг 1: Копирование файлов
```bash
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/
```

### Шаг 2: Пересборка контейнера
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache bot"
```

### Шаг 3: Перезапуск
```bash
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Шаг 4: Проверка логов
```bash
ssh root@88.210.10.145 "docker logs -f bybit_bot"
```

**Ожидаемый вывод:**
```
🚀 FuturesExecutor v7.0 initialized (MAKER STRATEGY):
   💎 Order Type: LIMIT (Maker: 0.02%, Taker: 0.055%)
   ⏰ Limit Timeout: 60s
   🔄 Fallback to Market: ON
```

### Шаг 5: Мониторинг первых сделок
- Проверить логи: `LIMIT order filled` или `fallback to MARKET`
- Проверить комиссии в БД: `fee_entry` должен быть ~0.02%
- Проверить Dashboard: новые сделки с типом `LIMIT`

---

## 📊 МЕТРИКИ ДЛЯ ОТСЛЕЖИВАНИЯ

### KPI 1: Maker Fill Rate
**Цель:** > 70%  
**Формула:** (Limit Orders Filled / Total Orders) × 100%

### KPI 2: Средняя комиссия входа
**Цель:** < 0.03%  
**Формула:** AVG(fee_entry / entry_value) × 100%

### KPI 3: Экономия комиссий
**Цель:** > $0.03 на сделку  
**Формула:** (Old Fee - New Fee) per trade

### KPI 4: Таймауты
**Цель:** < 30%  
**Формула:** (Timeouts / Total Limit Orders) × 100%

---

## 🔍 МОНИТОРИНГ

### SQL запросы для анализа:

**1. Maker Fill Rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE extra_data->>'order_type' = 'LIMIT') as limit_orders,
    COUNT(*) as total_orders,
    ROUND(COUNT(*) FILTER (WHERE extra_data->>'order_type' = 'LIMIT')::numeric / COUNT(*) * 100, 1) as maker_fill_rate
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours';
```

**2. Средняя комиссия:**
```sql
SELECT 
    extra_data->>'order_type' as order_type,
    COUNT(*) as count,
    ROUND(AVG(fee_entry)::numeric, 4) as avg_entry_fee,
    ROUND(AVG(fee_entry / (entry_price * quantity) * 100)::numeric, 3) as avg_fee_pct
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours'
GROUP BY extra_data->>'order_type';
```

**3. Экономия:**
```sql
SELECT 
    SUM(CASE 
        WHEN extra_data->>'order_type' = 'LIMIT' 
        THEN (entry_price * quantity * 0.00055) - fee_entry 
        ELSE 0 
    END) as total_savings
FROM trades 
WHERE status = 'CLOSED' 
  AND market_type = 'futures'
  AND entry_time > NOW() - INTERVAL '24 hours';
```

---

## 🎓 ВЫВОДЫ

### Преимущества:
✅ **63% снижение комиссий входа** (0.055% → 0.02%)  
✅ **31.8% снижение общих комиссий** на круг  
✅ **Безопасный fallback** на Market при таймауте  
✅ **Graceful degradation** при ошибках API  
✅ **Очистка зомби-ордеров** перед каждым сигналом  
✅ **Правильный учёт комиссий** в БД и балансе  

### Недостатки:
⚠️ **Задержка входа** до 60 секунд (но это норма для Maker)  
⚠️ **30% сделок** могут быть Taker (fallback)  
⚠️ **Сложность кода** увеличилась  

### Рекомендации:
1. **Мониторить Maker Fill Rate** первые 24 часа
2. **Настроить таймаут** если > 30% fallback (можно увеличить до 90s)
3. **Анализировать экономию** еженедельно
4. **Рассмотреть Post-Only** ордера для 100% Maker (но риск пропуска сигналов)

---

## 📝 CHANGELOG

### v7.0 (12 декабря 2025)
- ✅ Добавлены Limit Orders с умным ценообразованием
- ✅ Реализован мониторинг таймаутов (60s)
- ✅ Добавлен fallback на Market
- ✅ Очистка зомби-ордеров
- ✅ Динамический расчёт комиссий (Maker vs Taker)
- ✅ Обновлена документация

---

**Автор:** Kiro AI  
**Дата:** 12 декабря 2025, 01:15 UTC  
**Статус:** ✅ Готово к деплою
