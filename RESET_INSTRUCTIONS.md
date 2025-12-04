# Инструкция по сбросу на $50 баланс

## 🎯 Цель
Очистить всю торговую историю и начать с чистого листа с балансом $50.

## ⚠️ Что будет удалено
- ✅ Все сделки (trades)
- ✅ История баланса (wallet_history)
- ✅ AI решения (ai_decisions)
- ✅ Системные логи (system_logs)

## ✅ Что будет сохранено
- ✅ Исторические свечи (candles) - для ML
- ✅ Конфигурация (app_config)
- ✅ ML модели (файлы в ml_data/)
- ✅ Self-learning данные

## 📋 Шаги выполнения

### 1. Копируем файлы на сервер

```bash
# Копируем обновлённый config.py с балансом $50
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/

# Копируем SQL скрипт для очистки
scp Bybit_Trader/scripts/reset_trading_data.sql root@88.210.10.145:/tmp/

# Копируем скрипт проверки
scp Bybit_Trader/scripts/verify_reset.py root@88.210.10.145:/root/Bybit_Trader/scripts/
```

### 2. Подключаемся к серверу

```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
```

### 3. Останавливаем бота

```bash
docker-compose stop bot
```

### 4. Очищаем торговые данные

```bash
docker exec bybit_db psql -U bybit_user -d bybit_trader -f /tmp/reset_trading_data.sql
```

**Ожидаемый вывод:**
```
TRUNCATE TABLE
TRUNCATE TABLE
TRUNCATE TABLE
TRUNCATE TABLE
UPDATE 1

         status          | count 
-------------------------+-------
 Trades cleared          |     0
 Wallet history cleared  |     0
 AI decisions cleared    |     0
 System logs cleared     |     0
 Candles preserved       |  XXXX
```

### 5. Пересобираем бота с новым config

```bash
docker-compose build bot
```

### 6. Запускаем бота

```bash
docker-compose up -d bot
```

### 7. Проверяем логи

```bash
docker logs -f bybit_bot --tail 100
```

**Ищем в логах:**
```
💰 Virtual Balance: $50.0
📊 Base Leverage: 5x (dynamic 2-7x)
🎯 Risk per Trade: 20.0%
```

### 8. Проверяем БД

```bash
# Проверяем что сделки очищены
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT COUNT(*) FROM trades;"

# Проверяем что candles сохранены
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT COUNT(*) FROM candles;"

# Проверяем баланс
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT * FROM app_config WHERE key = 'futures_virtual_balance';"
```

### 9. (Опционально) Запускаем автоматическую проверку

```bash
cd /root/Bybit_Trader
python3 scripts/verify_reset.py
```

**Ожидаемый вывод:**
```
✅ ALL CHECKS PASSED

📊 Summary:
   - Trades: 0 (cleared)
   - Wallet history: 0 (cleared)
   - AI decisions: 0 (cleared)
   - System logs: 0 (cleared)
   - Candles: XXXX (preserved)
   - Balance: $50.00

🚀 System ready for fresh start!
```

## 🧪 Тестирование после сброса

### 1. Проверяем что бот работает

```bash
docker logs bybit_bot --tail 50
```

Должны видеть:
- ✅ Инициализация с балансом $50
- ✅ Загрузка ML моделей
- ✅ Gatekeeper работает
- ✅ Анализ рынков

### 2. Проверяем Dashboard

Открываем: http://88.210.10.145:8585

Должны видеть:
- ✅ Balance: $50.00
- ✅ Trades: 0
- ✅ Win Rate: 0%
- ✅ ML Learning Count: сохранён (9500+)

### 3. Ждём первую сделку

Мониторим логи:
```bash
docker logs -f bybit_bot | grep -E "(OPEN LONG|OPEN SHORT|Fee check)"
```

Проверяем:
- ✅ Fee check работает
- ✅ Gatekeeper фильтрует
- ✅ Futures Brain требует Score >= 3
- ✅ Telegram уведомления с Gross/Net PnL

## 📊 Ожидаемые результаты

### Первые 24 часа:
- Сделок: 5-15 (строгая фильтрация)
- Win Rate: 30-50% (цель)
- Net PnL: -$2 до +$5 (реалистично)
- Комиссии: ~$0.12 на сделку

### Через неделю:
- Баланс: $48-$55 (цель: не потерять депозит)
- Win Rate: 40%+ (стабильно)
- Avg Trade: +$0.50 - $1.00 net

## 🚨 Что делать если что-то пошло не так

### Бот не запускается:
```bash
docker logs bybit_bot --tail 100
# Ищем ошибки
```

### Баланс не $50:
```bash
# Проверяем config
docker exec bybit_bot cat /app/config.py | grep futures_virtual_balance

# Обновляем в БД
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "UPDATE app_config SET value = '50.0' WHERE key = 'futures_virtual_balance';"

# Перезапускаем
docker-compose restart bot
```

### ML данные потеряны:
```bash
# Проверяем candles
docker exec bybit_db psql -U bybit_user -d bybit_trader -c "SELECT COUNT(*) FROM candles;"

# Если 0 - нужно восстановить из бэкапа или подождать накопления новых данных
```

## 📝 Checklist

Перед началом торговли убедись:
- [ ] Баланс = $50
- [ ] Trades = 0
- [ ] Candles > 0 (ML данные сохранены)
- [ ] Бот запущен и работает
- [ ] Dashboard показывает $50
- [ ] Gatekeeper активен
- [ ] Fee simulation включена
- [ ] Telegram уведомления работают

## 🎯 Готово!

Система сброшена и готова к торговле с $50. Удачи! 🚀

---

**Дата:** 2025-12-04  
**Версия:** v3.1 (Futures Brain Fix + Simulated Realism)  
**Стартовый баланс:** $50.00
