# Local Core Architecture - Автономный торговый мозг

## 🎯 Цель
Полная автономность бота без зависимости от внешних LLM API (Gemini/OpenAI).

## 📁 Новые модули

### 1. `core/news_brain.py` - Фундаментальный анализ
- **Источник**: CryptoPanic API (бесплатный)
- **NLP**: VADER Sentiment (легковесный, работает локально)
- **Функции**:
  - `fetch_latest_news()` - получение новостей за последний час
  - `analyze_sentiment()` - анализ тональности заголовка
  - `get_market_sentiment()` - итоговый сентимент рынка

**Статусы сентимента**:
| Статус | Score | Действие |
|--------|-------|----------|
| EXTREME_FEAR | < -0.5 | PANIC_SELL / CLOSE_ALL |
| FEAR | -0.5 to -0.2 | Осторожные сделки, размер /2 |
| NEUTRAL | -0.2 to 0.2 | Нормальная торговля |
| GREED | 0.2 to 0.5 | Разрешены лонги |
| EXTREME_GREED | > 0.5 | Только лонги, размер x1.2 |

### 2. `core/ml_predictor_v2.py` - LSTM модель (УЖЕ СУЩЕСТВУЕТ!)
- **Модель**: LSTM (TensorFlow/Keras)
- **Файлы**: 
  - `ml_training/models/bybit_lstm_model_v2.h5`
  - `ml_training/models/scaler_X_v2.pkl`
  - `ml_training/models/scaler_y_v2.pkl`
- **Предсказание**: % изменение цены за следующий час

**Фичи модели** (24 нормализованных):
```python
['open_norm', 'high_norm', 'low_norm', 'rsi_norm',
 'macd_norm', 'macd_signal_norm', 'macd_hist_norm',
 'bb_upper_norm', 'bb_lower_norm', 'bb_width',
 'sma20_norm', 'sma50_norm', 'ema12_norm', 'ema26_norm',
 'atr_norm', 'stoch_k_norm', 'stoch_d_norm', 'volume_log',
 'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos']
```

### 3. `core/ai_brain_local.py` - Локальный мозг
Замена `ai_brain_smart.py` - работает полностью локально!

**Decision Tree**:
```
┌─────────────────────────────────────────────────────────┐
│                    NEWS RISK CHECK                       │
│  EXTREME_FEAR? ──────────────────────► PANIC_SELL       │
└─────────────────────────────────────────────────────────┘
                          │ нет
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      ML SIGNAL                           │
│  Confidence < 75%? ──────────────────► SKIP             │
└─────────────────────────────────────────────────────────┘
                          │ нет
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   TA CONFIRMATION                        │
│  Confirms? ──► Boost confidence                         │
│  Conflicts? ──► Reduce confidence, size x0.7            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   FINAL DECISION                         │
│  BUY / SELL / SKIP + risk_score + position_multiplier   │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Установка

### 1. Зависимости
```bash
pip install vaderSentiment
```

### 2. CryptoPanic API Key (уже настроен!)
```
CRYPTOPANIC_API_KEY=3e44ec47b8bdffdf84526285e2eb948c2537bdd4
```
⚠️ Лимит: 100 req/month, кэш 8 часов

### 3. ML модель (УЖЕ РАБОТАЕТ!)
LSTM модель уже обучена и загружена:
```
ml_training/models/bybit_lstm_model_v2.h5
ml_training/models/scaler_X_v2.pkl
ml_training/models/scaler_y_v2.pkl
```

## 🚀 Интеграция в loop.py

Замени импорт:
```python
# Было:
from core.ai_brain_smart import get_smart_ai_brain

# Стало:
from core.ai_brain_local import get_local_brain
```

И в `__init__`:
```python
# Было:
self.ai_brain = get_smart_ai_brain()

# Стало:
self.ai_brain = get_local_brain()
```

## 📊 Пример использования

```python
from core.ai_brain_local import get_local_brain

brain = get_local_brain()

market_data = {
    'symbol': 'BTCUSDT',
    'price': 95000,
    'rsi': 45,
    'macd': {'value': 100, 'signal': 80, 'histogram': 20, 'trend': 'bullish'},
    'bollinger_bands': {'upper': 96000, 'middle': 95000, 'lower': 94000},
    'trend': 'uptrend',
    'technical_signal': 'BUY'
}

result = await brain.decide_trade(market_data)
print(result)
# {
#   'decision': 'BUY',
#   'confidence': 0.82,
#   'risk_score': 4,
#   'source': 'ML_CONFIRMED',
#   'reasoning': 'ML: BUY (85%) | News: NEUTRAL | TA: confirms | RSI: 45.0',
#   'position_size_multiplier': 1.0,
#   ...
# }
```

## ⚠️ Fallback режимы

| Ситуация | Поведение |
|----------|-----------|
| ML модель не найдена | HOLD (безопасный режим) |
| CryptoPanic API упал | NEUTRAL (торговля разрешена) |
| ML confidence < 75% | SKIP |
| EXTREME_FEAR | PANIC_SELL |

## 📈 Преимущества

1. **Нет лимитов API** - работает 24/7 без ограничений
2. **Нет задержек** - мгновенные решения
3. **Нет затрат** - бесплатно (кроме CryptoPanic 100 req/hour)
4. **Работает на слабом VPS** - минимальные требования к ресурсам
