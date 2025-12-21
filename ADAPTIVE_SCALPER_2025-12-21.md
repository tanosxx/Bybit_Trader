# Adaptive Scalper v7.1 - Адаптивная торговля во флэте

**Дата:** 21 декабря 2025  
**Версия:** v7.1  
**Статус:** ✅ Deployed

---

## 🎯 Проблема

На дашборде видим `Strategy: FLAT`, и список последних сделок состоит на 100% из `ZOMBIE TRADE (TTL EXPIRED)`.

**Причина:** На вялом рынке (CHOP > 50) цена не успевает дойти до стандартного Take Profit за 180 минут. Бот держит позицию 3 часа и закрывает по таймеру (часто в минус).

**Пример:**
- Базовый TP: +3% (слишком далеко для флэта)
- Базовый SL: -2%
- TTL: 180 минут
- Результат: Цена двигается ±0.5%, не достигает TP, закрывается по таймеру

---

## 💡 Решение: Adaptive Scalper

Бот теперь **адаптируется к режиму рынка**:

### FLAT режим (CHOP > 50):
- ✅ **TP сжимается на 50%**: 3% → 1.5%
- ✅ **SL сжимается на 30%**: 2% → 1.4%
- ✅ **TTL сокращается вдвое**: 180 → 90 минут
- 🎯 **Цель:** Быстрые сделки (скальпинг), закрытие по TP вместо таймера

### TREND режим (CHOP ≤ 50):
- 📈 **Базовые значения**: TP 3%, SL 2%, TTL 180 минут
- 🎯 **Цель:** Ловить большие движения

---

## 🔧 Технические изменения

### 1. `futures_executor.py` - Адаптивная логика

**Новый метод:**
```python
def adapt_to_market_regime(self, chop: float, market_mode: str = None) -> Dict:
    """
    Адаптировать TP/SL/TTL к режиму рынка
    
    FLAT (CHOP > 50):
    - TP × 0.5 (3% → 1.5%)
    - SL × 0.7 (2% → 1.4%)
    - TTL ÷ 2 (180 → 90 минут)
    
    TREND (CHOP ≤ 50):
    - Базовые значения
    """
```

**Изменения в `_open_long` и `_open_short`:**
```python
# 0.5. ADAPT TO MARKET REGIME (v7.1)
chop = signal.extra_data.get('chop') if signal.extra_data else None
market_mode = signal.extra_data.get('market_mode') if signal.extra_data else None

adaptive_params = self.adapt_to_market_regime(chop, market_mode)
ttl_minutes = adaptive_params['ttl_minutes']

# Сохраняем TTL в extra_data
extra_data={
    'ttl_minutes': ttl_minutes,  # Адаптивный TTL
    'market_mode': adaptive_params['mode'],
    'chop': chop
}
```

**Изменения в `monitor_emergency_risks`:**
```python
# Получаем адаптивный TTL из extra_data
ttl_limit = settings.max_hold_time_minutes  # Базовый (180)

if trade.extra_data and 'ttl_minutes' in trade.extra_data:
    ttl_limit = trade.extra_data['ttl_minutes']  # Адаптивный (90 или 180)
    market_mode = trade.extra_data.get('market_mode', 'UNKNOWN')
    print(f"   🧟 Zombie Check ({market_mode}): Duration={hold_time_minutes:.1f}m / Adaptive Limit={ttl_limit}m")
```

### 2. `hybrid_loop.py` - Передача CHOP в сигнал

**Изменения в `execute_hybrid`:**
```python
# Извлекаем CHOP и market_mode из gatekeeper
gatekeeper = ai.get('gatekeeper', {}) if isinstance(ai, dict) else {}
chop = gatekeeper.get('chop')

# Определяем market_mode по CHOP
market_mode = None
if chop is not None:
    market_mode = 'FLAT' if chop > 50.0 else 'TREND'

# Собираем extra_data
extra_data = {}
if ml_features:
    extra_data['ml_features'] = ml_features
if chop is not None:
    extra_data['chop'] = chop
if market_mode:
    extra_data['market_mode'] = market_mode

futures_signal = TradeSignal(
    action=action_str,
    confidence=futures_decision.trading_confidence / 100,
    risk_score=risk_score,
    reasoning=futures_decision.reasoning,
    symbol=symbol,
    price=price,
    extra_data=extra_data if extra_data else None
)
```

---

## 📊 Ожидаемые результаты

### До (v7.0):
```
Strategy: FLAT
Last Trades:
- SOLUSDT: ZOMBIE TRADE (TTL EXPIRED) - 180 min
- SOLUSDT: ZOMBIE TRADE (TTL EXPIRED) - 180 min
- SOLUSDT: ZOMBIE TRADE (TTL EXPIRED) - 180 min
```

### После (v7.1):
```
Strategy: FLAT (Adaptive Scalper)
Last Trades:
- SOLUSDT: Take Profit hit: $126.12 (+1.5%) - 45 min
- SOLUSDT: Take Profit hit: $125.88 (+1.5%) - 32 min
- SOLUSDT: ZOMBIE TRADE (TTL EXPIRED) - 90 min (редко)
```

**Метрики:**
- ✅ Закрытие по TP вместо таймера: 70%+ (цель)
- ✅ Среднее время сделки во флэте: 30-60 минут (вместо 180)
- ✅ Win Rate во флэте: 40%+ (вместо 20%)

---

## 🚀 Deployment

```bash
# 1. Копирование файлов
scp Bybit_Trader/core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Пересборка
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# 3. Удаление старого контейнера
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose rm -f bot"

# 4. Запуск
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"

# 5. Проверка логов
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100"
```

**Статус:** ✅ Deployed успешно

---

## 📝 Логи запуска

```
🚀 FuturesExecutor v7.1 initialized (ADAPTIVE SCALPER):
   💰 Virtual Balance: $100.0
   📊 Base Leverage: 3x (dynamic 2-7x)
   🎯 Risk per Trade: 5.0%
   🛡️ Base SL: 2.0% | Base TP: 3.0%
   🔄 ADAPTIVE MODE: FLAT → TP×0.5, SL×0.7, TTL÷2
   📈 Trailing Stop: ON
   💸 Funding Filter: ON
   🚫 Max Symbols: 1
   🚫 Max Orders/Symbol: 15
   🚫 Max Total Orders: 80
   🎯 Min Confidence: 60.0%
   ⚠️ ISOLATED margin ENFORCED
   💎 Order Type: LIMIT (Maker: 0.02%, Taker: 0.055%)
   ⏰ Limit Timeout: 60s
   🔄 Fallback to Market: ON
```

---

## 🎯 Следующие шаги

1. **Мониторинг:** Наблюдать за сделками в течение 24 часов
2. **Анализ:** Проверить % закрытий по TP vs TTL
3. **Оптимизация:** Если нужно, подкрутить множители (0.5 → 0.6 для TP)

---

## 📚 Связанные документы

- `LIMIT_ORDER_STRATEGY_2025-12-12.md` - Maker Strategy v7.0
- `SAFE_MODE_DEPLOYED_2025-12-16.md` - Safe Mode configuration
- `config.py` - Базовые настройки TP/SL/TTL

---

**Автор:** AI Assistant  
**Дата:** 2025-12-21  
**Версия:** v7.1 (Adaptive Scalper)
