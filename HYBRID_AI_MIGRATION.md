# Миграция на Гибридный AI Brain (ML-First)

## 🎯 Цель
Экономия API запросов через приоритет локальной ML модели и жёсткий rate limiting.

## 📦 Что изменилось

### Новая архитектура
```
┌─────────────────────────────────────┐
│   Гибридный AI Brain (ML-First)    │
├─────────────────────────────────────┤
│ 1. Кэш (если цена не изменилась)   │
│ 2. ML модель (если уверенность>80%)│
│ 3. Gemini API (только спорные)      │
│ 4. ML Fallback (если API недоступен)│
└─────────────────────────────────────┘
```

### Защита от спама
- ✅ **Circuit Breaker**: 5 минут заморозки после 429 ошибки
- ✅ **Rate Limiter**: Минимум 20 секунд между запросами
- ✅ **Кэш**: Повторное использование если цена изменилась < 0.1%
- ✅ **ML-First**: API запрос только если ML уверенность < 80%

### Экономия
- 🎯 **80%+ решений через ML** (без API запросов!)
- 🎯 **Кэш хиты** при незначительных изменениях цены
- 🎯 **Нет бесконечных циклов** благодаря Circuit Breaker

## 🚀 Установка

### 1. Загрузить ML модель
```bash
# Скопируй обученную модель из Google Colab в:
# ml_training/models/random_forest_model.pkl
# ml_training/models/scaler.pkl

# На сервере:
scp random_forest_model.pkl root@88.210.10.145:/root/Bybit_Trader/ml_training/models/
scp scaler.pkl root@88.210.10.145:/root/Bybit_Trader/ml_training/models/
```

### 2. Обновить код
В файлах где используется AI (например `core/real_trader.py`):

```python
# Было:
from core.ai_brain import get_ai_brain
ai = get_ai_brain()

# Стало:
from core.ai_brain_hybrid import get_ai_brain_hybrid
ai = get_ai_brain_hybrid()
```

### 3. Тест
```bash
# Локально (без Docker):
python Bybit_Trader/scripts/test_hybrid_ai.py

# На сервере:
docker exec bybit_bot python scripts/test_hybrid_ai.py
```

## 📊 Как это работает

### Сценарий 1: ML уверенность высокая (>80%)
```
Запрос → ML модель → Уверенность 85% → ✅ Решение БЕЗ API!
```
**Экономия: 1 API запрос**

### Сценарий 2: ML уверенность средняя (50-80%)
```
Запрос → ML модель → Уверенность 65% → Gemini API → Комбинированное решение
```
**API запрос: 1 (но с rate limiting)**

### Сценарий 3: Цена не изменилась
```
Запрос → Кэш → ✅ Старое решение
```
**Экономия: 1 API запрос + 1 ML предсказание**

### Сценарий 4: 429 ошибка
```
Запрос → Gemini API → 429 Error → Circuit Breaker открыт на 5 минут
Следующие запросы → ML модель (fallback)
```
**Защита: Нет спама API**

## 🔧 Настройки

В `core/ai_brain_hybrid.py`:

```python
# Circuit Breaker
CircuitBreaker(cooldown_seconds=300)  # 5 минут заморозки

# Rate Limiter
RateLimiter(min_interval_seconds=20)  # 20 секунд между запросами

# Кэш
ResponseCache(ttl_seconds=60)  # 1 минута TTL

# ML порог
if confidence >= 0.80:  # 80% уверенность = не спрашиваем API
```

## 📈 Мониторинг

### Статистика
```python
ai = get_ai_brain_hybrid()
ai.print_stats()
```

Вывод:
```
📊 Статистика AI Brain:
   ML решений: 45
   API запросов: 5
   Кэш хитов: 12
   Circuit breaker блоков: 2
   ML использование: 90.0%
   💰 Экономия API: 45 запросов!
```

### Логи
Ищи в логах:
- `🤖 ML: BUY (уверенность: 85%)` - ML предсказание
- `✅ ML решение принято БЕЗ API запроса!` - экономия
- `💾 Кэш: цена изменилась на 0.05%` - кэш хит
- `🔴 Circuit Breaker ОТКРЫТ!` - защита от спама
- `⏱️ Rate limit: подожди 15.3с` - троттлинг

## ⚠️ Важно

### ML модель обязательна!
Без ML модели бот будет работать только через API (как раньше).

Проверь что модель загружена:
```bash
ls -lh ml_training/models/
# Должны быть:
# random_forest_model.pkl
# scaler.pkl
```

### Формат фичей
ML модель ожидает эти поля в `market_data`:
- `price`
- `rsi`
- `macd` (dict с value, signal, histogram)
- `bollinger_bands` (dict с upper, middle, lower)
- `stochastic` (dict с k, d)
- `volume_24h`
- `price_change_24h`

## 🎉 Результат

После миграции:
- ✅ **80-90% решений через ML** (без API)
- ✅ **Нет 429 ошибок** (Circuit Breaker)
- ✅ **Нет спама** (Rate Limiter)
- ✅ **Быстрее** (кэш + локальная ML)
- ✅ **Дешевле** (экономия API квот)

## 🔄 Откат

Если что-то пошло не так:
```python
# Вернись на старый AI Brain:
from core.ai_brain import get_ai_brain
ai = get_ai_brain()
```

Старый код остался в `core/ai_brain.py`.
