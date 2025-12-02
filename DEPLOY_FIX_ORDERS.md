# 🔧 Деплой исправления ошибки ордеров

## Проблема
Ордера падали с ошибкой:
```
❌ Order FAILED: TakeProfit:86810000000 set for Buy position should be higher than base_price:87080000000
```

Цены SL/TP передавались как строки и Bybit API неправильно их парсил.

## Решение
Изменен `core/executors/futures_executor.py`:
- SL/TP теперь передаются как `float`, а не `str`
- Bybit API корректно обрабатывает числовые значения

## Шаги деплоя

### 1. Остановить торговлю (на сервере)
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader

# Запустить скрипт остановки
docker exec -it bybit_bot python scripts/stop_trading.py
```

### 2. Скопировать исправленный файл на сервер (локально)
```bash
scp ./Bybit_Trader/core/executors/futures_executor.py root@88.210.10.145:/root/Bybit_Trader/core/executors/
scp ./Bybit_Trader/scripts/stop_trading.py root@88.210.10.145:/root/Bybit_Trader/scripts/
scp ./Bybit_Trader/scripts/check_and_transfer_balance.py root@88.210.10.145:/root/Bybit_Trader/scripts/
```

### 3. Проверить балансы (на сервере)
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader

# Проверить балансы Demo счёта
docker exec -it bybit_bot python scripts/check_and_transfer_balance.py
```

### 4. Обновить конфиг (опционально)
Если хочешь изменить стартовый баланс на $50 или $100:

```bash
# Редактировать config.py на сервере
nano /root/Bybit_Trader/config.py

# Найти и изменить:
futures_virtual_balance: float = 50.0  # Было 500.0
```

### 5. Пересобрать и запустить контейнеры (на сервере)
```bash
cd /root/Bybit_Trader

# Остановить контейнеры
docker-compose down

# Пересобрать с новым кодом
docker-compose up -d --build

# Проверить логи
docker logs -f bybit_bot
```

### 6. Мониторинг (на сервере)
```bash
# Смотреть логи в реальном времени
docker logs -f bybit_bot

# Проверить что ордера проходят успешно
# Должны видеть:
# ✅ Order placed: <order_id>
# ✅ [FUTURES] LONG BTCUSDT: 0.002 @ $87000 (2x)

# Проверить позиции в БД
docker exec -it bybit_db psql -U bybit_user -d bybit_trader -c "SELECT symbol, side, entry_price, quantity, status FROM trades WHERE status='OPEN' ORDER BY entry_time DESC LIMIT 10;"
```

### 7. Полная диагностика (на сервере)
```bash
# Запустить полную проверку системы
docker exec -it bybit_bot python scripts/system_diagnostics.py
```

## Ожидаемый результат

После деплоя:
- ✅ Ордера проходят успешно
- ✅ Позиции открываются с SL/TP
- ✅ Нет ошибок "Order FAILED"
- ✅ Бот активно торгует

## Проверка успешности

Смотрим логи и ищем:
```
✅ Order placed: a6920ed3-3174-4db5-b9f2-541bcdba4c16
✅ [FUTURES] LONG BNBUSDT: 0.19 @ $827.50 (2x)
   🛡️ SL=$810.9 | TP=$852.3
```

Если видим `❌ Order FAILED` - значит проблема не решена.

## Откат (если что-то пошло не так)

```bash
cd /root/Bybit_Trader

# Откатить изменения через git
git checkout HEAD -- core/executors/futures_executor.py

# Пересобрать
docker-compose down
docker-compose up -d --build
```

## Статус

- [x] Проблема найдена
- [x] Исправление сделано
- [ ] Деплой на сервер
- [ ] Тестирование
- [ ] Подтверждение работы
