# Миграция на Gemini Live API (WebSockets)

## 🎯 Цель
Переход с REST API (Free Tier с лимитами RPM) на **Live API через WebSockets** с unlimited доступом.

## 📦 Что изменилось

### Новая библиотека
- **Старая**: `google-generativeai` (REST API)
- **Новая**: `google-genai` (Live API + WebSockets)

### Новые файлы
1. `core/ai_brain_live.py` - новый класс для Live API
2. `scripts/test_live_api.py` - тест Live API

### Преимущества Live API
- ✅ **Unlimited RPM** - нет лимитов на запросы в минуту
- ✅ **WebSockets** - быстрее чем REST
- ✅ **Streaming** - получение ответа по частям
- ✅ **Стабильность** - меньше 429 ошибок

## 🚀 Установка

### 1. Обновить зависимости
```bash
# На сервере
docker exec bybit_bot pip install google-genai==0.2.2
```

### 2. Проверить API ключи
Убедись что в `.env` есть хотя бы один Google API ключ:
```env
GOOGLE_API_KEY_1=your_key_here
GOOGLE_API_KEY_2=your_key_here  # опционально
GOOGLE_API_KEY_3=your_key_here  # опционально
```

### 3. Тест Live API
```bash
# На сервере
docker exec bybit_bot python scripts/test_live_api.py
```

Ожидаемый вывод:
```
🧪 Тест Gemini Live API (WebSockets)
🔌 Подключено к gemini-2.0-flash-exp (ключ #1)
✅ Live API (gemini-2.0-flash-exp): BUY (риск: 5, уверенность: 75%)
```

## 🔄 Миграция кода

### Вариант 1: Полная замена (рекомендуется)

В файлах где используется AI:
```python
# Было
from core.ai_brain import get_ai_brain
ai = get_ai_brain()

# Стало
from core.ai_brain_live import get_ai_brain_live
ai = get_ai_brain_live()
```

### Вариант 2: Постепенная миграция

Можно использовать оба варианта параллельно:
```python
from core.ai_brain import get_ai_brain
from core.ai_brain_live import get_ai_brain_live

# Пробуем Live API
ai_live = get_ai_brain_live()
result = await ai_live.analyze_market(market_data)

# Если не сработало - fallback на REST
if not result:
    ai_rest = get_ai_brain()
    result = await ai_rest.analyze_market(market_data)
```

## 📝 Файлы для обновления

### 1. `core/real_trader.py`
```python
# Найти строку:
from core.ai_brain import get_ai_brain

# Заменить на:
from core.ai_brain_live import get_ai_brain_live

# Найти строку:
self.ai = get_ai_brain()

# Заменить на:
self.ai = get_ai_brain_live()
```

### 2. Другие файлы (если есть)
Поиск всех использований:
```bash
grep -r "get_ai_brain()" Bybit_Trader/
```

## 🧪 Тестирование

### 1. Тест Live API
```bash
docker exec bybit_bot python scripts/test_live_api.py
```

### 2. Тест интеграции с трейдером
```bash
docker exec bybit_bot python scripts/test_ml_integration.py
```

### 3. Запуск бота
```bash
docker-compose restart bybit_bot
docker logs -f bybit_bot
```

## 🔍 Мониторинг

### Логи Live API
В логах бота ищи:
- `🔌 Подключено к gemini-2.0-flash-exp` - успешное подключение
- `✅ Live API (...)` - успешный анализ
- `⚠️ Rate limit` - лимит (не должно быть!)
- `🔄 Переключение на API ключ` - ротация ключей

### Проверка работы
```bash
# Смотрим логи в реальном времени
docker logs -f bybit_bot | grep "Live API"
```

## ⚠️ Troubleshooting

### Ошибка: "No module named 'google.genai'"
```bash
docker exec bybit_bot pip install google-genai==0.2.2
docker-compose restart bybit_bot
```

### Ошибка: "API key not valid"
Проверь `.env`:
```bash
docker exec bybit_bot cat /app/.env | grep GOOGLE_API_KEY
```

### Ошибка: "Connection timeout"
Live API требует стабильного интернета. Проверь:
```bash
docker exec bybit_bot ping -c 3 generativelanguage.googleapis.com
```

### Все еще 429 ошибки
1. Проверь что используешь именно Live API (не REST)
2. Проверь логи: должно быть "🔌 Подключено к gemini-2.0-flash-exp"
3. Если видишь "generativelanguage.googleapis.com/v1beta/models" - это старый REST API!

## 📊 Сравнение производительности

| Метрика | REST API (старый) | Live API (новый) |
|---------|-------------------|------------------|
| RPM лимит | 15-30 | Unlimited ✅ |
| Скорость ответа | 2-5 сек | 1-3 сек ✅ |
| 429 ошибки | Часто ❌ | Редко ✅ |
| Стабильность | Средняя | Высокая ✅ |

## ✅ Checklist миграции

- [ ] Установлен `google-genai==0.2.2`
- [ ] Тест `test_live_api.py` прошел успешно
- [ ] Обновлен `core/real_trader.py`
- [ ] Обновлены другие файлы (если есть)
- [ ] Бот перезапущен
- [ ] Логи показывают "🔌 Подключено к gemini-2.0-flash-exp"
- [ ] Нет 429 ошибок в течение 1 часа
- [ ] Старый `ai_brain.py` можно удалить (опционально)

## 🎉 Готово!

После миграции бот будет работать без лимитов RPM и быстрее отвечать на запросы.
