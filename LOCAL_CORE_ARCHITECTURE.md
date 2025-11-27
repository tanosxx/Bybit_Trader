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

### 2. `core/ml_service.py` - ML инференс
- **Модель**: RandomForest/XGBoost (обучается в Colab)
- **Файл**: `ml_data/trained_model.joblib`
- **Функции**:
  - `load_model()` - загрузка модели
  - `predict()` - предсказание (BUY=1, SELL=-1, HOLD=0)

**Фичи модели**:
```python
['rsi', 'macd_value', 'macd_signal', 'macd_histogram',
 'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
 'ema_20', 'ema_50', 'volume_sma', 'price_change_pct', 'volatility']
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
pip install vaderSentiment joblib xgboost
```

### 2. CryptoPanic API Key
1. Зарегистрируйся: https://cryptopanic.com/developers/api/
2. Получи бесплатный ключ (100 запросов/час)
3. Добавь в `.env`:
```
CRYPTOPANIC_API_KEY=your_key_here
```

### 3. ML модель
Обучи модель в Google Colab и скопируй файлы:
```
ml_data/trained_model.joblib
ml_data/trained_model_scaler.joblib  # опционально
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
