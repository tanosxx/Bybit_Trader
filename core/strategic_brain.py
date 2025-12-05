"""
Strategic Brain - Высокоуровневый анализ рыночного режима
Использует Claude 3.5 Sonnet через OhMyGPT API для определения глобального тренда
Работает как Gatekeeper Level 0 (перед всеми остальными фильтрами)
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI

# Import GlobalBrainState для обновления
try:
    from core.state import get_global_brain_state
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False

# Market Regime Types
REGIME_BULL_RUSH = "BULL_RUSH"      # Агрессивный рост -> только LONG
REGIME_BEAR_CRASH = "BEAR_CRASH"    # Агрессивное падение -> только SHORT
REGIME_SIDEWAYS = "SIDEWAYS"        # Боковик -> LONG и SHORT разрешены
REGIME_UNCERTAIN = "UNCERTAIN"      # Высокая волатильность -> НЕ торговать

VALID_REGIMES = [REGIME_BULL_RUSH, REGIME_BEAR_CRASH, REGIME_SIDEWAYS, REGIME_UNCERTAIN]


class StrategicBrain:
    """
    Стратегический анализатор рынка на базе Claude 3.5 Sonnet
    Определяет глобальный режим рынка раз в 4 часа
    """
    
    def __init__(self):
        """Инициализация клиента OhMyGPT (OpenAI-compatible)"""
        self.api_key = os.getenv("OHMYGPT_KEY")
        self.base_url = os.getenv("STRATEGIC_DRIVER_URL", "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg")
        self.model = os.getenv("STRATEGIC_MODEL", "claude-3-5-sonnet-20240620")
        
        # Кэш режима (обновляется раз в 4 часа)
        self.current_regime: str = REGIME_SIDEWAYS  # Default: торгуем как обычно
        self.last_update: Optional[datetime] = None
        self.update_interval_hours: int = 4
        
        # Инициализация клиента
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                print(f"✅ Strategic Brain initialized (Model: {self.model})")
            except Exception as e:
                print(f"⚠️ Strategic Brain client init failed: {e}")
                print("   → Will use default SIDEWAYS regime")
        else:
            print("⚠️ OHMYGPT_KEY not found in .env")
            print("   → Strategic Brain disabled, using SIDEWAYS regime")
    
    def _build_prompt(self, daily_candles: List[Dict], news_summary: str) -> str:
        """
        Формирует промпт для Claude с данными о рынке
        
        Args:
            daily_candles: Список дневных свечей (7 дней) для BTC/ETH
            news_summary: Краткая сводка новостей от News Brain
        
        Returns:
            Промпт для анализа
        """
        # Форматируем свечи
        candles_text = ""
        for candle in daily_candles[-7:]:  # Последние 7 дней
            symbol = candle.get('symbol', 'UNKNOWN')
            open_price = candle.get('open', 0)
            close_price = candle.get('close', 0)
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            volume = candle.get('volume', 0)
            change_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
            
            candles_text += f"{symbol}: Open ${open_price:.2f}, Close ${close_price:.2f}, "
            candles_text += f"High ${high:.2f}, Low ${low:.2f}, Change {change_pct:+.2f}%, Vol {volume:.0f}\n"
        
        prompt = f"""You are a Senior Crypto Market Analyst with 10+ years of experience.

Your task: Analyze the current market structure and determine the DOMINANT regime.

📰 News Sentiment Summary:
{news_summary if news_summary else "No significant news"}

📊 Price Action (Last 7 Days):
{candles_text}

Based on this data, determine the current Market Regime. Choose ONE strictly:

1. BULL_RUSH - Strong uptrend, bullish momentum dominates
   → Strategy: LONG positions only, block all SHORT signals

2. BEAR_CRASH - Strong downtrend, bearish pressure dominates
   → Strategy: SHORT positions only, block all LONG signals

3. SIDEWAYS - Range-bound market, no clear direction
   → Strategy: Both LONG and SHORT allowed (normal trading)

4. UNCERTAIN - High volatility, conflicting signals, major news risk
   → Strategy: NO TRADING (wait for clarity)

CRITICAL: Return ONLY the regime name (e.g., "BULL_RUSH"), nothing else.
"""
        return prompt
    
    async def get_market_regime(
        self, 
        daily_candles: List[Dict], 
        news_summary: str = ""
    ) -> str:
        """
        Определяет текущий рыночный режим через Claude
        
        Args:
            daily_candles: Дневные свечи (минимум 7 дней)
            news_summary: Сводка новостей от News Brain
        
        Returns:
            Один из: BULL_RUSH, BEAR_CRASH, SIDEWAYS, UNCERTAIN
        """
        # Проверка: нужно ли обновлять режим?
        if self.last_update:
            hours_since_update = (datetime.now() - self.last_update).total_seconds() / 3600
            if hours_since_update < self.update_interval_hours:
                print(f"📊 Strategic Brain: Using cached regime '{self.current_regime}' "
                      f"(updated {hours_since_update:.1f}h ago)")
                return self.current_regime
        
        # Если клиент не инициализирован, возвращаем SIDEWAYS
        if not self.client:
            print("⚠️ Strategic Brain: Client not available, using SIDEWAYS")
            return REGIME_SIDEWAYS
        
        try:
            # Формируем промпт
            prompt = self._build_prompt(daily_candles, news_summary)
            
            print(f"🧠 Strategic Brain: Analyzing market regime...")
            
            # Вызов Claude через OpenAI-compatible API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Низкая температура для консистентности
                max_tokens=50     # Нам нужно только одно слово
            )
            
            # Извлекаем ответ
            regime_raw = response.choices[0].message.content.strip().upper()
            
            # Парсим режим (ищем ключевое слово)
            detected_regime = REGIME_SIDEWAYS  # Default
            for valid_regime in VALID_REGIMES:
                if valid_regime in regime_raw:
                    detected_regime = valid_regime
                    break
            
            # Обновляем кэш
            self.current_regime = detected_regime
            self.last_update = datetime.now()
            
            print(f"✅ Strategic Brain: Market Regime = {detected_regime}")
            print(f"   → Claude Response: {regime_raw[:100]}")
            
            # Обновляем GlobalBrainState для Neural HUD
            if STATE_AVAILABLE:
                try:
                    state = get_global_brain_state()
                    state.update_strategic(detected_regime, regime_raw[:200])
                except Exception as e:
                    print(f"⚠️ Failed to update GlobalBrainState: {e}")
            
            return detected_regime
        
        except Exception as e:
            print(f"❌ Strategic Brain API Error: {e}")
            print(f"   → Fallback to SIDEWAYS regime (safe mode)")
            
            # В случае ошибки возвращаем SIDEWAYS (торгуем как обычно)
            self.current_regime = REGIME_SIDEWAYS
            return REGIME_SIDEWAYS
    
    def should_allow_signal(self, signal_direction: str, current_regime: str = None) -> bool:
        """
        Проверяет, разрешён ли сигнал в текущем режиме (Gatekeeper Level 0)
        
        Args:
            signal_direction: "BUY" или "SELL"
            current_regime: Текущий режим (если None, использует кэшированный)
        
        Returns:
            True если сигнал разрешён, False если заблокирован
        """
        regime = current_regime or self.current_regime
        
        # Правила фильтрации
        if regime == REGIME_BULL_RUSH:
            # Только LONG
            if signal_direction == "SELL":
                print(f"🚫 Strategic Veto: SELL blocked (Regime: {regime})")
                return False
        
        elif regime == REGIME_BEAR_CRASH:
            # Только SHORT
            if signal_direction == "BUY":
                print(f"🚫 Strategic Veto: BUY blocked (Regime: {regime})")
                return False
        
        elif regime == REGIME_UNCERTAIN:
            # НЕ торговать вообще
            print(f"🚫 Strategic Veto: ALL signals blocked (Regime: {regime})")
            return False
        
        # SIDEWAYS или любой другой режим -> разрешаем всё
        return True


# Singleton instance
_strategic_brain_instance = None

def get_strategic_brain() -> StrategicBrain:
    """Получить singleton instance Strategic Brain"""
    global _strategic_brain_instance
    if _strategic_brain_instance is None:
        _strategic_brain_instance = StrategicBrain()
    return _strategic_brain_instance
