# 🚀 Деплой: Учёт виртуального баланса с комиссиями

**Дата**: 2 декабря 2025  
**Задача**: Добавить пересчёт виртуального баланса с учётом комиссий Bybit

---

## 📋 Что изменилось

### 1. Новый модуль `balance_tracker.py`
- Рассчитывает текущий баланс: `$100 + realized_pnl - total_fees`
- Учитывает комиссии Bybit (0.055% taker fee)
- История баланса по сделкам

### 2. FuturesExecutor обновлён
- Записывает `fee_entry` при открытии (0.055% от стоимости)
- Записывает `fee_exit` при закрытии (0.055% от стоимости)
- Обновляет баланс с учётом net PnL

### 3. Dashboard обновлён
- Отображает: Realized PnL, Комиссии, Net PnL
- Текущий баланс = $100 + Net PnL
- 5 метрик вместо 4

---

## 🔧 Команды для деплоя

### Шаг 1: Копирование файлов на сервер

```bash
# 1. Новый файл balance_tracker.py
scp ./Bybit_Trader/database/balance_tracker.py root@88.210.10.145:/root/Bybit_Trader/database/

# 2. Обновлённый futures_executor.py
scp ./Bybit_Trader/core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/

# 3. Обновлённый app.py (dashboard API)
scp ./Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/

# 4. Обновлённый dashboard_futures.html
scp ./Bybit_Trader/web/templates/dashboard_futures.html root@88.210.10.145:/root/Bybit_Trader/web/templates/

# 5. Memory Bank (опционально)
scp ./Bybit_Trader/memory-bank/activeContext.md root@88.210.10.145:/root/Bybit_Trader/memory-bank/
```

### Шаг 2: Перезапуск контейнеров

```bash
# SSH на сервер
ssh root@88.210.10.145

# Перейти в директорию
cd /root/Bybit_Trader

# Перезапустить контейнеры
docker-compose down
docker-compose up -d --build

# Проверить логи бота
docker logs -f bybit_bot

# Проверить логи дашборда
docker logs -f bybit_dashboard
```

### Шаг 3: Проверка

```bash
# 1. Проверить что бот запустился
docker ps | grep bybit

# 2. Открыть дашборд
# http://88.210.10.145:8585/futures

# 3. Проверить что отображаются:
#    - Текущий баланс (должен быть ~$100 + PnL - комиссии)
#    - Realized PnL
#    - Комиссии (отрицательное число)
#    - Net PnL (PnL - комиссии)
#    - Изменение в %
```

---

## ✅ Ожидаемый результат

### До изменений
```
Текущий баланс: $100.00 (не меняется)
Realized PnL: +$8.50
Комиссии: не отображаются
```

### После изменений
```
Текущий баланс: $105.23 (пересчитывается!)
Realized PnL: +$8.50
Комиссии: -$3.27
Net PnL: +$5.23
Изменение: +5.23%
```

---

## 📊 Формулы

```python
# Комиссия входа
entry_fee = entry_price * quantity * 0.055%

# Комиссия выхода
exit_fee = exit_price * quantity * 0.055%

# Net PnL
net_pnl = realized_pnl - (entry_fee + exit_fee)

# Текущий баланс
current_balance = initial_balance + net_pnl
```

---

## 🐛 Возможные проблемы

### 1. Баланс не обновляется
**Причина**: Старые сделки без комиссий в БД  
**Решение**: Комиссии рассчитываются автоматически если `fee_entry = 0`

### 2. Комиссии слишком большие
**Причина**: Неправильный расчёт (умножение на leverage)  
**Решение**: Комиссии считаются от стоимости позиции БЕЗ плеча

### 3. Dashboard не обновляется
**Причина**: Кэш браузера  
**Решение**: Ctrl+F5 для жёсткой перезагрузки

---

## 📝 Примечания

- Комиссии записываются в поля `fee_entry` и `fee_exit` в таблице `trades`
- Funding rate комиссии пока не учитываются (TODO)
- Виртуальный баланс обновляется при каждом закрытии позиции
- Dashboard обновляется каждые 5 секунд

---

## 🎯 Следующие шаги

1. Деплой на сервер
2. Мониторинг 24 часа
3. Проверка корректности расчётов
4. Добавить учёт funding rate (если нужно)
