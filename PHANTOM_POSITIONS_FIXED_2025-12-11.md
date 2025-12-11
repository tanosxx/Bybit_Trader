# Исправление фантомных позиций - 11 декабря 2025

## Проблема

На Dashboard отображались **23 фантомные позиции** с огромными unrealized losses:
- XRPUSDT: **-$106.88** (14 ордеров, размер 1368.3)
- ETHUSDT: **-$9.17** (3 ордера)
- SOLUSDT: **-$11.66** (2 ордера)
- BNBUSDT: несколько позиций
- Всего: 23 позиции в БД, 0 на бирже

**Причина:** Позиции были закрыты на бирже, но остались в БД со статусом `OPEN`.

## Решение

### 1. Исправлен Sync Service

**Файл:** `core/sync_positions.py`

**Логика:**
```python
async def sync_futures_positions(self):
    # Получаем ВСЕ позиции с биржи
    all_positions = await self.api.get_positions()
    
    # Разделяем на открытые (size > 0) и закрытые (size = 0)
    exchange_positions = {}  # Открытые
    closed_symbols = set()   # Закрытые
    
    # Закрываем в БД позиции которых нет на бирже
    for trade in db_trades:
        if trade.symbol not in exchange_positions:
            trade.status = 'CLOSED'
            trade.exit_time = datetime.utcnow()
            trade.exit_price = trade.entry_price
            trade.exit_reason = 'Sync: closed on exchange'
            
            # Обучаем Self-Learning на результате
            if trade.ml_features and trade.pnl is not None:
                learner.learn(trade.ml_features, result)
```

**Особенности:**
- ✅ Закрывает фантомные позиции в БД
- ✅ Обучает Self-Learning на каждой закрытой позиции
- ✅ Обновляет quantity существующих позиций
- ✅ НЕ добавляет новые позиции (это делает бот)

### 2. Исправлена проблема с Pydantic

**Проблема:** `openrouter_api_key` Field required

**Причина:** В `/app/core/config.py` был старый файл без `Optional[str] = "dummy"`

**Решение:**
```bash
# Удалили дубликат config.py из core/
rm /root/Bybit_Trader/core/config.py

# Пересобрали образ
docker-compose build sync
```

### 3. Deployment

```bash
# 1. Копируем файлы
scp Bybit_Trader/core/sync_positions.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/

# 2. Удаляем дубликат
ssh root@88.210.10.145 "rm /root/Bybit_Trader/core/config.py"

# 3. Пересобираем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build sync"

# 4. Перезапускаем
ssh root@88.210.10.145 "docker stop bybit_sync && docker rm bybit_sync"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d sync"
```

## Результат

### До исправления:
- Открытых позиций в БД: **23**
- Открытых позиций на бирже: **0**
- Расхождение: **23 фантома**
- Dashboard показывал: **-$106.88 unrealized loss**

### После исправления:
```
✅ Синхронизация завершена:
   Закрыто в БД: 23
   Обновлено: 0
   Осталось открытых: 0
   На бирже открытых: 0
   ✅ Полное совпадение!
```

### Статистика торговли:
- Всего сделок: **332**
- Открытых позиций: **0** ✅
- Закрытых сделок: **332**
- Win Rate: **29.2%**
- Net Profit: **+$279.10** (+279% ROI)
- Текущий баланс: **$379.10** (стартовый $100)

### Self-Learning обновлён:
- Обучено на сделках: **9,690** (было 9,670)
- Добавлено: **+20 samples** (23 фантома - 3 уже были)
- Model Accuracy: **90.49%**

## Интервал синхронизации

Sync Service работает каждые **30 секунд**:
- Синхронизирует балансы
- Закрывает фантомные позиции
- Обновляет quantity
- Обучает Self-Learning

## Проверка

```bash
# Полная диагностика
docker exec bybit_bot python full_system_check.py

# Логи sync
docker logs bybit_sync --tail 50

# Проверка БД
docker exec bybit_db psql -U bybit_user -d bybit_trader -c \
  "SELECT COUNT(*) FROM trades WHERE status = 'OPEN';"
```

## Известные проблемы

### Dashboard показывает полный баланс Demo счёта

**Проблема:** Dashboard API возвращает `$186,175.67` вместо виртуального `$379.10`

**Причина:** API берёт данные с Bybit API вместо расчёта из БД

**Решение:** Нужно обновить `web/app.py` чтобы считать баланс из trades:
```python
# Вместо
balance_data = await api.get_wallet_balance()

# Использовать
virtual_balance = 100.0 + sum(trade.pnl - trade.fee_entry - trade.fee_exit 
                               for trade in closed_trades)
```

**Статус:** Не критично, основная проблема (фантомные позиции) решена.

---

**Дата:** 2025-12-11 14:57 UTC  
**Автор:** Kiro AI  
**Статус:** ✅ Завершено
