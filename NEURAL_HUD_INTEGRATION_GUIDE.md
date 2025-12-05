# Neural HUD - Integration Guide for Developers

## 🎯 Как интегрировать GlobalBrainState в свой модуль

Если вы разрабатываете новый AI модуль или обновляете существующий, следуйте этому гайду для интеграции с Neural HUD.

## 📦 Импорт

```python
# В начале вашего модуля
try:
    from core.state import get_global_brain_state
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False
    print("⚠️ GlobalBrainState not available")
```

**Важно:** Используйте `try/except` для graceful degradation. Если `state.py` отсутствует, модуль должен работать без обновления HUD.

## 🔄 Обновление данных

### 1. Strategic Brain (Market Regime)

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_strategic(
            regime="BULL_RUSH",  # или BEAR_CRASH, SIDEWAYS, UNCERTAIN
            reason="Strong uptrend detected across major pairs"
        )
    except Exception as e:
        pass  # Не критично, продолжаем работу
```

### 2. News Brain (Sentiment)

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_news(
            sentiment=0.75,  # -1.0 to +1.0
            headline="Bitcoin breaks $50k resistance",
            count=12  # количество новостей
        )
    except Exception as e:
        pass
```

### 3. Market Data (CHOP, RSI, Price)

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_market_data(
            symbol="BTCUSDT",
            chop=45.2,      # Choppiness Index (опционально)
            rsi=58.3,       # RSI (опционально)
            price=42150.50  # Текущая цена (опционально)
        )
    except Exception as e:
        pass
```

**Примечание:** Все параметры кроме `symbol` опциональны. Передавайте только те, которые у вас есть.

### 4. ML Predictions

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_ml_prediction(
            symbol="BTCUSDT",
            decision="BUY",  # или "SELL", "HOLD"
            confidence=0.68,  # 0.0 to 1.0
            change_pct=1.2    # Ожидаемое изменение в %
        )
    except Exception as e:
        pass
```

### 5. Gatekeeper Status

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        
        # Если сигнал прошёл
        state.update_gatekeeper(symbol="BTCUSDT", status="PASS")
        
        # Если заблокирован
        state.update_gatekeeper(symbol="ETHUSDT", status="BLOCK: CHOP 65.3")
    except Exception as e:
        pass
```

### 6. Active Positions

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_positions(
            positions=["BTCUSDT", "ETHUSDT"]  # Список символов с открытыми позициями
        )
    except Exception as e:
        pass
```

### 7. System Status

```python
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_system_status(
            running=True,  # Бот активен
            scan_time=datetime.now()  # Время последнего сканирования
        )
    except Exception as e:
        pass
```

## 📍 Где размещать обновления

### Правило 1: После получения данных
Обновляйте state **сразу после** получения/расчёта данных, но **до** принятия решения.

```python
# ✅ ПРАВИЛЬНО
chop = calculate_chop(klines)
state.update_market_data(symbol, chop=chop)

if chop > 60:
    return "SKIP"

# ❌ НЕПРАВИЛЬНО
if chop > 60:
    return "SKIP"

state.update_market_data(symbol, chop=chop)  # Не выполнится при SKIP!
```

### Правило 2: В критических точках
Обновляйте state в ключевых точках принятия решений:

```python
async def decide_trade(self, market_data):
    # 1. Начало анализа
    state.update_system_status(running=True, scan_time=datetime.now())
    
    # 2. После получения новостей
    news_data = await self.get_news()
    state.update_news(sentiment=news_data['score'], ...)
    
    # 3. После ML предсказания
    ml_result = await self.ml_predict()
    state.update_ml_prediction(symbol, ml_result['decision'], ...)
    
    # 4. После Gatekeeper проверки
    if not gatekeeper_passed:
        state.update_gatekeeper(symbol, "BLOCK: Reason")
        return "SKIP"
    
    state.update_gatekeeper(symbol, "PASS")
    
    # 5. Финальное решение
    return decision
```

### Правило 3: Не блокируйте основной поток
Всегда используйте `try/except` и не ждите результата:

```python
# ✅ ПРАВИЛЬНО - быстро и безопасно
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_market_data(symbol, chop=chop)
    except:
        pass  # Игнорируем ошибки

# ❌ НЕПРАВИЛЬНО - может упасть весь модуль
state = get_global_brain_state()
state.update_market_data(symbol, chop=chop)
```

## 🧪 Тестирование интеграции

### 1. Проверка обновления данных

```python
# В вашем тестовом скрипте
from core.state import get_global_brain_state

state = get_global_brain_state()

# Обновляем данные
state.update_market_data("BTCUSDT", chop=45.2, rsi=58.3, price=42150.50)

# Проверяем
data = state.to_dict()
print(data['market']['chop_index']['BTCUSDT'])  # Должно быть 45.2
```

### 2. Проверка через API

```bash
# Запустите бот и проверьте API
curl http://localhost:8585/api/brain_live | jq .

# Должны увидеть обновлённые данные
```

### 3. Проверка в Neural HUD

1. Откройте http://localhost:8585/brain
2. Запустите бот
3. Наблюдайте обновления в реальном времени

## 🎨 Добавление новых полей в GlobalBrainState

Если вам нужны дополнительные поля:

### 1. Обновите `core/state.py`

```python
class GlobalBrainState:
    def __init__(self):
        # ... существующие поля ...
        
        # Ваше новое поле
        self.my_custom_data: Dict[str, float] = {}
    
    def update_my_custom_data(self, symbol: str, value: float):
        """Обновить кастомные данные"""
        with self._lock:
            self.my_custom_data[symbol] = value
    
    def to_dict(self) -> Dict:
        return {
            # ... существующие поля ...
            'my_custom': self.my_custom_data
        }
```

### 2. Обновите `web/templates/brain.html`

```javascript
function updateSymbols(data) {
    const myCustomData = data.my_custom || {};
    
    SYMBOLS.forEach(symbol => {
        const customValue = myCustomData[symbol] || 0;
        // Отобразите в UI
    });
}
```

## 📊 Best Practices

### 1. Минимизируйте overhead
- Обновляйте только изменившиеся данные
- Не обновляйте на каждой итерации цикла
- Группируйте обновления

```python
# ✅ ПРАВИЛЬНО - одно обновление
state.update_market_data(symbol, chop=chop, rsi=rsi, price=price)

# ❌ НЕПРАВИЛЬНО - три обновления
state.update_market_data(symbol, chop=chop)
state.update_market_data(symbol, rsi=rsi)
state.update_market_data(symbol, price=price)
```

### 2. Используйте осмысленные сообщения

```python
# ✅ ПРАВИЛЬНО - понятно что произошло
state.update_gatekeeper(symbol, "BLOCK: CHOP 65.3 > 60 (choppy market)")

# ❌ НЕПРАВИЛЬНО - непонятно
state.update_gatekeeper(symbol, "BLOCK")
```

### 3. Обновляйте timestamp автоматически
GlobalBrainState автоматически добавляет timestamp при обновлении. Не нужно передавать его вручную.

### 4. Thread-safe по умолчанию
GlobalBrainState использует `threading.Lock` внутри. Можно безопасно обновлять из разных потоков.

## 🔍 Debugging

### Проверка что данные обновляются

```python
# В вашем модуле добавьте логирование
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_market_data(symbol, chop=chop)
        print(f"✅ GlobalBrainState updated: {symbol} CHOP={chop}")
    except Exception as e:
        print(f"⚠️ Failed to update GlobalBrainState: {e}")
```

### Проверка содержимого state

```python
from core.state import get_global_brain_state

state = get_global_brain_state()
print(state.to_json())  # Красивый JSON вывод
```

## 📚 Примеры из существующих модулей

### Strategic Brain

```python
# core/strategic_brain.py, строка ~95
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_strategic(detected_regime, regime_raw[:200])
    except Exception as e:
        print(f"⚠️ Failed to update GlobalBrainState: {e}")
```

### AI Brain Local

```python
# core/ai_brain_local.py, строка ~520
if STATE_AVAILABLE:
    try:
        state = get_global_brain_state()
        state.update_market_data(symbol, chop=chop)
    except:
        pass
```

## 🚀 Quick Start Checklist

- [ ] Импортировал `get_global_brain_state` с `try/except`
- [ ] Добавил проверку `if STATE_AVAILABLE:`
- [ ] Обернул обновления в `try/except`
- [ ] Обновляю данные после их получения
- [ ] Использую осмысленные сообщения для Gatekeeper
- [ ] Протестировал через `/api/brain_live`
- [ ] Проверил в Neural HUD UI

---

**Вопросы?** Проверьте существующие интеграции в `core/strategic_brain.py` и `core/ai_brain_local.py`.
