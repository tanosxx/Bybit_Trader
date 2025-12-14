# 🧠 Smart AI Architecture - ML Gatekeeper

## Проблема

Старая архитектура делала запрос к Gemini API на **каждое** решение:
- 60 секунд цикл × 2 символа = **120 запросов/час**
- Free Tier: 15 RPM (requests per minute) = **900 запросов/час**
- Бот убивал квоту за **7-8 часов**

## Решение: ML Gatekeeper

ML модель (RandomForest) становится **первичным фильтром**.
AI (Gemini) вызывается только в **спорных случаях**.

### Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Data Input                         │
│         (RSI, MACD, BB, EMA, Volume, Trend)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Technical Analysis (TA)                         │
│         Signal: BUY / SELL / SKIP                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           ML Model (RandomForest) Prediction                 │
│    Decision: BUY/SELL/HOLD + Confidence (0-100%)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
              ┌──────┴──────┐
              │   Filter    │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │                         │
        ▼                         ▼
┌──────────────┐         ┌──────────────┐
│  FAST PATH   │         │  SLOW PATH   │
│              │         │              │
│ ML Conf≥80%  │         │ ML Conf<80%  │
│     +        │         │     OR       │
│ TA Confirms  │         │ ML≠TA Signal │
│              │         │              │
│ ✅ TRADE     │         │ Call Gemini  │
│ (No AI call) │         │   API 🤖     │
└──────────────┘         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │                       │
                    ▼                       ▼
            ┌──────────────┐       ┌──────────────┐
            │  AI Success  │       │  AI Failed   │
            │              │       │              │
            │ Use AI       │       │ SAFETY MODE  │
            │ Decision     │       │              │
            │              │       │ ML+TA only   │
            │ ✅ TRADE     │       │ Position/2   │
            └──────────────┘       └──────────────┘
```

## Smart Flow

### 1. ML Prediction (Всегда)
```python
ml_prediction = ml_model.predict(features)
# Returns: {'decision': 'BUY', 'confidence': 0.85, 'predicted_change': 0.02}
```

### 2. Decision Logic

#### FAST PATH (90% случаев)
```
IF (ML confidence >= 80%) AND (TA confirms ML direction):
    ✅ TRADE WITHOUT AI CALL
    💰 API Call Saved!
```

#### SLOW PATH (10% случаев)
```
IF (ML confidence < 80%) OR (ML ≠ TA signal):
    🤔 Call Gemini API for final decision
    
    IF API Success:
        ✅ Use AI decision
    
    IF API Failed (429 / timeout):
        ⚠️ SAFETY MODE
        - Trade only if ML + TA agree
        - Position size = 50%
        - Risk score +2
```

### 3. Circuit Breaker

Защита от rate limits:
```python
if api_error_count >= 3:
    circuit_breaker.open()  # Block AI calls for 15 min
    
# Auto-reset after cooldown
```

## Экономия API

### Старая архитектура
- Запросов в час: **120**
- Запросов в день: **2,880**
- Free Tier хватает на: **7-8 часов**

### Новая архитектура (Smart AI)
- ML Only (90%): **108 решений** → 0 API calls
- AI Confirmed (10%): **12 решений** → 12 API calls
- **Запросов в час: 12** (экономия 90%)
- **Запросов в день: 288**
- **Free Tier хватает на: 3+ дня** 🎉

## Параметры стратегии

### Aggressive Mode
```python
{
    'position_size_pct': 30,    # 30% баланса
    'max_risk': 7,              # Риск до 7/10
    'min_confidence': 0.60,     # AI: 60%, ML: 80%
    'stop_loss_pct': 2,         # -2%
    'take_profit_pct': 3        # +3%
}
```

### ML Thresholds
- **ML High Confidence**: ≥ 80% → Trade without AI
- **ML Low Confidence**: < 80% → Call AI
- **ML Prediction Change**: ≥ ±1.5% → BUY/SELL signal

### Safety Mode
- Активируется при недоступности AI
- Position size: **50%** от обычного
- Risk score: **+2** к базовому
- Торгуем только при согласии ML + TA

## Использование

### В коде
```python
from core.ai_brain_smart import get_smart_ai_brain

brain = get_smart_ai_brain()

result = await brain.decide_trade(market_data)

# result = {
#     'decision': 'BUY',
#     'confidence': 0.85,
#     'risk_score': 5,
#     'source': 'ML_ONLY',  # or 'AI_CONFIRMED' or 'SAFETY_MODE'
#     'reasoning': '...',
#     'position_size_multiplier': 1.0  # or 0.5 in Safety Mode
# }
```

### Тестирование
```bash
# На сервере
ssh root@88.210.10.145
cd /root/Bybit_Trader
docker exec -it bybit_trader python scripts/test_smart_ai.py
```

## Статистика

Smart AI Brain отслеживает:
- Total Decisions
- ML Only Decisions (💰 экономия)
- AI Confirmed Decisions
- Safety Mode Decisions
- API Calls Saved
- API Calls Made
- Circuit Breaker Status

```python
brain.print_stats()
# 📊 Smart AI Brain Statistics:
#    Total Decisions: 100
#    ML Only: 90 (90.0%) 💰
#    AI Confirmed: 8 (8.0%)
#    Safety Mode: 2 (2.0%)
#    API Calls Saved: 90 🎉
#    API Calls Made: 8
#    Circuit Breaker: 🟢 CLOSED
```

## Преимущества

✅ **Экономия API**: 90% запросов сохранено
✅ **Скорость**: Решения за миллисекунды (ML локально)
✅ **Надежность**: Fallback при недоступности AI
✅ **Защита**: Circuit Breaker от rate limits
✅ **Качество**: AI для сложных случаев

## Файлы

- `core/ai_brain_smart.py` - Smart AI Brain
- `core/loop.py` - Обновленный главный цикл
- `core/real_trader.py` - Обновленный трейдер
- `scripts/test_smart_ai.py` - Тесты
- `ml_data/models/price_predictor.pkl` - ML модель (требуется обучение)

## Обучение ML модели

```bash
# Локально или в Google Colab
jupyter notebook notebooks/train_ml_colab.ipynb

# Загрузить модель на сервер
scp ml_data/models/price_predictor.pkl root@88.210.10.145:/root/Bybit_Trader/ml_data/models/
```

## Мониторинг

Проверяй статистику в логах:
```
📊 Smart AI Brain Statistics:
   ML Only: 90 (90.0%) 💰  ← Хорошо!
   API Calls Saved: 90 🎉   ← Отлично!
   Circuit Breaker: 🟢      ← Все ОК
```

Если Circuit Breaker открыт:
```
🔴 Circuit Breaker OPEN - AI requests blocked for 15 min
```
→ Бот работает в Safety Mode, API восстановится автоматически
