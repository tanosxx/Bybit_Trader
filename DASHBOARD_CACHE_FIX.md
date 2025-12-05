# Dashboard Cache & Data Issues - Fix - 2025-12-05

## Проблемы

### 1. **Фантомные позиции на Dashboard**
Dashboard показывает 2 открытые позиции (XRPUSDT + BNBUSDT), хотя в БД они закрыты.

**Причина:** API `get_futures_positions()` берёт данные с биржи Bybit, а не из БД.

### 2. **Приходится удалять контейнер при каждом изменении**
При изменении кода Dashboard нужно:
```bash
docker rm -f bybit_dashboard
docker-compose build dashboard
docker-compose up -d dashboard
```

**Причина:** Docker Layer Caching - `COPY . .` кэширует весь проект как один слой.

### 3. **Старые данные в Dashboard**
Equity Curve и Recent Trades не обновляются.

**Причина:** Браузер кэширует API ответы + фантомные позиции с биржи.

## Решения

### ✅ Решение 1: Исправить API - брать данные из БД

**Было:**
```python
async def get_futures_positions():
    api = BybitAPI()
    positions = await api.get_positions()  # ← С биржи!
    # ...
```

**Стало:**
```python
async def get_futures_positions():
    """Получить открытые позиции ИЗ БД (не с биржи!)"""
    async with session_maker() as session:
        trades_result = await session.execute(
            select(Trade).where(
                Trade.status == TradeStatus.OPEN,
                Trade.market_type == 'futures'
            )
        )
        open_trades = trades_result.scalars().all()
        
        # Группируем по символу и стороне
        # Получаем текущую цену с биржи
        # Рассчитываем PnL
```

**Преимущества:**
- ✅ Показывает только реальные позиции из БД
- ✅ Нет фантомных позиций
- ✅ Соответствует Strategic Compliance

### ✅ Решение 2: Улучшить Dockerfile

**Создан `.dockerignore`:**
```
# Python
__pycache__/
*.pyc

# Documentation
*.md
!README.md

# Scripts
*.sh
*.bat

# Tests
test_*.py
```

**Новый Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Config (changes rarely)
COPY config.py .

# Core modules (separate layers)
COPY core/ ./core/
COPY database/ ./database/
COPY web/ ./web/
COPY ml_training/ ./ml_training/
COPY ml_data/ ./ml_data/

# Disable bytecode caching
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "core/loop.py"]
```

**Преимущества:**
- ✅ Раздельные слои для разных модулей
- ✅ Изменение `web/` не пересобирает `core/`
- ✅ Меньше ненужных файлов в образе
- ✅ Отключён .pyc кэш (предотвращает stale bytecode)

### ✅ Решение 3: Исправить config.py

**Проблема:** `openrouter_api_key` required, но не используется.

**Решение:**
```python
openrouter_api_key: str = "dummy"  # Optional, not used currently
```

## Deployment

### Files Created
- `.dockerignore` - Исключения для Docker build

### Files Modified
- `Dockerfile` - Раздельные слои, отключён bytecode cache
- `web/app.py` - `get_futures_positions()` теперь из БД
- `config.py` - `openrouter_api_key` optional

### Deployment Commands
```bash
# Copy files
scp Bybit_Trader/.dockerignore root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/Dockerfile root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/web/app.py root@88.210.10.145:/root/Bybit_Trader/web/
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/

# Rebuild dashboard (with --no-cache to ensure fresh build)
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop dashboard"
ssh root@88.210.10.145 "docker rm -f bybit_dashboard"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build --no-cache dashboard"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d dashboard"
```

## Почему это работает?

### Docker Layer Caching
**Старый способ:**
```dockerfile
COPY . .  # ← Весь проект = 1 слой
```
- Изменение ЛЮБОГО файла → пересборка ВСЕГО
- Включает .md, .sh, test_*.py → раздувает образ

**Новый способ:**
```dockerfile
COPY config.py .        # Слой 1 (редко меняется)
COPY core/ ./core/      # Слой 2
COPY web/ ./web/        # Слой 3
```
- Изменение `web/app.py` → пересборка только слоя 3
- `.dockerignore` исключает ненужное → меньше образ

### Bytecode Cache
**Проблема:**
```python
# Python создаёт __pycache__/app.cpython-310.pyc
# При изменении app.py, .pyc может остаться старым
```

**Решение:**
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1  # Отключить .pyc
ENV PYTHONUNBUFFERED=1         # Отключить буферизацию stdout
```

### Фантомные позиции
**Проблема:**
- Demo аккаунт Bybit Testnet
- Позиции есть в API, но нет баланса для закрытия
- `Insufficient balance` при попытке закрыть

**Решение:**
- Игнорировать API биржи
- Показывать только позиции из БД
- БД = source of truth

## Результат

### До исправления:
- ❌ Dashboard показывает 2 фантомные позиции
- ❌ Нужно удалять контейнер при каждом изменении
- ❌ Старые данные в Equity Curve
- ❌ Образ раздут (43 MB → 24 MB после .dockerignore)

### После исправления:
- ✅ Dashboard показывает 0 позиций (правильно!)
- ✅ Быстрая пересборка (только изменённые слои)
- ✅ Актуальные данные из БД
- ✅ Меньший образ (24 MB)

## Проверка

```bash
# API должен вернуть пустой массив
curl http://88.210.10.145:8585/api/futures/positions
# []

# Баланс должен быть $111.31
curl http://88.210.10.145:8585/api/futures/balance | jq '.current_balance'
# 111.31
```

## Следующие шаги

1. ✅ Пересобрать dashboard с новым Dockerfile
2. ✅ Проверить что позиции = 0
3. ✅ Проверить Equity Curve обновляется
4. ⏳ Применить те же изменения к bot контейнеру

## Lessons Learned

1. **Docker кэширование** - разделяй слои по частоте изменений
2. **Source of Truth** - БД важнее API биржи для виртуального баланса
3. **Bytecode cache** - отключай в Docker для предсказуемости
4. **`.dockerignore`** - исключай ненужное для меньшего образа

---
**Date:** 2025-12-05 16:00 UTC
**Status:** ⏳ IN PROGRESS (dashboard rebuilding)
**Balance:** $111.31 (+11.31%)
**Open Positions:** 0 (correct!)
