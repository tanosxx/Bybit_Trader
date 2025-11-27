# 🔧 Bybit API - Текущий статус

**Дата**: 26 ноября 2025, 11:30 UTC

## ❌ Проблема: 401 Unauthorized для приватных эндпоинтов

### Что работает ✅

- **Публичные эндпоинты** (без подписи):
  - ✅ `/v5/market/tickers` - получение цены BTC
  - ✅ `/v5/market/kline` - получение свечей
  
### Что НЕ работает ❌

- **Приватные эндпоинты** (требуют подпись):
  - ❌ `/v5/account/wallet-balance` - баланс кошелька (401)
  - ❌ `/v5/order/realtime` - открытые ордера (401)
  - ❌ `/v5/order/create` - создание ордера (не тестировали)

## 🔍 Диагностика

### API ключи
```
API Key: LmHhFgiAD8Qj27dt1P
API Secret: j3GavMoVXrUxL1uCwhqU7sDlRZyqDc4yKkQQ
Testnet: true
Base URL: https://api-testnet.bybit.com
```

### Разрешения API ключа
- ✅ Контракты - Ордера Позиции
- ✅ USDC контракты - ТОРГОВАТЬ
- ✅ Единый торговый аккаунт - Торговать
- ✅ СПОТ - ТОРГОВАТЬ
- ✅ Кошелек - Перевод с аккаунта Перевод с субаккаунта
- ✅ Обмен - Конвертер: история обмена

### Формат подписи (V5 API)
```python
# Текущая реализация:
sign_string = f"{timestamp}{api_key}{recv_window}{query_string}"
signature = HMAC_SHA256(api_secret, sign_string)

# Пример:
timestamp = "1732618800000"
api_key = "LmHhFgiAD8Qj27dt1P"
recv_window = "5000"
query_string = "accountType=UNIFIED"

sign_string = "1732618800000LmHhFgiAD8Qj27dt1P5000accountType=UNIFIED"
signature = HMAC_SHA256("j3GavMoVXrUxL1uCwhqU7sDlRZyqDc4yKkQQ", sign_string)
```

### Заголовки запроса
```
X-BAPI-API-KEY: LmHhFgiAD8Qj27dt1P
X-BAPI-SIGN: <signature>
X-BAPI-TIMESTAMP: 1732618800000
X-BAPI-RECV-WINDOW: 5000
```

## 🤔 Возможные причины 401

### 1. IP Whitelist
- **Проблема**: Demo API ключи могут требовать IP whitelist
- **Решение**: Добавить IP сервера (88.210.10.145) в whitelist на Bybit Testnet

### 2. Неправильная подпись
- **Проблема**: Формат подписи для V5 API может отличаться
- **Решение**: Проверить документацию V5 API еще раз

### 3. Разрешения API ключа
- **Проблема**: API ключ не имеет разрешения на чтение баланса
- **Решение**: Проверить разрешения в Bybit Testnet

### 4. Testnet vs Mainnet
- **Проблема**: Testnet API может работать по-другому
- **Решение**: Попробовать на Mainnet (с осторожностью!)

## 🎯 Что делать дальше?

### Вариант 1: Проверить IP Whitelist (РЕКОМЕНДУЮ)
1. Зайди на https://testnet.bybit.com
2. Перейди в API Management
3. Найди API ключ "WiSecDemo"
4. Добавь IP whitelist: **88.210.10.145**
5. Сохрани и протестируй снова

### Вариант 2: Пересоздать API ключ
1. Удали старый API ключ
2. Создай новый с теми же разрешениями
3. Обязательно добавь IP whitelist: **88.210.10.145**
4. Обнови .env на сервере

### Вариант 3: Использовать виртуальный трейдер пока
1. Вернуться к VirtualTrader (симуляция)
2. Собрать статистику на виртуальном балансе
3. Разобраться с API позже

## 📊 Текущее решение

**Сейчас используется**: VirtualTrader (симуляция)
- Ордера НЕ идут на биржу
- Баланс виртуальный ($50)
- Все в БД

**Хотим**: RealTrader (реальные ордера)
- Ордера идут на Bybit Demo
- Баланс реальный из Demo аккаунта
- Проверка всей логики

## 🔧 Команды для тестирования

```bash
# Тест API
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose build bot
docker run --rm --network bybit_trader_bybit_network --env-file .env bybit_trader_bot:latest python scripts/test_real_bybit_api.py
```

---

**Статус**: ⚠️ Ждем решения проблемы с API (скорее всего IP whitelist)
