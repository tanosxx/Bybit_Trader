# BTC Correlation Filter - 11 декабря 2025

## Проблема

Бот открывал LONG по альткоинам (ETH, SOL, BNB, XRP) когда их локальные индикаторы были положительными, **игнорируя состояние BTC**.

**Результат:** Гарантированный стоп-лосс, потому что:
- BTC падает → альткоины падают сильнее
- BTC растёт → альткоины могут не успеть за ним

**Пример:**
```
SOL: RSI=35 (перепродан), MACD=bullish → ML говорит BUY
НО: BTC падает -1.2% за последние 30 минут
→ Открываем LONG по SOL → BTC продолжает падать → SOL падает -3% → Stop Loss
```

## Решение: KING BTC RULE

**"Папа решает всё"** - новый фильтр который проверяет состояние BTC перед открытием сделки по альткоину.

### Логика

**Для LONG по альткоину:**
- Если BTC падает > 0.3% → **БЛОКИРОВАТЬ**
- Причина: "King BTC is dumping (-0.5%)"

**Для SHORT по альткоину:**
- Если BTC растёт > 0.3% → **БЛОКИРОВАТЬ**
- Причина: "King BTC is pumping (+0.8%)"

**Для BTC:**
- Фильтр не применяется (торгуем сам BTC без ограничений)

## Реализация

### 1. Конфигурация (config.py)

```python
# ========== BTC CORRELATION FILTER (KING BTC RULE) ==========
btc_correlation_enabled: bool = True  # Включить фильтр
btc_correlation_threshold: float = 0.3  # Порог 0.3% (30 базисных пунктов)
btc_correlation_candles: int = 2  # Анализ 2 свечей (2 × 15m = 30 минут)
```

**Параметры:**
- `btc_correlation_enabled` - включить/выключить фильтр
- `btc_correlation_threshold` - порог изменения BTC (0.3% = консервативно)
- `btc_correlation_candles` - количество свечей для анализа (2 = 30 минут)

### 2. Метод проверки тренда BTC (ai_brain_local.py)

```python
def _get_btc_trend_strength(self, btc_klines: list) -> float:
    """
    Получить силу тренда BTC за последние N свечей.
    
    Returns:
        float: Процентное изменение BTC
               Положительное = рост, отрицательное = падение
    """
    # Берём последние N свечей
    recent_candles = btc_klines[-candles_count:]
    
    # Цена открытия первой свечи
    open_price = float(recent_candles[0]['open'])
    
    # Цена закрытия последней свечи
    close_price = float(recent_candles[-1]['close'])
    
    # Процентное изменение
    change_pct = ((close_price - open_price) / open_price) * 100
    
    return change_pct
```

**Пример:**
- BTC открылся на $90,000
- BTC закрылся на $89,700
- Изменение: -0.33% (падение)

### 3. Метод проверки корреляции (ai_brain_local.py)

```python
def _check_btc_correlation(
    self, 
    symbol: str, 
    decision: str, 
    btc_klines: list
) -> Dict:
    """
    BTC Correlation Filter (Gatekeeper Level 2.5)
    
    Returns:
        {
            'allowed': bool,
            'btc_trend': float,
            'reason': str
        }
    """
    # Если торгуем сам BTC - пропускаем
    if symbol == 'BTCUSDT':
        return {'allowed': True, ...}
    
    # Получаем тренд BTC
    btc_trend = self._get_btc_trend_strength(btc_klines)
    
    # Проверяем корреляцию
    if decision == 'BUY' and btc_trend < -threshold:
        return {
            'allowed': False,
            'reason': f'King BTC is dumping ({btc_trend:+.2f}%)'
        }
    
    if decision == 'SELL' and btc_trend > threshold:
        return {
            'allowed': False,
            'reason': f'King BTC is pumping ({btc_trend:+.2f}%)'
        }
    
    return {'allowed': True, ...}
```

### 4. Интеграция в Decision Tree (ai_brain_local.py)

**Позиция в цепочке:**
```
0. Strategic Brain (глобальный режим)
1. CHOP Filter (флэт)
2. Pattern Filter (исторический WR)
2.5. BTC Correlation Filter ← НОВЫЙ!
3. TA Confirmation
4. Fee Profitability Check
5. Final Decision
```

**Код:**
```python
# ========== GATEKEEPER LEVEL 2.5: BTC CORRELATION CHECK ==========
if ml_decision in ['BUY', 'SELL']:
    # Получаем свечи BTC
    btc_klines = market_data.get('btc_klines', [])
    
    # Проверяем корреляцию
    btc_check = self._check_btc_correlation(symbol, ml_decision, btc_klines)
    
    if not btc_check['allowed']:
        print(f"   🚫 BTC Correlation: {btc_check['reason']}")
        return {'decision': 'SKIP', ...}
    else:
        print(f"   ✅ BTC Correlation: {btc_check['reason']}")
```

### 5. Загрузка BTC свечей (hybrid_loop.py)

```python
# Получаем BTC свечи для корреляционного фильтра
btc_klines = []
if symbol != 'BTCUSDT':
    try:
        btc_klines = await self.api.get_klines('BTCUSDT', '15', limit=10)
    except Exception as e:
        print(f"   ⚠️ Failed to get BTC klines: {e}")

# Добавляем в market_data
market_data = {
    ...
    "btc_klines": btc_klines  # Для BTC Correlation Filter
}
```

## Примеры работы

### Пример 1: LONG по ETH заблокирован (BTC падает)

```
📊 Analyzing ETHUSDT...
   Price: $3,200
   RSI: 35.2 (перепродан)
   MACD: bullish
   Trend: downtrend

🧠 Local Brain analyzing ETHUSDT...
   ✅ Gatekeeper: PASSED (CHOP: 45.2, Historical WR: 55.0%)
   🤖 ML Signal: BUY (conf: 68%, change: +1.2%)
   
   🚫 BTC Correlation: King BTC is dumping (-0.8%)
   
   🧠 AI Decision: SKIP
   🎯 Confidence: 0%
   ⚠️  Risk: 7/10
```

**Результат:** Сделка заблокирована, избежали убытка.

### Пример 2: SHORT по SOL заблокирован (BTC растёт)

```
📊 Analyzing SOLUSDT...
   Price: $132
   RSI: 68.5 (перекуплен)
   MACD: bearish
   Trend: uptrend

🧠 Local Brain analyzing SOLUSDT...
   ✅ Gatekeeper: PASSED (CHOP: 52.1, Historical WR: 48.0%)
   🤖 ML Signal: SELL (conf: 62%, change: -0.8%)
   
   🚫 BTC Correlation: King BTC is pumping (+0.5%)
   
   🧠 AI Decision: SKIP
   🎯 Confidence: 0%
   ⚠️  Risk: 7/10
```

**Результат:** Сделка заблокирована, избежали убытка.

### Пример 3: LONG по XRP разрешён (BTC нейтрален)

```
📊 Analyzing XRPUSDT...
   Price: $2.05
   RSI: 42.3
   MACD: bullish
   Trend: sideways

🧠 Local Brain analyzing XRPUSDT...
   ✅ Gatekeeper: PASSED (CHOP: 48.5, Historical WR: 52.0%)
   🤖 ML Signal: BUY (conf: 65%, change: +0.9%)
   
   ✅ BTC Correlation: BTC trend OK (+0.1%)
   
   📊 TA Confirmation: ✅ (strength: 70%)
   
   🧠 AI Decision: BUY
   🎯 Confidence: 72%
   ⚠️  Risk: 5/10
```

**Результат:** Сделка разрешена, BTC не мешает.

### Пример 4: BTC сам торгуется без ограничений

```
📊 Analyzing BTCUSDT...
   Price: $90,000
   RSI: 38.5
   MACD: bullish
   Trend: downtrend

🧠 Local Brain analyzing BTCUSDT...
   ✅ Gatekeeper: PASSED (CHOP: 51.2, Historical WR: 58.0%)
   🤖 ML Signal: BUY (conf: 70%, change: +1.5%)
   
   ✅ BTC Correlation: Trading BTC itself
   
   📊 TA Confirmation: ✅ (strength: 75%)
   
   🧠 AI Decision: BUY
   🎯 Confidence: 78%
   ⚠️  Risk: 4/10
```

**Результат:** BTC торгуется без ограничений.

## Преимущества

### До внедрения:
- ❌ Открывали LONG по альткоинам когда BTC падал
- ❌ Открывали SHORT по альткоинам когда BTC рос
- ❌ Высокий процент стоп-лоссов (30-40%)
- ❌ Игнорировали "Папу" рынка

### После внедрения:
- ✅ Блокируем LONG когда BTC падает > 0.3%
- ✅ Блокируем SHORT когда BTC растёт > 0.3%
- ✅ Снижаем процент стоп-лоссов
- ✅ Учитываем корреляцию с BTC

## Настройка

### Консервативный режим (меньше сделок, выше качество)

```python
btc_correlation_threshold: float = 0.2  # Порог 0.2% (строже)
btc_correlation_candles: int = 3  # Анализ 3 свечей (45 минут)
```

### Агрессивный режим (больше сделок, ниже качество)

```python
btc_correlation_threshold: float = 0.5  # Порог 0.5% (мягче)
btc_correlation_candles: int = 1  # Анализ 1 свечи (15 минут)
```

### Отключить фильтр

```python
btc_correlation_enabled: bool = False
```

## Мониторинг

### Логи

Фильтр логирует каждую проверку:
```
✅ BTC Correlation: BTC trend OK (+0.1%)
🚫 BTC Correlation: King BTC is dumping (-0.8%)
🚫 BTC Correlation: King BTC is pumping (+0.5%)
```

### Статистика

Добавить в `full_system_check.py`:
```python
# Статистика BTC Correlation Filter
btc_blocks = db.query(
    "SELECT COUNT(*) FROM trades WHERE exit_reason LIKE '%King BTC%'"
)
print(f"BTC Correlation blocks: {btc_blocks}")
```

### Dashboard

Добавить индикатор:
```
BTC Trend: +0.3% ✅ (OK for LONG)
BTC Trend: -0.8% 🚫 (Block LONG)
BTC Trend: +0.5% 🚫 (Block SHORT)
```

## Тестирование

### Тест 1: BTC падает, LONG блокируется

```python
btc_klines = [
    {'open': 90000, 'close': 89700},  # -0.33%
    {'open': 89700, 'close': 89500}   # -0.22%
]
# Итого: -0.55% за 30 минут

result = brain._check_btc_correlation('ETHUSDT', 'BUY', btc_klines)
assert result['allowed'] == False
assert 'dumping' in result['reason']
```

### Тест 2: BTC растёт, SHORT блокируется

```python
btc_klines = [
    {'open': 90000, 'close': 90300},  # +0.33%
    {'open': 90300, 'close': 90500}   # +0.22%
]
# Итого: +0.55% за 30 минут

result = brain._check_btc_correlation('SOLUSDT', 'SELL', btc_klines)
assert result['allowed'] == False
assert 'pumping' in result['reason']
```

### Тест 3: BTC нейтрален, всё разрешено

```python
btc_klines = [
    {'open': 90000, 'close': 90100},  # +0.11%
    {'open': 90100, 'close': 90150}   # +0.05%
]
# Итого: +0.16% за 30 минут (< 0.3%)

result = brain._check_btc_correlation('XRPUSDT', 'BUY', btc_klines)
assert result['allowed'] == True
```

## Deployment

### Файлы изменены:
- ✅ `config.py` - добавлены параметры фильтра
- ✅ `core/ai_brain_local.py` - добавлены методы проверки
- ✅ `core/hybrid_loop.py` - добавлена загрузка BTC свечей

### Команды деплоя:
```bash
# Копируем файлы
scp Bybit_Trader/config.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/core/ai_brain_local.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/hybrid_loop.py root@88.210.10.145:/root/Bybit_Trader/core/

# Пересобираем контейнер
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Проверка:
```bash
# Логи фильтра
docker logs bybit_bot | grep "BTC Correlation"

# Должны увидеть:
# ✅ BTC Correlation: BTC trend OK (+0.1%)
# или
# 🚫 BTC Correlation: King BTC is dumping (-0.8%)
```

## Ожидаемый эффект

### Метрики до внедрения:
- Win Rate: 29-31%
- Avg Loss: -$1.50
- Стоп-лоссов по альткоинам: ~40%

### Ожидаемые метрики после:
- Win Rate: 35-40% (+5-10%)
- Avg Loss: -$1.20 (-20%)
- Стоп-лоссов по альткоинам: ~25% (-15%)

### Почему:
- Меньше сделок против тренда BTC
- Выше качество входов
- Лучшая корреляция с рынком

---

**Дата:** 2025-12-11 21:45 UTC  
**Автор:** Kiro AI  
**Статус:** ✅ Готово к деплою
