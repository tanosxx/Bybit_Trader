"""
Algion (GPTFree) API Client
Бесплатный fallback для Gemini при исчерпании лимитов
"""
import httpx
import time
import os
from typing import Optional, List, Dict


class AlgionClient:
    """
    Клиент для работы с Algion API (GPTFree).
    Поддерживает ротацию моделей при ошибках.
    """
    
    def __init__(self, bearer_token: Optional[str] = None):
        """
        Инициализация клиента.
        
        Args:
            bearer_token: Bearer токен для авторизации (если None, берется из env)
        """
        self.bearer_token = bearer_token or os.getenv("ALGION_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("ALGION_BEARER_TOKEN не установлен")
        
        self.base_url = "https://api.algion.dev/v1"
        
        # Модели в порядке приоритета (от лучшей к быстрой)
        self.models = ["gpt-4.1", "gpt-3.5-turbo", "gpt-4o-mini"]
        self.current_model_index = 0
        
        # Статистика
        self.requests_count = 0
        self.errors_count = 0
        self.rate_limits_count = 0
        
        # HTTP клиент
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def _get_current_model(self) -> str:
        """Получает текущую модель."""
        return self.models[self.current_model_index]
    
    def _rotate_model(self) -> bool:
        """
        Переключается на следующую модель.
        
        Returns:
            bool: True если есть следующая модель, False если все исчерпаны
        """
        self.current_model_index += 1
        if self.current_model_index >= len(self.models):
            self.current_model_index = 0  # Сбрасываем для следующего раза
            return False
        return True
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Генерирует текст через Algion API с автоматической ротацией моделей.
        
        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт (опционально)
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов
            max_retries: Максимальное количество попыток
            
        Returns:
            str: Сгенерированный текст или None при ошибке
        """
        attempts = 0
        
        while attempts < max_retries:
            current_model = self._get_current_model()
            
            try:
                # Формируем сообщения
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Формируем запрос
                payload = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Выполняем запрос
                response = self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                
                # Проверяем статус
                response.raise_for_status()
                
                # Парсим ответ
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                
                # Успех!
                self.requests_count += 1
                print(f"✅ Algion ({current_model}): успешно")
                return result
                
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                
                if status_code == 429:
                    # Rate limit - переключаемся на следующую модель
                    self.rate_limits_count += 1
                    print(f"⚠️ Algion ({current_model}): Rate limit (429)")
                    
                    if self._rotate_model():
                        print(f"   → Переключаемся на {self._get_current_model()}")
                        attempts += 1
                        continue
                    else:
                        print(f"   → Все модели Algion исчерпаны")
                        self.errors_count += 1
                        return None
                
                elif status_code in [401, 403]:
                    # Ошибка авторизации - не повторяем
                    print(f"❌ Algion: Ошибка авторизации ({status_code})")
                    print(f"   Проверьте ALGION_BEARER_TOKEN")
                    self.errors_count += 1
                    return None
                
                elif status_code >= 500:
                    # Ошибка сервера - повторяем с задержкой
                    print(f"⚠️ Algion ({current_model}): Ошибка сервера ({status_code})")
                    attempts += 1
                    if attempts < max_retries:
                        wait_time = 2 ** attempts  # Экспоненциальная задержка
                        print(f"   → Повтор через {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.errors_count += 1
                        return None
                
                else:
                    # Другие ошибки
                    print(f"❌ Algion ({current_model}): HTTP {status_code}")
                    print(f"   {e.response.text[:200]}")
                    self.errors_count += 1
                    return None
            
            except httpx.TimeoutException:
                # Таймаут - повторяем
                print(f"⚠️ Algion ({current_model}): Таймаут")
                attempts += 1
                if attempts < max_retries:
                    print(f"   → Повтор {attempts}/{max_retries}...")
                    time.sleep(1)
                    continue
                else:
                    self.errors_count += 1
                    return None
            
            except Exception as e:
                # Неожиданная ошибка
                print(f"❌ Algion ({current_model}): {type(e).__name__}: {str(e)}")
                self.errors_count += 1
                return None
        
        # Все попытки исчерпаны
        self.errors_count += 1
        return None
    
    def get_stats(self) -> Dict[str, any]:
        """
        Получает статистику использования.
        
        Returns:
            dict: Статистика запросов
        """
        success_rate = 0.0
        if self.requests_count > 0:
            success_rate = (self.requests_count - self.errors_count) / self.requests_count
        
        return {
            "total_requests": self.requests_count,
            "errors": self.errors_count,
            "rate_limits": self.rate_limits_count,
            "success_rate": round(success_rate * 100, 1)
        }
    
    def __del__(self):
        """Закрывает HTTP клиент при удалении объекта."""
        try:
            self.client.close()
        except:
            pass


# Singleton instance
_algion_client = None


def get_algion_client() -> AlgionClient:
    """
    Получает singleton instance AlgionClient.
    
    Returns:
        AlgionClient: Клиент Algion API
    """
    global _algion_client
    if _algion_client is None:
        try:
            _algion_client = AlgionClient()
            print("🚀 Algion Client initialized")
        except ValueError as e:
            print(f"⚠️ Algion Client не инициализирован: {e}")
            return None
    return _algion_client


# Пример использования
if __name__ == "__main__":
    # Тестирование клиента
    client = get_algion_client()
    
    if client:
        print("\n" + "="*60)
        print("Тестирование Algion Client")
        print("="*60)
        
        # Тест 1: Простой запрос
        print("\n📝 Тест 1: Простой запрос")
        result = client.generate_text(
            "Напиши короткое приветствие для торгового бота.",
            system_prompt="Ты - профессиональный копирайтер."
        )
        if result:
            print(f"Результат: {result[:100]}...")
        
        # Тест 2: Анализ рынка
        print("\n📊 Тест 2: Анализ рынка")
        result = client.generate_text(
            "BTC цена $90,000. RSI=65, MACD=bullish. Что делать?",
            system_prompt="Ты - эксперт по криптовалютам. Отвечай кратко."
        )
        if result:
            print(f"Результат: {result[:100]}...")
        
        # Статистика
        print("\n📊 Статистика:")
        stats = client.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n" + "="*60)
