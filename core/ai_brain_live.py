"""
AI Brain для анализа крипто рынков через Gemini Live API (WebSockets)
Использует новую библиотеку google-genai с unlimited RPM через WebSocket
"""
import json
import asyncio
from typing import Dict, Optional
from google import genai
from google.genai import types
from config import settings


class AIBrainLive:
    """AI анализ через Gemini Live API (WebSockets) - UNLIMITED RPM"""
    
    def __init__(self):
        # API ключи для ротации
        self.google_api_keys = [
            settings.google_api_key_1,
            settings.google_api_key_2,
            settings.google_api_key_3,
        ]
        self.google_api_keys = [k for k in self.google_api_keys if k]
        self.current_key_index = 0
        
        # Модели Live API (технический ID для WebSocket через v1alpha)
        # gemini-2.0-flash-live в интерфейсе = gemini-2.0-flash-exp в коде!
        self.live_models = [
            "gemini-2.0-flash-exp",  # Основная Live модель (Unlimited через WebSocket!)
            "models/gemini-2.0-flash-exp",  # Альтернативный формат
        ]
        self.current_model_index = 0
    
    def _get_client(self) -> genai.Client:
        """Получить или создать клиент с текущим API ключом (v1alpha для Live API!)"""
        api_key = self.google_api_keys[self.current_key_index]
        # ВАЖНО: Live API доступен только в v1alpha!
        return genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )
    
    def _rotate_key(self):
        """Переключиться на следующий API ключ"""
        self.current_key_index = (self.current_key_index + 1) % len(self.google_api_keys)
        print(f"🔄 Переключение на API ключ #{self.current_key_index + 1}")
    
    def _rotate_model(self):
        """Переключиться на следующую модель"""
        self.current_model_index = (self.current_model_index + 1) % len(self.live_models)
        print(f"🔄 Переключение на модель: {self.live_models[self.current_model_index]}")
    
    async def _send_and_receive(self, session, prompt: str) -> Optional[str]:
        """
        Отправить сообщение и получить ответ через Live API WebSocket
        
        Args:
            session: Активная Live WebSocket сессия
            prompt: Текст запроса
        
        Returns:
            Полный текстовый ответ или None
        """
        try:
            # Отправляем сообщение через WebSocket
            await session.send(prompt, end_of_turn=True)
            
            # Собираем ответ из чанков (streaming)
            full_response = ""
            
            async for response in session.receive():
                # Проверяем наличие текста в ответе
                if hasattr(response, 'text') and response.text:
                    full_response += response.text
                
                # Проверяем server_content (альтернативный формат)
                elif hasattr(response, 'server_content'):
                    if hasattr(response.server_content, 'model_turn'):
                        for part in response.server_content.model_turn.parts:
                            if hasattr(part, 'text') and part.text:
                                full_response += part.text
                
                # Если получили turn_complete - ответ завершен
                if hasattr(response, 'server_content'):
                    if hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete:
                        break
            
            return full_response.strip() if full_response else None
        
        except Exception as e:
            print(f"❌ Ошибка при отправке/получении через WebSocket: {e}")
            return None
    
    async def _call_live_api(self, market_data: Dict) -> Optional[Dict]:
        """
        Вызов Gemini Live API через WebSocket (UNLIMITED RPM!)
        
        Args:
            market_data: Данные рынка для анализа
        
        Returns:
            Результат анализа в формате JSON или None
        """
        # Формируем промпт
        prompt = f"""Ты профессиональный криптотрейдер. Проанализируй рынок и дай рекомендацию.

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО валидным JSON
2. БЕЗ объяснений, БЕЗ markdown, БЕЗ блоков кода
3. Будь решительным - выбирай BUY (покупка), SELL (продажа) или SKIP (пропустить)
4. Оценка риска: 1 (безопасно) до 10 (очень рискованно)
5. ВАЖНО: Рассматривай как LONG (покупка), так и SHORT (продажа) позиции!
6. SHORT позиции выгодны при падении цены - не бойся их использовать!

Данные рынка:
{json.dumps(market_data, indent=2)}

Отвечай ТОЧНО в таком JSON формате:
{{
  "decision": "BUY" или "SELL" или "SKIP",
  "risk_score": 1-10,
  "confidence": 0.0-1.0,
  "reasoning": "краткое объяснение на русском в 1-2 предложениях",
  "key_factors": ["фактор1", "фактор2", "фактор3"]
}}

JSON ответ:"""
        
        # Пробуем все комбинации ключей и моделей
        for key_attempt in range(len(self.google_api_keys)):
            client = self._get_client()
            
            for model_attempt in range(len(self.live_models)):
                model_name = self.live_models[self.current_model_index]
                
                try:
                    # Конфигурация Live API - ТОЛЬКО ТЕКСТ через WebSocket
                    config = types.LiveConnectConfig(
                        response_modalities=["TEXT"],  # Только текст, без аудио!
                    )
                    
                    # Открываем WebSocket сессию (UNLIMITED RPM!)
                    async with client.aio.live.connect(
                        model=model_name,
                        config=config
                    ) as session:
                        print(f"🔌 WebSocket подключен к {model_name} (ключ #{self.current_key_index + 1})")
                        
                        # Отправляем и получаем ответ через WebSocket
                        response_text = await self._send_and_receive(session, prompt)
                        
                        if not response_text:
                            print(f"⚠️ Пустой ответ от {model_name}")
                            self._rotate_model()
                            continue
                        
                        # Очищаем от markdown
                        text = response_text.strip()
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.startswith("```"):
                            text = text[3:]
                        if text.endswith("```"):
                            text = text[:-3]
                        text = text.strip()
                        
                        # Находим JSON
                        start = text.find('{')
                        end = text.rfind('}')
                        if start != -1 and end != -1:
                            text = text[start:end+1]
                        
                        # Парсим JSON
                        result = json.loads(text)
                        
                        # Валидация
                        if not all(k in result for k in ["decision", "risk_score", "confidence"]):
                            print(f"⚠️ Неполный JSON от {model_name}")
                            self._rotate_model()
                            continue
                        
                        print(f"✅ Live API WebSocket ({model_name}): {result['decision']} (риск: {result['risk_score']}, уверенность: {result['confidence']:.0%})")
                        
                        return result
                
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error ({model_name}): {e}")
                    print(f"Response: {response_text[:200] if response_text else 'None'}")
                    self._rotate_model()
                    continue
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # Выводим полную ошибку для диагностики
                    print(f"❌ Полная ошибка ({model_name}): {error_msg}")
                    
                    # Проверяем на rate limit (не должно быть на WebSocket!)
                    if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                        print(f"⚠️ Rate limit на {model_name}")
                        self._rotate_model()
                        continue
                    
                    # Проверяем на отсутствие доступа к Live API
                    if "not found" in error_msg.lower() or "not available" in error_msg.lower():
                        print(f"⚠️ Live API недоступен для {model_name} (нужна активация)")
                        self._rotate_model()
                        continue
                    
                    # Другая ошибка
                    print(f"❌ Ошибка Live API WebSocket ({model_name}): {e}")
                    self._rotate_model()
                    continue
            
            # Все модели с этим ключом исчерпаны
            print(f"⚠️ Все модели с ключом #{self.current_key_index + 1} недоступны")
            self._rotate_key()
        
        # Все ключи и модели исчерпаны
        print(f"❌ Live API WebSocket недоступен (возможно требуется активация)")
        return None
    
    async def analyze_market(self, market_data: Dict) -> Optional[Dict]:
        """
        Анализ рынка через Gemini Live API WebSocket (UNLIMITED RPM!)
        
        Args:
            market_data: {
                "symbol": "BTCUSDT",
                "price": 43250.50,
                "rsi": 32.5,
                "macd": {...},
                "bollinger_bands": {...},
                "trend": "uptrend",
                "volume_trend": "increasing",
                "signal": "BUY"
            }
        
        Returns:
            {
                "decision": "BUY/SELL/SKIP",
                "risk_score": 1-10,
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "key_factors": [...]
            }
        """
        result = await self._call_live_api(market_data)
        
        if not result:
            print("❌ Live API WebSocket не ответил (возможно требуется активация в Google AI Studio)")
        
        return result


# Singleton
_ai_brain_live = None

def get_ai_brain_live() -> AIBrainLive:
    """Получить singleton instance"""
    global _ai_brain_live
    if _ai_brain_live is None:
        _ai_brain_live = AIBrainLive()
    return _ai_brain_live
