# Strategic Compliance Spam Fix

**Date:** January 6, 2026  
**Status:** ✅ FIXED  
**Issue:** Strategic Compliance отправлял повторяющиеся Telegram уведомления

## Проблема

Strategic Compliance отправлял уведомление при каждом цикле (каждые 30 секунд), даже если позиции уже были закрыты:

```
🚨 STRATEGIC COMPLIANCE
🚀 Regime: BULL_RUSH
📝 Bull market - SHORT positions closed
🔒 Closed: 1 position(s)
💡 Reason: Non-compliant with current strategy
```

**Причина:** Код не отслеживал уже закрытые позиции и отправлял уведомление каждый раз когда находил несоответствующие позиции в списке.

## Решение

### 1. Обновлён `strategic_compliance.py`

**Добавлено отслеживание:**
- `last_closed_positions` - set закрытых позиций (по ключу `symbol_side`)
- `notification_sent_for_regime` - режим для которого уже отправили уведомление

**Изменена сигнатура `enforce_strategic_compliance()`:**
```python
# Было:
def enforce_strategic_compliance(...) -> List[Dict]:

# Стало:
def enforce_strategic_compliance(...) -> tuple[List[Dict], bool]:
    # Возвращает (positions_to_close, should_notify)
```

**Логика уведомлений:**
- Уведомление отправляется только при изменении режима
- ИЛИ при появлении новых несоответствующих позиций
- Закрытые позиции запоминаются и не обрабатываются повторно

### 2. Обновлён `hybrid_loop.py`

**Добавлен счётчик успешно закрытых позиций:**
```python
successfully_closed = 0
for pos_info in positions_to_close:
    result = await self.futures_executor.close_position(...)
    if result.success:
        successfully_closed += 1

# Уведомление ТОЛЬКО если реально закрыли позиции
if successfully_closed > 0:
    await self.telegram.notify_strategic_compliance(...)
```

**Преимущества:**
- Уведомление отправляется только при реальном закрытии позиций
- Не спамит если позиции уже закрыты
- Не спамит если закрытие не удалось

## Изменения в коде

### `strategic_compliance.py`

**Добавлено в `__init__`:**
```python
self.last_closed_positions = set()  # Отслеживаем закрытые позиции
self.notification_sent_for_regime = None  # Режим для которого отправили уведомление
```

**Обновлён `enforce_strategic_compliance()`:**
- Проверяет `pos_key not in self.last_closed_positions` перед добавлением в `positions_to_close`
- Возвращает tuple `(positions_to_close, should_notify)`
- `should_notify = True` только при изменении режима или новых позициях
- Запоминает закрытые позиции в `self.last_closed_positions`

**Обновлён `get_compliance_status()`:**
- Распаковывает tuple: `positions_to_close, _ = self.enforce_strategic_compliance(...)`

### `hybrid_loop.py`

**Добавлен счётчик `successfully_closed`:**
- Инкрементируется только при `result.success`
- Уведомление отправляется только если `successfully_closed > 0`

## Тестирование

**До фикса:**
- Уведомления каждые 30 секунд (при каждом цикле)
- Спам в Telegram

**После фикса:**
- Уведомление только при реальном закрытии позиций
- Уведомление только один раз для каждого режима
- Нет спама

## Deployment

```bash
# 1. Копирование файлов
scp Bybit_Trader/core/strategic_compliance.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Копирование в контейнер
ssh root@88.210.10.145 "docker cp /root/Bybit_Trader/core/strategic_compliance.py bybit_bot:/app/core/"
ssh root@88.210.10.145 "docker cp /root/Bybit_Trader/core/hybrid_loop.py bybit_bot:/app/core/"

# 3. Перезапуск
ssh root@88.210.10.145 "docker restart bybit_bot"

# 4. Проверка логов
ssh root@88.210.10.145 "docker logs bybit_bot --tail 50"
```

## Результат

✅ Strategic Compliance больше не спамит уведомлениями  
✅ Уведомление отправляется только при реальном закрытии позиций  
✅ Уведомление отправляется только один раз для каждого режима  
✅ Бот работает корректно

---

**Deployment completed:** January 6, 2026, 22:10 UTC  
**Status:** ✅ SUCCESS
