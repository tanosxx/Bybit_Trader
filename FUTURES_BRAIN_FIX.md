# Futures Brain Fix - 2025-12-04

## 🐛 Проблема

За последние 24 часа:
- **20 сделок - 0 выигрышей (0% Win Rate)**
- **-5.86 USDT убыток**
- Все сделки закрыты по Stop Loss за 0.1-1.5 минуты
- Все позиции SHORT, цена сразу идёт против на 2%+

## 🔍 Найденные баги

### 1. Искусственный буст confidence при HOLD/SKIP
**Было:**
```python
elif raw_decision in ['HOLD', 'SKIP']:
    if rsi > 70 and macd_trend in ['bearish', 'bearish_crossover']:
        action = 'SHORT'
        trading_conf = max(trading_conf, 60)  # Буст с 0% до 60%!
```

**Проблема**: ML говорит HOLD (0% confidence), но код открывает SHORT с искусственным 60% confidence. RSI > 70 часто означает сильный тренд вверх, а не разворот!

**Исправлено**: Убран агрессивный буст, оставлены только экстремальные сигналы (RSI < 25 или > 75 + кроссовер + тренд).

### 2. Слишком низкий порог aggressive агента
**Было:**
```python
'aggressive': {
    'weight': 1,
    'min_confidence': 40,  # Торгует с 40% confidence!
    'require_ta': False,
    'max_risk': 9
}
```

**Проблема**: Агент открывает сделки с 40% confidence без подтверждения TA.

**Исправлено**: Повышен порог до 55%.

### 3. Минимальный порог входа = 1
**Было:**
```python
self.min_score_to_trade = 1  # Достаточно 1 агента (aggressive)
```

**Проблема**: Достаточно 1 aggressive агента (вес 1) для входа.

**Исправлено**: Повышен порог до 3 (нужно минимум 2 агента или 1 conservative).

### 4. Нет защиты от SHORT на uptrend
**Было**: Код мог открыть SHORT даже на сильном восходящем тренде.

**Исправлено**: Добавлена проверка - блокируем SHORT если `trend in ['uptrend', 'strong_uptrend']`.

## ✅ Исправления

### Изменения в `futures_brain.py`:

1. **Пороги агентов (строки 58-73)**:
   - Conservative: 75% (без изменений)
   - Balanced: 60% (было 55%)
   - Aggressive: 55% (было 40%) ← **КРИТИЧНО**
   - min_score_to_trade: 3 (было 1) ← **КРИТИЧНО**

2. **Логика HOLD/SKIP (строки 260-272)**:
   - Убран агрессивный буст confidence
   - Оставлены только экстремальные сигналы:
     - RSI < 25 + bullish crossover + uptrend → LONG
     - RSI > 75 + bearish crossover + downtrend → SHORT
   - Убраны слабые сигналы (RSI 65/35)

3. **Smart Shorting (строки 274-285)**:
   - Требуется 3 условия для SHORT: негативные новости + ML SELL + медвежий тренд
   - Добавлена защита: блокируем SHORT на uptrend

## 📊 Ожидаемый результат

**До исправления:**
- Открывались SHORT с 0% confidence
- Все сделки убыточные
- Win Rate: 0%

**После исправления:**
- Минимальная confidence для входа: 55%
- Нужно согласие минимум 2 агентов (score >= 3)
- Защита от SHORT на uptrend
- Ожидаемый Win Rate: 30-40%+

## 🚀 Деплой

```bash
# 1. Копирование на сервер
scp Bybit_Trader/core/futures_brain.py root@88.210.10.145:/root/Bybit_Trader/core/

# 2. Перезапуск бота
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker-compose restart bot
docker logs -f bybit_bot --tail 50
```

## 🔍 Проверка после деплоя

Смотрим в логах:
```
🧠 FUTURES BRAIN: SHORT/LONG
   Raw Conf: XX% -> Trading Conf: YY%
   Score: Z/6 (need 3+)
```

**Хорошие сигналы:**
- Raw Conf >= 50%
- Trading Conf >= 55%
- Score >= 3

**Плохие сигналы (будут заблокированы):**
- Raw Conf < 50%
- Score < 3
- SHORT на uptrend

## 📝 Дополнительно

Если после исправления всё равно будут убытки - проверим:
1. ML модель (возможно нужно переобучить)
2. Stop Loss расстояние (сейчас 2%)
3. Gatekeeper пороги (CHOP, Historical WR)
