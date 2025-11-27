# ✅ Dashboard Final Update - Правильный расчет баланса

## Проблема

Дашборд показывал неправильный баланс и PnL:
- Показывал только USDT: $108,067
- Игнорировал BTC, ETH, SOL, BNB, USDC
- Казалось что потеряли $41,932

## Решение

### 1. Правильный расчет баланса

**Начальный депозит (известные значения):**
```
USDC: 50,000
USDT: 50,000
BTC: 1.0
ETH: 1.0
```

**Текущий баланс (все активы в USDT):**
```
USDC:  $49,995  (50,000 × $0.9999)
BTC:   $13,078  (0.1427 × $91,648)
ETH:   $6,575   (2.192 × $3,028)
SOL:   $11,340  (79.42 × $142.79)
USDT:  $107,705
BNB:   $1,791   (2.003 × $894)
─────────────────────────────
TOTAL: $190,484
```

**Начальный баланс в USDT:**
```
USDC:  $49,995  (50,000 × $0.9999)
USDT:  $50,000
BTC:   $91,648  (1.0 × $91,648 текущая цена)
ETH:   $3,028   (1.0 × $3,028 текущая цена)
─────────────────────────────
TOTAL: $194,671 (приблизительно)
```

**PnL:**
```
Текущий: $190,484
Начальный: ~$194,671
PnL: -$4,187 (-2.15%)
```

### 2. Исправления в коде

**`web/app.py` - функция `get_real_balance()`:**

```python
# Начальный депозит (известные значения)
initial_deposits = {
    'USDC': 50000.0,
    'USDT': 50000.0,
    'BTC': 1.0,
    'ETH': 1.0
}

# Для каждого актива
for coin, data in balances.items():
    current = float(data['total'])
    
    if current > 0:
        # Конвертируем в USDT
        if coin == 'USDT':
            usdt_value = current
            current_price = 1.0
        elif coin == 'USDC':
            usdt_value = current * 0.9999
            current_price = 0.9999
        else:
            # Получаем текущую цену
            ticker = await api.get_ticker(f"{coin}USDT")
            current_price = float(ticker['last_price'])
            usdt_value = current * current_price
        
        # Рассчитываем изменение
        initial_amount = initial_deposits.get(coin, 0)
        change_amount = current - initial_amount
        
        # Начальная стоимость в USDT
        if coin in initial_deposits:
            if coin in ['USDT', 'USDC']:
                initial_usdt_value = initial_amount
            else:
                # Для BTC/ETH используем текущую цену
                initial_usdt_value = initial_amount * current_price
        
        result.append({
            'coin': coin,
            'total': current,
            'current_price': current_price,
            'usdt_value': usdt_value,
            'initial_amount': initial_amount,
            'change_amount': change_amount,
            'initial_usdt_value': initial_usdt_value
        })

# Рассчитываем начальный баланс в USDT
initial_balance_usdt = sum(item['initial_usdt_value'] for item in result)

# Рассчитываем PnL
total_pnl = total_usdt_value - initial_balance_usdt
total_pnl_pct = (total_pnl / initial_balance_usdt) * 100
```

### 3. Исправление Event Loop

**Проблема:** Flask создает новый event loop для каждого запроса, но `async_session` был привязан к старому loop.

**Решение:** Создаем новый engine и session для каждого запроса:

```python
async def get_stats():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    # Создаем новый engine для текущего event loop
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        # ... запросы к БД
```

Применено ко всем функциям:
- `get_stats()`
- `get_open_trades()`
- `get_recent_trades()`
- `get_balance_history()`
- `get_recent_logs()`

### 4. Endpoint `/api/data`

Используем `asyncio.run()` вместо ручного управления event loop:

```python
@app.route('/api/data')
def get_data():
    try:
        async def fetch_all_data():
            balance_data = await get_real_balance()
            stats = await get_stats()
            closed_trades = await get_recent_trades()
            balance_history = await get_balance_history()
            logs = await get_recent_logs()
            
            return {
                'balance': balance_data,
                'stats': stats,
                'closed_trades': closed_trades,
                'balance_history': balance_history,
                'logs': logs,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        data = asyncio.run(fetch_all_data())
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Результат

✅ Дашборд показывает правильный баланс всех активов
✅ Правильный расчет PnL от начального депозита
✅ Нет ошибок event loop
✅ API возвращает 200 OK

## Дашборд

URL: http://88.210.10.145:8585

Показывает:
- Все активы (USDC, USDT, BTC, ETH, SOL, BNB)
- Текущие цены
- USDT эквивалент каждого актива
- Начальный баланс
- Текущий баланс
- PnL в $ и %
- Статистику торгов
- Последние сделки
- Логи

## Проверка

```bash
# Проверить API
curl http://88.210.10.145:8585/api/data | python3 -m json.tool

# Проверить логи
docker logs --tail 20 bybit_dashboard

# Проверить реальный баланс
docker exec bybit_bot python scripts/check_wallet_assets.py
```

## Файлы

- ✅ `web/app.py` - исправлен расчет баланса и event loop
- ✅ `scripts/check_wallet_assets.py` - проверка всех активов
- ✅ `scripts/get_transaction_history.py` - попытка получить историю
- ✅ `scripts/get_deposits.py` - попытка получить депозиты

## Примечание

Начальный баланс рассчитывается приблизительно, так как:
- Demo Trading API не возвращает историю депозитов
- Используем текущие цены BTC/ETH для расчета начальной стоимости
- Реальный начальный баланс был на момент депозита (цены могли быть другими)

Для точного расчета нужно знать цены BTC и ETH на момент депозита.
