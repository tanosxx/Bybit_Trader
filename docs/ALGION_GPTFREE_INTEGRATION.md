# Интеграция с Algion (GPTFree) API

## Описание сервиса

**Algion** (также известный как **GPTFree**) - это бесплатный API для доступа к различным AI моделям, включая GPT-3.5-turbo, GPT-4 и другие.

### Основная информация

- **Официальный сайт**: https://algion.dev
- **GitHub проекта**: https://github.com/Mr-Abood/GPTFree
- **Базовый URL API**: `https://api.algion.dev/v1`
- **Тип авторизации**: Bearer Token
- **Формат API**: OpenAI-совместимый
- **Стоимость**: Бесплатно (с лимитами)

### Особенности

✅ **Преимущества:**
- Бесплатный доступ к мощным моделям
- OpenAI-совместимый API (легко интегрировать)
- Поддержка нескольких моделей
- Не требует кредитной карты

⚠️ **Ограничения:**
- Может быть нестабильным (новый проект)
- Есть rate limits (лимиты запросов)
- Требуется Bearer токен для авторизации
- Скорость ответа может варьироваться

---

## Получение Bearer токена

### Шаг 1: Регистрация

1. Перейдите на https://algion.dev
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в раздел API Keys / Tokens

### Шаг 2: Создание токена

1. Нажмите "Create New Token" или "Generate API Key"
2. Скопируйте сгенерированный Bearer токен
3. Сохраните токен в безопасном месте

**Пример токена:**
```
algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI
```

⚠️ **ВАЖНО**: Никогда не коммитьте токен в git! Используйте переменные окружения или конфигурационные файлы.

---

## Доступные модели

Algion предоставляет доступ к следующим моделям:

| Модель | Описание | Рекомендуется |
|--------|----------|---------------|
| `gpt-4.1` | Основная модель Algion (оптимизированная) | ✅ Да |
| `gpt-3.5-turbo` | Быстрая модель для простых задач | ✅ Да |
| `gpt-4` | Мощная модель для сложных задач | ⚠️ Может быть медленнее |
| `gpt-4o-mini` | Облегченная версия GPT-4 | ✅ Да |

**Рекомендация**: Начните с `gpt-4.1` - это основная модель сервиса с лучшим балансом скорости и качества.

---

## API Endpoints

### 1. Chat Completions (Генерация текста)

**Endpoint:** `POST https://api.algion.dev/v1/chat/completions`

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gpt-4.1",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4.1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 25,
    "total_tokens": 45
  }
}
```

---

## Примеры интеграции

### Python (с httpx)

```python
import httpx
import json

# Конфигурация
BEARER_TOKEN = "algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI"
BASE_URL = "https://api.algion.dev/v1"

# Создаем HTTP клиент
client = httpx.Client(
    headers={
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    },
    timeout=30.0
)

# Функция для генерации текста
def generate_text(prompt, system_prompt=None, model="gpt-4.1"):
    """
    Генерирует текст через Algion API.
    
    Args:
        prompt: Пользовательский промпт
        system_prompt: Системный промпт (опционально)
        model: Название модели
        
    Returns:
        str: Сгенерированный текст
    """
    # Формируем сообщения
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Формируем запрос
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    # Выполняем запрос
    response = client.post(
        f"{BASE_URL}/chat/completions",
        json=payload
    )
    
    # Проверяем статус
    response.raise_for_status()
    
    # Парсим ответ
    data = response.json()
    return data["choices"][0]["message"]["content"]

# Пример использования
if __name__ == "__main__":
    system_prompt = "Ты - профессиональный копирайтер."
    user_prompt = "Напиши короткую статью о пользе чтения книг."
    
    try:
        result = generate_text(user_prompt, system_prompt)
        print("Результат:")
        print(result)
    except httpx.HTTPStatusError as e:
        print(f"HTTP ошибка: {e.response.status_code}")
        print(f"Ответ: {e.response.text}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")
```

### Python (асинхронный с httpx)

```python
import httpx
import asyncio

BEARER_TOKEN = "algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI"
BASE_URL = "https://api.algion.dev/v1"

async def generate_text_async(prompt, system_prompt=None, model="gpt-4.1"):
    """
    Асинхронная генерация текста через Algion API.
    """
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Content-Type": "application/json"
        },
        timeout=30.0
    ) as client:
        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Формируем запрос
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        # Выполняем запрос
        response = await client.post(
            f"{BASE_URL}/chat/completions",
            json=payload
        )
        
        response.raise_for_status()
        
        # Парсим ответ
        data = response.json()
        return data["choices"][0]["message"]["content"]

# Пример использования
async def main():
    result = await generate_text_async(
        "Напиши короткую статью о пользе чтения книг.",
        "Ты - профессиональный копирайтер."
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript (Node.js с axios)

```javascript
const axios = require('axios');

// Конфигурация
const BEARER_TOKEN = 'algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI';
const BASE_URL = 'https://api.algion.dev/v1';

// Функция для генерации текста
async function generateText(prompt, systemPrompt = null, model = 'gpt-4.1') {
  // Формируем сообщения
  const messages = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }
  messages.push({ role: 'user', content: prompt });
  
  // Выполняем запрос
  try {
    const response = await axios.post(
      `${BASE_URL}/chat/completions`,
      {
        model: model,
        messages: messages,
        temperature: 0.7,
        max_tokens: 2048
      },
      {
        headers: {
          'Authorization': `Bearer ${BEARER_TOKEN}`,
          'Content-Type': 'application/json'
        },
        timeout: 30000
      }
    );
    
    return response.data.choices[0].message.content;
  } catch (error) {
    if (error.response) {
      console.error(`HTTP ошибка: ${error.response.status}`);
      console.error(`Ответ: ${JSON.stringify(error.response.data)}`);
    } else {
      console.error(`Ошибка: ${error.message}`);
    }
    throw error;
  }
}

// Пример использования
(async () => {
  const systemPrompt = 'Ты - профессиональный копирайтер.';
  const userPrompt = 'Напиши короткую статью о пользе чтения книг.';
  
  try {
    const result = await generateText(userPrompt, systemPrompt);
    console.log('Результат:');
    console.log(result);
  } catch (error) {
    console.error('Не удалось сгенерировать текст');
  }
})();
```

### cURL (для тестирования)

```bash
curl -X POST https://api.algion.dev/v1/chat/completions \
  -H "Authorization: Bearer algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1",
    "messages": [
      {
        "role": "system",
        "content": "Ты - профессиональный копирайтер."
      },
      {
        "role": "user",
        "content": "Напиши короткую статью о пользе чтения книг."
      }
    ],
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

---

## Обработка ошибок

### Коды ошибок HTTP

| Код | Описание | Решение |
|-----|----------|---------|
| `401` | Unauthorized - неверный токен | Проверьте Bearer токен |
| `403` | Forbidden - доступ запрещен | Проверьте права токена |
| `404` | Not Found - модель не найдена | Используйте другую модель |
| `429` | Too Many Requests - лимит запросов | Подождите или используйте другую модель |
| `500` | Internal Server Error - ошибка сервера | Повторите запрос позже |
| `503` | Service Unavailable - сервис недоступен | Повторите запрос позже |

### Пример обработки ошибок

```python
import httpx
import time

def generate_with_retry(prompt, max_retries=3):
    """
    Генерирует текст с повторными попытками при ошибках.
    """
    for attempt in range(max_retries):
        try:
            return generate_text(prompt)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            
            if status_code == 429:
                # Rate limit - ждем и повторяем
                wait_time = 2 ** attempt  # Экспоненциальная задержка
                print(f"Rate limit. Ожидание {wait_time}s...")
                time.sleep(wait_time)
                continue
            elif status_code in [401, 403]:
                # Ошибка авторизации - не повторяем
                print("Ошибка авторизации. Проверьте токен.")
                raise
            elif status_code >= 500:
                # Ошибка сервера - повторяем
                print(f"Ошибка сервера {status_code}. Повтор...")
                time.sleep(1)
                continue
            else:
                # Другие ошибки
                raise
        except httpx.TimeoutException:
            # Таймаут - повторяем
            print(f"Таймаут. Повтор {attempt + 1}/{max_retries}...")
            time.sleep(1)
            continue
    
    raise Exception(f"Не удалось выполнить запрос после {max_retries} попыток")
```

---

## Ротация моделей

Для повышения надежности рекомендуется использовать ротацию моделей при ошибках:

```python
class AlgionClient:
    """Клиент с ротацией моделей."""
    
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.base_url = "https://api.algion.dev/v1"
        self.models = ["gpt-4.1", "gpt-3.5-turbo", "gpt-4o-mini"]
        self.current_model_index = 0
        
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def _get_current_model(self):
        """Получает текущую модель."""
        return self.models[self.current_model_index]
    
    def _rotate_model(self):
        """Переключается на следующую модель."""
        self.current_model_index += 1
        if self.current_model_index >= len(self.models):
            return False  # Все модели исчерпаны
        return True
    
    def generate_text(self, prompt, system_prompt=None):
        """
        Генерирует текст с автоматической ротацией моделей.
        """
        attempts = 0
        max_attempts = len(self.models)
        
        while attempts < max_attempts:
            current_model = self._get_current_model()
            
            try:
                # Формируем запрос
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
                
                # Выполняем запрос
                response = self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                
                response.raise_for_status()
                
                # Успех!
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit - переключаемся на следующую модель
                    print(f"Rate limit для {current_model}, переключаемся...")
                    attempts += 1
                    if not self._rotate_model():
                        raise Exception("Все модели исчерпаны")
                else:
                    raise
        
        raise Exception("Не удалось сгенерировать текст")

# Использование
client = AlgionClient("algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI")
result = client.generate_text("Напиши статью о Python")
```

---

## Конфигурация для разных проектов

### Переменные окружения (.env)

```env
# Algion (GPTFree) API
ALGION_BEARER_TOKEN=algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI
ALGION_BASE_URL=https://api.algion.dev/v1
ALGION_DEFAULT_MODEL=gpt-4.1
ALGION_TEMPERATURE=0.7
ALGION_MAX_TOKENS=2048
ALGION_TIMEOUT=30
```

### JSON конфигурация

```json
{
  "algion": {
    "bearer_token": "algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI",
    "base_url": "https://api.algion.dev/v1",
    "models": [
      "gpt-4.1",
      "gpt-3.5-turbo",
      "gpt-4o-mini"
    ],
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout": 30
  }
}
```

### YAML конфигурация

```yaml
algion:
  bearer_token: algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI
  base_url: https://api.algion.dev/v1
  models:
    - gpt-4.1
    - gpt-3.5-turbo
    - gpt-4o-mini
  temperature: 0.7
  max_tokens: 2048
  timeout: 30
```

---

## Best Practices (Лучшие практики)

### 1. Безопасность токена

❌ **НЕ ДЕЛАЙТЕ ТАК:**
```python
# Хардкод токена в коде
bearer_token = "algion_x5_5Y3PSIgoHiiP5I4tn4jU_DRoVJgA1DzAZFVKxaGI"
```

✅ **ДЕЛАЙТЕ ТАК:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
bearer_token = os.getenv("ALGION_BEARER_TOKEN")

if not bearer_token:
    raise ValueError("ALGION_BEARER_TOKEN не установлен")
```

### 2. Обработка ошибок

Всегда обрабатывайте возможные ошибки:
- Rate limits (429)
- Ошибки авторизации (401, 403)
- Таймауты
- Ошибки сервера (500+)

### 3. Логирование

Логируйте все запросы для отладки:

```python
import logging

logger = logging.getLogger(__name__)

def generate_text(prompt):
    logger.info(f"Генерация текста, промпт: {prompt[:50]}...")
    try:
        result = # ... ваш код
        logger.info("Текст успешно сгенерирован")
        return result
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}", exc_info=True)
        raise
```

### 4. Кэширование

Кэшируйте результаты для одинаковых промптов:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def generate_text_cached(prompt, system_prompt=None):
    return generate_text(prompt, system_prompt)
```

### 5. Мониторинг использования

Отслеживайте использование API:

```python
class AlgionMonitor:
    def __init__(self):
        self.requests_count = 0
        self.errors_count = 0
        self.rate_limits_count = 0
    
    def log_request(self, success=True, is_rate_limit=False):
        self.requests_count += 1
        if not success:
            self.errors_count += 1
        if is_rate_limit:
            self.rate_limits_count += 1
    
    def get_stats(self):
        return {
            "total_requests": self.requests_count,
            "errors": self.errors_count,
            "rate_limits": self.rate_limits_count,
            "success_rate": (self.requests_count - self.errors_count) / self.requests_count if self.requests_count > 0 else 0
        }
```

---

## Troubleshooting (Решение проблем)

### Проблема: "401 Unauthorized"

**Причина**: Неверный Bearer токен

**Решение**:
1. Проверьте что токен скопирован полностью
2. Убедитесь что токен не истек
3. Проверьте что токен передается в заголовке `Authorization: Bearer YOUR_TOKEN`

### Проблема: "429 Too Many Requests"

**Причина**: Превышен лимит запросов

**Решение**:
1. Подождите несколько секунд перед следующим запросом
2. Используйте ротацию моделей
3. Реализуйте экспоненциальную задержку (exponential backoff)

### Проблема: Медленные ответы

**Причина**: Высокая нагрузка на сервис или сложный промпт

**Решение**:
1. Используйте более быструю модель (`gpt-3.5-turbo` вместо `gpt-4`)
2. Уменьшите `max_tokens`
3. Упростите промпт
4. Увеличьте `timeout`

### Проблема: Некорректные ответы

**Причина**: Неправильный промпт или температура

**Решение**:
1. Улучшите системный промпт
2. Уменьшите `temperature` для более предсказуемых ответов
3. Добавьте примеры в промпт (few-shot learning)

---

## Дополнительные ресурсы

- **Официальная документация**: https://algion.dev/docs
- **GitHub**: https://github.com/Mr-Abood/GPTFree
- **Сообщество**: https://discord.gg/gptfree (если есть)
- **Статус сервиса**: https://status.algion.dev (если есть)

---

## Заключение

Algion (GPTFree) - отличный выбор для:
- Прототипирования AI приложений
- Тестирования промптов
- Небольших проектов с ограниченным бюджетом
- Обучения работе с AI API

Для production проектов с высокой нагрузкой рекомендуется:
- Использовать несколько провайдеров (fallback)
- Мониторить использование и ошибки
- Иметь план B (другой AI провайдер)

**Удачи в интеграции! 🚀**
