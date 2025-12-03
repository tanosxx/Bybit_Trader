"""
AI Brain для анализа крипто рынков
Поддержка: Gemini (FREE tier) + OpenRouter (Claude/GPT)

v3.0: Gatekeeper система с двухуровневой фильтрацией:
- CHOP фильтр (отсекает боковик)
- Pattern Matcher (отсекает паттерны с плохой историей)
"""
import aiohttp
import json
import numpy as np
import time
from typing import Dict, List, Optional
from config import settings, GEMINI_CRYPTO_ANALYSIS_PROMPT, OPENROUTER_CRYPTO_ANALYSIS_PROMPT
from core.ta_lib import get_choppiness_index
from core.scenario_tester import get_scenario_tester


class AIBrain:
    """
    AI анализ крипто рынков с ротацией ключей и моделей
    
    v3.0: Gatekeeper система - двухуровневая фильтрация входов
    """
    
    def __init__(self, api_client=None):
        # Несколько Gemini API ключей для ротации (из .env)
        self.google_api_keys = [
            settings.google_api_key_1,  # Ключ 1
            settings.google_api_key_2,  # Ключ 2
            settings.google_api_key_3,  # Ключ 3
        ]
        # Фильтруем пустые ключи
        self.google_api_keys = [k for k in self.google_api_keys if k]
        self.current_key_index = 0
        
        # Gemini модели с лимитами (отсортированы по приоритету)
        self.gemini_models = [
            # Лучшие модели (больше лимитов)
            {"name": "gemini-2.0-flash-lite", "rpm": 30, "rpd": 200, "tpm": 1000000},
            {"name": "gemini-2.5-flash-lite", "rpm": 15, "rpd": 1000, "tpm": 250000},
            {"name": "gemini-2.0-flash", "rpm": 15, "rpd": 200, "tpm": 1000000},
            {"name": "gemini-2.5-flash", "rpm": 10, "rpd": 250, "tpm": 250000},
            # Экспериментальные
            {"name": "learnlm-2.0-flash-experimental", "rpm": 15, "rpd": 1500, "tpm": 0},
        ]
        self.current_model_index = 0
        
        # OpenRouter (не используем, но оставляем на случай)
        self.openrouter_api_key = settings.openrouter_api_key
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # ========== GATEKEEPER v3.0 ==========
        # ScenarioTester для Pattern Matching
        self.scenario_tester = None
        if api_client:
            try:
                self.scenario_tester = get_scenario_tester(api_client)
                print("🔍 Gatekeeper: ScenarioTester initialized")
            except Exception as e:
                print(f"⚠️ Gatekeeper: ScenarioTester init failed: {e}")
        
        # Пороги фильтрации
        self.chop_threshold = 60.0  # CHOP > 60 = флэт
        self.historical_wr_threshold = 40.0  # Historical WR < 40% = плохой паттерн
        
        print(f"🚦 Gatekeeper v3.0 enabled:")
        print(f"   CHOP threshold: {self.chop_threshold}")
        print(f"   Historical WR threshold: {self.historical_wr_threshold}%")
    
    async def _call_gemini(self, market_data: Dict) -> Optional[Dict]:
        """
        Вызов Gemini API с ротацией ключей и моделей
        
        Стратегия:
        1. Пробуем все модели с текущим ключом
        2. Если все модели исчерпаны - переключаемся на следующий ключ
        3. Повторяем для всех ключей
        """
        prompt = GEMINI_CRYPTO_ANALYSIS_PROMPT.format(
            market_data=json.dumps(market_data, indent=2)
        )
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 500
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Пробуем все ключи
        for key_idx, api_key in enumerate(self.google_api_keys):
            if not api_key:
                continue
            
            # Пробуем все модели с этим ключом
            for model_idx, model_info in enumerate(self.gemini_models):
                model_name = model_info["name"]
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Извлекаем текст ответа
                                text = data["candidates"][0]["content"]["parts"][0]["text"]
                                
                                # Очищаем от markdown
                                text = text.strip()
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                text = text.strip()
                                
                                # Парсим JSON
                                result = json.loads(text)
                                
                                print(f"✅ Gemini (ключ #{key_idx+1}, {model_name}): {result['decision']} (риск: {result['risk_score']}, уверенность: {result['confidence']:.0%})")
                                
                                return result
                            
                            elif response.status == 429:
                                # Лимит исчерпан, пробуем следующую модель
                                print(f"⚠️ Ключ #{key_idx+1}, {model_name}: лимит исчерпан")
                                continue
                            
                            else:
                                # Другая ошибка, пробуем следующую модель
                                continue
                
                except json.JSONDecodeError:
                    continue
                except Exception:
                    continue
            
            # Все модели с этим ключом исчерпаны
            print(f"⚠️ Ключ #{key_idx+1}: все модели исчерпаны, переключаемся на следующий ключ")
        
        # Все ключи и модели исчерпаны
        print(f"❌ Все Gemini ключи и модели исчерпаны")
        return None
    
    async def _call_openrouter(self, market_data: Dict, model: str = "anthropic/claude-3.5-haiku") -> Optional[Dict]:
        """
        Вызов OpenRouter API (Claude/GPT)
        """
        if not self.openrouter_api_key:
            return None
        
        prompt = OPENROUTER_CRYPTO_ANALYSIS_PROMPT.format(
            market_data=json.dumps(market_data, indent=2)
        )
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/bybit-trader",
            "X-Title": "Bybit Trader Bot"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.openrouter_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        text = data["choices"][0]["message"]["content"]
                        
                        # Очищаем от markdown
                        text = text.strip()
                        if text.startswith("```json"):
                            text = text[7:]
                        if text.startswith("```"):
                            text = text[3:]
                        if text.endswith("```"):
                            text = text[:-3]
                        text = text.strip()
                        
                        # Находим первый { и последний }
                        start = text.find('{')
                        end = text.rfind('}')
                        if start != -1 and end != -1:
                            text = text[start:end+1]
                        
                        result = json.loads(text)
                        
                        print(f"✅ OpenRouter ({model}) analysis: {result['decision']} (risk: {result['risk_score']})")
                        
                        return result
                    else:
                        error_text = await response.text()
                        print(f"❌ OpenRouter API error {response.status}: {error_text}")
                        return None
        
        except json.JSONDecodeError as e:
            print(f"❌ OpenRouter JSON parse error: {e}")
            print(f"Response text: {text}")
            return None
        except Exception as e:
            print(f"❌ OpenRouter API error: {e}")
            return None
    
    async def decide_trade(self, market_data: Dict, klines: List[Dict], news_sentiment: str = "NEUTRAL") -> Optional[Dict]:
        """
        Принять решение о сделке с Gatekeeper фильтрацией
        
        v3.0: Двухуровневая фильтрация:
        1. CHOP Check - отсекаем боковик
        2. Pattern Check - отсекаем паттерны с плохой историей
        
        Args:
            market_data: данные рынка (RSI, MACD, etc)
            klines: исторические свечи для CHOP и Pattern Matching
            news_sentiment: "EXTREME" игнорирует CHOP фильтр
        
        Returns:
            {
                "decision": "BUY/SELL/SKIP",
                "risk_score": 1-10,
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "key_factors": [...],
                "gatekeeper": {
                    "chop": float,
                    "historical_wr": float,
                    "passed": bool
                }
            }
        """
        symbol = market_data.get('symbol', '')
        signal = market_data.get('signal', 'SKIP')
        
        # ========== GATEKEEPER LEVEL 1: CHOP CHECK ==========
        try:
            # Извлекаем данные для CHOP
            if len(klines) >= 15:
                high = np.array([float(k['high']) for k in klines])
                low = np.array([float(k['low']) for k in klines])
                close = np.array([float(k['close']) for k in klines])
                
                chop = get_choppiness_index(high, low, close, period=14)
                
                # Проверка: CHOP > 60 И новости не EXTREME
                if chop > self.chop_threshold and news_sentiment != "EXTREME":
                    print(f"🚫 Gatekeeper: {symbol} SKIP - Choppy Market (CHOP: {chop:.1f})")
                    return {
                        "decision": "SKIP",
                        "risk_score": 10,
                        "confidence": 0.0,
                        "reasoning": f"Choppy Market detected (CHOP: {chop:.1f} > {self.chop_threshold})",
                        "key_factors": ["Sideways market", "High noise", "False signals likely"],
                        "gatekeeper": {
                            "chop": chop,
                            "historical_wr": None,
                            "passed": False,
                            "reason": "CHOP_FILTER"
                        }
                    }
            else:
                chop = 50.0  # Neutral если недостаточно данных
        
        except Exception as e:
            print(f"⚠️ CHOP calculation error: {e}")
            chop = 50.0  # Neutral при ошибке
        
        # ========== GATEKEEPER LEVEL 2: PATTERN CHECK ==========
        historical_wr = 50.0  # Default neutral
        
        if self.scenario_tester and signal in ['BUY', 'SELL']:
            try:
                # Lazy Loading: обновляем историю если нужно
                await self.scenario_tester.update_history(symbol)
                
                # Анализируем исторические паттерны
                historical_wr = self.scenario_tester.analyze_outcome(symbol, signal)
                
                # Проверка: Historical WR < 40%
                if historical_wr < self.historical_wr_threshold:
                    print(f"🚫 Gatekeeper: {symbol} SKIP - Bad Historical Pattern (WR: {historical_wr:.1f}%)")
                    return {
                        "decision": "SKIP",
                        "risk_score": 8,
                        "confidence": 0.0,
                        "reasoning": f"Bad Historical Pattern (Win Rate: {historical_wr:.1f}% < {self.historical_wr_threshold}%)",
                        "key_factors": ["Similar patterns failed in past", "Low probability setup"],
                        "gatekeeper": {
                            "chop": chop,
                            "historical_wr": historical_wr,
                            "passed": False,
                            "reason": "PATTERN_FILTER"
                        }
                    }
            
            except Exception as e:
                print(f"⚠️ Pattern analysis error: {e}")
                historical_wr = 50.0  # Neutral при ошибке
        
        # ========== GATEKEEPER PASSED - Анализируем через AI ==========
        print(f"✅ Gatekeeper: {symbol} PASSED (CHOP: {chop:.1f}, Historical WR: {historical_wr:.1f}%)")
        
        # Пробуем Gemini с ротацией ключей и моделей
        result = await self._call_gemini(market_data)
        
        if result:
            # Добавляем Gatekeeper метрики
            result['gatekeeper'] = {
                "chop": chop,
                "historical_wr": historical_wr,
                "passed": True,
                "reason": "ALL_CHECKS_PASSED"
            }
            return result
        
        print("❌ Gemini не ответил, пропускаем сделку")
        return None
    
    async def analyze_market(self, market_data: Dict, use_gemini: bool = True) -> Optional[Dict]:
        """
        Анализ рынка через AI (legacy метод, используй decide_trade)
        
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
            use_gemini: использовать Gemini (FREE) или OpenRouter
        
        Returns:
            {
                "decision": "BUY/SELL/SKIP",
                "risk_score": 1-10,
                "confidence": 0.0-1.0,
                "reasoning": "...",
                "key_factors": [...]
            }
        """
        
        # Пробуем Gemini с ротацией ключей и моделей
        result = await self._call_gemini(market_data)
        if result:
            return result
        
        print("❌ Gemini не ответил, пропускаем сделку")
        return None


# Singleton
_ai_brain = None

def get_ai_brain(api_client=None) -> AIBrain:
    """Получить singleton instance"""
    global _ai_brain
    if _ai_brain is None:
        _ai_brain = AIBrain(api_client)
    return _ai_brain
