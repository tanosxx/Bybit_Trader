# 🎮 Настройка Bybit Demo Trading

## Что это?

Bybit Demo Trading - это **реальная торговля с виртуальными деньгами**:
- Реальные цены и рынок
- Реальные ордера (но виртуальный баланс)
- Тестовый баланс от Bybit
- Проверка всей логики перед реальными деньгами

## 📋 Шаги настройки

### 1. Создай Demo аккаунт

1. Перейди на https://testnet.bybit.com
2. Зарегистрируйся (можно с тем же email что и основной аккаунт)
3. Получи тестовый баланс (обычно дают автоматически)

### 2. Создай API ключи для Demo

1. Войди в https://testnet.bybit.com
2. Перейди в **API Management**
3. Создай новый API ключ:
   - **Name**: Bybit Trading Bot Demo
   - **Permissions**: 
     - ✅ Read-Write (для ордеров)
     - ✅ Contract Trading
     - ✅ Spot Trading
   - **IP Whitelist**: 88.210.10.145 (наш сервер)

4. Сохрани:
   - API Key
   - API Secret

### 3. Обнови .env на сервере

```bash
ssh root@88.210.10.145

# Редактируй .env
nano /root/Bybit_Trader/.env

# Измени:
BYBIT_API_KEY=твой_demo_api_key
BYBIT_API_SECRET=твой_demo_api_secret
BYBIT_TESTNET=true  # ВАЖНО! Включить demo режим

# Сохрани: Ctrl+O, Enter, Ctrl+X
```

### 4. Перезапусти бота

```bash
cd /root/Bybit_Trader
docker-compose build bot
docker rm -f bybit_bot
docker run -d --name bybit_bot --network bybit_trader_bybit_network --env-file /root/Bybit_Trader/.env bybit_trader_bot:latest
```

### 5. Проверь логи

```bash
docker logs -f bybit_bot
```

Должно быть:
```
🔧 Bybit API: https://api-testnet.bybit.com (DEMO MODE)
💰 Balance: $10000.00 (тестовый баланс)
```

## ✅ Преимущества Demo Trading

1. **Реальное тестирование**
   - Реальные цены
   - Реальное исполнение ордеров
   - Реальные комиссии

2. **Безопасность**
   - Виртуальные деньги
   - Нет риска потерь
   - Можно экспериментировать

3. **Проверка логики**
   - API работает правильно?
   - Ордера открываются/закрываются?
   - SL/TP срабатывают?

4. **Статистика**
   - Реальная статистика торговли
   - Винрейт, PnL, Sharpe Ratio
   - Оптимизация параметров

## 🎯 Когда переходить на реальные деньги?

Переходи на mainnet когда:
- ✅ 100+ сделок на demo
- ✅ Винрейт > 55%
- ✅ Положительный PnL
- ✅ Нет критических ошибок
- ✅ Стратегия оптимизирована

## 🔄 Переключение на Mainnet

Когда будешь готов:

```bash
# В .env измени:
BYBIT_TESTNET=false

# И используй РЕАЛЬНЫЕ API ключи (не demo!)
BYBIT_API_KEY=твой_реальный_api_key
BYBIT_API_SECRET=твой_реальный_api_secret
```

---

**ВАЖНО**: Сначала протестируй на Demo! Не рискуй реальными деньгами без тестирования!
