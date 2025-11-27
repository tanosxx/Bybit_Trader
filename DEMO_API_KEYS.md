# 🔑 Как получить API ключи для Demo Trading

**ВАЖНО**: API ключи для Demo Trading создаются ОТДЕЛЬНО от обычных ключей!

## 📋 Пошаговая инструкция

### 1. Зайди на основной сайт
- Перейди на **https://bybit.com**
- Войди в свой аккаунт

### 2. Переключись в Demo Trading
- Найди тумблер **"Demo Trading"** вверху страницы
- Переключи его в режим **Demo**
- Ты увидишь виртуальный баланс (~$50,000)

### 3. Открой API Management в Demo режиме
- **ВАЖНО**: Находясь в Demo режиме, перейди в настройки
- Найди раздел **API Management**
- Это будут API ключи ТОЛЬКО для Demo Trading!

### 4. Создай новый API ключ
- Нажми **"Create New Key"**
- Название: `Bybit_Trading_Bot_Demo`

### 5. Выбери разрешения
Дай следующие разрешения:
- ✅ **Spot Trading** - Read & Write
- ✅ **Contract Trading** - Read & Write  
- ✅ **Wallet** - Read
- ✅ **Unified Trading Account** - Read & Write

### 6. Добавь IP Whitelist
- **ОБЯЗАТЕЛЬНО**: Добавь IP сервера
- IP: **88.210.10.145**
- Без этого API не будет работать!

### 7. Сохрани ключи
После создания ты получишь:
- **API Key**: Например `DEMO_xxxxxxxxxxxxx`
- **API Secret**: Например `yyyyyyyyyyyyyyyy`

**ВАЖНО**: Сохрани их сразу! Secret показывается только один раз!

### 8. Обнови .env на сервере

```bash
ssh root@88.210.10.145

# Редактируй .env
nano /root/Bybit_Trader/.env

# Измени:
BYBIT_API_KEY=твой_demo_api_key
BYBIT_API_SECRET=твой_demo_api_secret
BYBIT_TESTNET=false  # Demo Trading использует боевой URL!

# Сохрани: Ctrl+O, Enter, Ctrl+X
```

### 9. Перезапусти бота

```bash
cd /root/Bybit_Trader
docker-compose build bot
docker rm -f bybit_bot
docker run -d --name bybit_bot --network bybit_trader_bybit_network --env-file /root/Bybit_Trader/.env bybit_trader_bot:latest
```

### 10. Проверь работу

```bash
# Тест API
docker run --rm --network bybit_trader_bybit_network --env-file /root/Bybit_Trader/.env bybit_trader_bot:latest python scripts/test_real_bybit_api.py
```

Должно быть:
```
✅ Баланс получен:
   USDT: 50000.0000 (доступно: 50000.0000)
```

## ⚠️ Важные моменты

1. **Demo Trading ≠ Testnet**
   - Demo Trading: основной сайт bybit.com, режим Demo
   - Testnet: отдельный сайт testnet.bybit.com
   - Используем Demo Trading!

2. **URL для Demo Trading**
   - ✅ Правильно: `https://api.bybit.com`
   - ❌ Неправильно: `https://api-testnet.bybit.com`

3. **API ключи разные**
   - Обычные ключи НЕ работают в Demo
   - Demo ключи НЕ работают в обычном режиме
   - Нужны отдельные ключи для Demo!

4. **IP Whitelist обязателен**
   - Без IP whitelist будет 401 ошибка
   - IP сервера: 88.210.10.145

## 🎯 Что дальше?

После получения правильных Demo API ключей:
1. Обнови .env
2. Перезапусти бота
3. Бот начнет открывать РЕАЛЬНЫЕ ордера на Demo балансе!
4. Проверяй сделки на bybit.com в Demo режиме

---

**Статус**: ⏳ Ждем Demo API ключи от bybit.com (Demo Trading режим)
