"""
AI Gateway Client - OpenAI-compatible API для Bybit Trader
Unified LLM provider для Strategic Brain
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIGatewayClient:
    """Клиент для работы с AI Gateway (OpenAI-compatible)"""
    
    def __init__(self):
        """Инициализация AI Gateway клиента"""
        # API endpoint и ключ
        self.base_url = os.getenv("AI_GATEWAY_URL", "https://ai.stashiq.online")
        self.api_key = os.getenv("AI_GATEWAY_KEY")
        
        if not self.api_key:
            raise ValueError("AI_GATEWAY_KEY not found in environment")
        
        # Headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Модель (auto = автоматический выбор лучшей доступной)
        self.model = "auto"
        
        print(f"✅ AI Gateway Client initialized (endpoint: {self.base_url})")
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Генерация текста с помощью AI Gateway
        
        Args:
            prompt: Основной промпт
            system_prompt: Системный промпт (опционально)
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимальное количество токенов
            
        Returns:
            Сгенерированный текст или None при ошибке
        """
        try:
            # Формируем messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Запрос к API
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Проверяем статус
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                model_used = data.get("model", "unknown")
                
                print(f"✅ AI Gateway ({model_used}): успешно")
                return content.strip()
            
            elif response.status_code == 401:
                print("❌ AI Gateway: Invalid or missing token")
                return None
            
            elif response.status_code == 429:
                print("⚠️ AI Gateway: Rate limit exceeded")
                return None
            
            elif response.status_code == 503:
                print("⚠️ AI Gateway: No healthy models available")
                return None
            
            else:
                print(f"❌ AI Gateway error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ AI Gateway: Request timeout")
            return None
        except Exception as e:
            print(f"❌ AI Gateway error: {e}")
            return None


# Singleton
_ai_gateway_client = None


def get_ai_gateway_client() -> AIGatewayClient:
    """Получить singleton AI Gateway клиента"""
    global _ai_gateway_client
    if _ai_gateway_client is None:
        _ai_gateway_client = AIGatewayClient()
    return _ai_gateway_client
