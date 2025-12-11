# Интеграция Algion (GPTFree) - 11 декабря 2025

## Проблема

Gemini API часто исчерпывает лимиты (429 Too Many Requests), что приводит к:
- Strategic Brain не может обновить режим рынка
- Бот переходит в режим SIDEWAYS (по умолчанию)
- Теряется преимущество глобального анализа рынка

## Решение

Внедрён **Algion (GPTFree)** как бесплатный fallback для Gemini.

### Архитектура Fallback

```
Strategic Brain:
1. Gemini 2.5 Flash (основной)
   - Key #1 + Model #1 (gemini-2.5-flash)
   - Key #1 + Model #2 (gemini-2.5-flash-lite)
   - Key #2 + Model #1
   - Key #2 + Model #2
   ↓ (все комбинации исчерпаны)
2. Algion GPTFree (fallback)
   - gpt-4.1 (основная модель)
   - gpt-3.5-turbo (быстрая)
   - gpt-4o-mini (lite)
   ↓ (все модели исчерпаны)
3. SIDEWAYS (default режим)
```

## Что сделано

### 1. Создан Algion Client

**Файл:** `core/algion_client.py`

**Возможности:**
- ✅ Ротация моделей (gpt-4.1 → gpt-3.5-turbo → gpt-4o-mini)
- ✅ Обработка ошибок (429, 401, 403, 500+, timeout)
- ✅ Экспоненциальная задержка при ошибках сервера
- ✅ Статистика использования
- ✅ Singleton pattern

**Пример использования:**
```python
from core.algion_client import get_algion_client

client = get_algion_client()
result = client.generate_text(
    prompt="Analyze BTC market",
    system_prompt="You are a crypto analyst",
    temperature=0.7,
    max_tokens=2048
)
```

### 2. Обновлён Strategic Brain

**Файл:** `core/strategic_brain.py`

**Изменения:**
```python
# Добавлен импорт
from core.algion_client import get_algion_client

# Инициализация в __init__
self.algion_client = get_algion_client()

# Fallback в _call_gemini_api
if all Gemini combinations failed:
    return self._call_algion_api(prompt)

# Новый метод
def _call_algion_api(self, prompt: str) -> Optional[str]:
    # Адаптирует промпт для Algion
    # Вызывает Algion с ротацией моделей
    # Возвращает результат или None
```

**Логика работы:**
1. Пробует все комбинации Gemini (2 ключа × 2 модели = 4 попытки)
2. При исчерпании всех Gemini → вызывает Algion
3. Algion пробует 3 модели с ротацией
4. Если всё упало → возвращает None (режим SIDEWAYS)

### 3. Обновлён .env.example

**Добавлено:**
```env
# Algion (GPTFree) - Fallback для Gemini при исчерпании лимитов
# Бесплатный API для GPT моделей: https://algion.dev
# Получить токен: зарегистрируйтесь на сайте и создайте API key
ALGION_BEARER_TOKEN=your_algion_bearer_token_here
```

### 4. Создан тестовый скрипт

**Файл:** `test_algion.py`

**Тесты:**
- ✅ Простой запрос (hello world)
- ✅ Анализ рынка (как Strategic Brain)
- ✅ Ротация моделей
- ✅ Статистика использования

**Запуск:**
```bash
# Локально
python test_algion.py

# На сервере
docker exec bybit_bot python test_algion.py
```

## Deployment

### Шаг 1: Получить Algion токен

1. Перейти на https://algion.dev
2. Зарегистрироваться
3. Создать API Key
4. Скопировать Bearer токен

**Формат токена:**
```
algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI
```

### Шаг 2: Добавить токен в .env

**На сервере:**
```bash
ssh root@88.210.10.145
cd /root/Bybit_Trader
nano .env
```

**Добавить строку:**
```env
ALGION_BEARER_TOKEN=algion_x5_YOUR_TOKEN_HERE
```

### Шаг 3: Скопировать файлы

```bash
# Копируем новые файлы
scp Bybit_Trader/core/algion_client.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/core/strategic_brain.py root@88.210.10.145:/root/Bybit_Trader/core/
scp Bybit_Trader/test_algion.py root@88.210.10.145:/root/Bybit_Trader/
scp Bybit_Trader/.env.example root@88.210.10.145:/root/Bybit_Trader/
```

### Шаг 4: Пересобрать контейнер

```bash
# Пересобираем bot контейнер
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose build bot"

# Перезапускаем
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose stop bot"
ssh root@88.210.10.145 "docker rm -f bybit_bot"
ssh root@88.210.10.145 "cd /root/Bybit_Trader && docker-compose up -d bot"
```

### Шаг 5: Тестирование

```bash
# Тест Algion Client
ssh root@88.210.10.145 "docker exec bybit_bot python test_algion.py"

# Проверка логов Strategic Brain
ssh root@88.210.10.145 "docker logs bybit_bot --tail 100 | grep -E '(Strategic|Algion|Gemini)'"
```

## Проверка работы

### Логи при успешном Gemini

```
🧠 Strategic Brain: Updating regime...
   🔑 Using Key #1/2 + Model #1/2 (gemini-2.5-flash)...
   ✅ Gemini API success (Key #1 + Model #1)
   🎯 Strategic Regime: SIDEWAYS
```

### Логи при fallback на Algion

```
🧠 Strategic Brain: Updating regime...
   🔑 Using Key #1/2 + Model #1/2 (gemini-2.5-flash)...
   ⚠️  Key #1 + Model #1: Quota exceeded, switching...
   → Trying Model #2 on same key
   🔑 Using Key #1/2 + Model #2/2 (gemini-2.5-flash-lite)...
   ⚠️  Key #1 + Model #2: Quota exceeded, switching...
   → Switching to Key #2
   🔑 Using Key #2/2 + Model #1/2 (gemini-2.5-flash)...
   ⚠️  Key #2 + Model #1: Quota exceeded, switching...
   → Trying Model #2 on same key
   🔑 Using Key #2/2 + Model #2/2 (gemini-2.5-flash-lite)...
   ⚠️  Key #2 + Model #2: Quota exceeded, switching...
   ❌ All Gemini key+model combinations failed
   🔄 Trying Algion fallback...
   ✅ Algion (gpt-4.1): успешно
   ✅ Algion fallback success
   🎯 Strategic Regime: SIDEWAYS
```

### Логи при полном отказе

```
🧠 Strategic Brain: Updating regime...
   [... все Gemini попытки ...]
   ❌ All Gemini key+model combinations failed
   🔄 Trying Algion fallback...
   ⚠️ Algion (gpt-4.1): Rate limit (429)
   → Переключаемся на gpt-3.5-turbo
   ⚠️ Algion (gpt-3.5-turbo): Rate limit (429)
   → Переключаемся на gpt-4o-mini
   ⚠️ Algion (gpt-4o-mini): Rate limit (429)
   → Все модели Algion исчерпаны
   ❌ Algion fallback failed
   ⚠️  Strategic Brain: Failed to get regime, using cached: SIDEWAYS
```

## Статистика использования

### Algion Client

```python
from core.algion_client import get_algion_client

client = get_algion_client()
stats = client.get_stats()

# Результат:
{
    "total_requests": 15,
    "errors": 2,
    "rate_limits": 1,
    "success_rate": 86.7  # %
}
```

### Strategic Brain

Логи показывают:
- Сколько раз использовался Gemini
- Сколько раз использовался Algion
- Сколько раз fallback на SIDEWAYS

## Преимущества

### До интеграции:
- ❌ Gemini лимит → Strategic Brain отключается
- ❌ Режим SIDEWAYS по умолчанию
- ❌ Нет глобального анализа рынка

### После интеграции:
- ✅ Gemini лимит → Algion fallback
- ✅ Strategic Brain продолжает работать
- ✅ Глобальный анализ рынка сохраняется
- ✅ Бесплатный резервный канал

## Ограничения Algion

### Rate Limits:
- Есть лимиты запросов (429 ошибки)
- Скорость ответа варьируется
- Может быть нестабильным

### Решение:
- ✅ Ротация 3 моделей (увеличивает лимит)
- ✅ Экспоненциальная задержка при ошибках
- ✅ Graceful degradation на SIDEWAYS

## Мониторинг

### Проверка что Algion работает:

```bash
# Тест напрямую
docker exec bybit_bot python test_algion.py

# Проверка в логах бота
docker logs bybit_bot | grep -i algion

# Статистика Strategic Brain
docker logs bybit_bot | grep "Strategic Brain" | tail -20
```

### Алерты:

Если видите в логах:
- `❌ All Gemini key+model combinations failed` - Gemini исчерпан
- `🔄 Trying Algion fallback...` - Переключение на Algion
- `✅ Algion fallback success` - Algion работает
- `❌ Algion fallback failed` - Algion тоже исчерпан

## Рекомендации

### 1. Мониторить использование

Создать скрипт для проверки статистики:
```python
from core.algion_client import get_algion_client
from core.strategic_brain import get_strategic_brain

algion = get_algion_client()
brain = get_strategic_brain()

print("Algion stats:", algion.get_stats())
print("Current regime:", brain.current_regime)
```

### 2. Добавить несколько Algion токенов

Если один токен исчерпан, можно добавить ротацию:
```env
ALGION_BEARER_TOKEN_1=token1
ALGION_BEARER_TOKEN_2=token2
ALGION_BEARER_TOKEN_3=token3
```

### 3. Логировать в БД

Добавить таблицу для статистики AI провайдеров:
```sql
CREATE TABLE ai_provider_stats (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50),  -- 'gemini', 'algion'
    model VARCHAR(100),
    success BOOLEAN,
    error_code VARCHAR(10),
    response_time_ms INT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### Проблема: "ALGION_BEARER_TOKEN не установлен"

**Решение:**
```bash
# Проверить .env
cat /root/Bybit_Trader/.env | grep ALGION

# Добавить если нет
echo "ALGION_BEARER_TOKEN=your_token" >> /root/Bybit_Trader/.env

# Перезапустить контейнер
docker-compose restart bot
```

### Проблема: "401 Unauthorized"

**Причина:** Неверный токен

**Решение:**
1. Проверить токен на https://algion.dev
2. Создать новый токен
3. Обновить .env
4. Перезапустить контейнер

### Проблема: "429 Too Many Requests" на Algion

**Причина:** Исчерпан лимит Algion

**Решение:**
1. Подождать несколько минут
2. Или создать второй аккаунт Algion
3. Добавить второй токен в ротацию

---

**Дата:** 2025-12-11 15:30 UTC  
**Автор:** Kiro AI  
**Статус:** ✅ Готово к деплою
