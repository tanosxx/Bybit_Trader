"""
Strategic Brain - Высокоуровневый анализ рыночного режима
Использует AI Gateway для определения глобального тренда
Работает как Gatekeeper Level 0 (перед всеми остальными фильтрами)
"""

import os
from typing import Dict, List, Optional
from datetime import datetime

# Import AI Gateway Client
try:
    from core.ai_gateway_client import get_ai_gateway_client
    AI_GATEWAY_AVAILABLE = True
except ImportError:
    AI_GATEWAY_AVAILABLE = False
    print("⚠️ AI Gateway Client not available")

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
REGIME_UNCERTAIN = "UNCERTAIN"      # Высокая волатильность -> торговля разрешена с осторожностью

VALID_REGIMES = [REGIME_BULL_RUSH, REGIME_BEAR_CRASH, REGIME_SIDEWAYS, REGIME_UNCERTAIN]


class StrategicBrain:
    """
    Стратегический анализатор рынка на базе AI Gateway
    Определяет глобальный режим рынка раз в 15 минут
    """
    
    def __init__(self):
        """Инициализация AI Gateway клиента"""
        # AI Gateway Client
        self.ai_client = None
        if AI_GATEWAY_AVAILABLE:
            try:
                self.ai_client = get_ai_gateway_client()
                print(f"✅ Strategic Brain initialized")
                print(f"   Provider: AI Gateway (unified LLM)")
            except Exception as e:
                print(f"   ⚠️ AI Gateway init failed: {e}")
        
        # Кэш режима с гибким обновлением
        self.current_regime: str = REGIME_SIDEWAYS  # Default: торгуем как обычно
        self.last_update: Optional[datetime] = None
        self.update_interval_hours: float = 0.25  # Базовый интервал: 15 минут
        
        # Триггеры для принудительного обновления (реакция на изменения)
        # Если BTC изменился на 3%+ с последней проверки -> обновить режим немедленно
        self.last_btc_price: Optional[float] = None
        self.price_change_threshold: float = 3.0  # 3% изменение BTC = обновить режим
        
        if not self.ai_client:
            print("⚠️ No AI Gateway available")
            print("   → Strategic Brain disabled, using SIDEWAYS regime")
    
    def _build_prompt(self, daily_candles: List[Dict], news_summary: str) -> str:
        """
        Формирует промпт для AI Gateway с данными о рынке
        
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
        news_summary: str = "",
        current_btc_price: Optional[float] = None
    ) -> str:
        """
        Определяет текущий рыночный режим через AI Gateway
        
        Args:
            daily_candles: Дневные свечи (минимум 7 дней)
            news_summary: Сводка новостей от News Brain
            current_btc_price: Текущая цена BTC (для триггера обновления)
        
        Returns:
            Один из: BULL_RUSH, BEAR_CRASH, SIDEWAYS, UNCERTAIN
        """
        # Проверка триггеров для принудительного обновления
        force_update = False
        
        # Триггер 1: Резкое изменение цены BTC
        if current_btc_price and self.last_btc_price:
            price_change_pct = abs((current_btc_price - self.last_btc_price) / self.last_btc_price * 100)
            if price_change_pct >= self.price_change_threshold:
                print(f"🚨 Strategic Brain: BTC price changed {price_change_pct:.1f}% - forcing update")
                force_update = True
        
        # Проверка: нужно ли обновлять режим?
        if self.last_update and not force_update:
            hours_since_update = (datetime.now() - self.last_update).total_seconds() / 3600
            if hours_since_update < self.update_interval_hours:
                print(f"📊 Strategic Brain: Using cached regime '{self.current_regime}' "
                      f"(updated {hours_since_update:.1f}h ago)")
                return self.current_regime
        
        # Если нет AI Gateway, возвращаем SIDEWAYS
        if not self.ai_client:
            print("⚠️ Strategic Brain: No AI Gateway available, using SIDEWAYS")
            return REGIME_SIDEWAYS
        
        try:
            # Формируем промпт
            prompt = self._build_prompt(daily_candles, news_summary)
            
            print(f"🧠 Strategic Brain: Analyzing market regime...")
            
            # Вызов AI Gateway
            response = self.ai_client.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=200
            )
            
            if response:
                regime_raw = response.strip().upper()
                
                # Парсим режим (ищем ключевое слово)
                detected_regime = REGIME_SIDEWAYS  # Default
                for valid_regime in VALID_REGIMES:
                    if valid_regime in regime_raw:
                        detected_regime = valid_regime
                        break
                
                # Обновляем кэш
                self.current_regime = detected_regime
                self.last_update = datetime.now()
                
                # Сохраняем текущую цену BTC для триггера
                if current_btc_price:
                    self.last_btc_price = current_btc_price
                
                print(f"✅ Strategic Brain: Market Regime = {detected_regime}")
                print(f"   → AI Gateway Response: {regime_raw[:100]}")
                if force_update:
                    print(f"   → Triggered by: Price change")
                
                # Обновляем GlobalBrainState для Neural HUD
                if STATE_AVAILABLE:
                    try:
                        state = get_global_brain_state()
                        state.update_strategic(detected_regime, regime_raw[:200])
                        
                        # Сохраняем полный текст анализа для AI Reasoning Panel
                        reasoning_text = f"""🧠 STRATEGIC BRAIN ANALYSIS (Updated: {datetime.now().strftime('%H:%M:%S')})

Market Regime: {detected_regime}

AI Gateway Analysis:
{regime_raw}

Trading Strategy:
"""
                        if detected_regime == "BULL_RUSH":
                            reasoning_text += "→ LONG positions only (block all SHORT signals)\n→ Strong uptrend detected, bullish momentum dominates"
                        elif detected_regime == "BEAR_CRASH":
                            reasoning_text += "→ SHORT positions only (block all LONG signals)\n→ Strong downtrend detected, bearish pressure dominates"
                        elif detected_regime == "SIDEWAYS":
                            reasoning_text += "→ Both LONG and SHORT allowed\n→ Range-bound market, normal trading conditions"
                        elif detected_regime == "UNCERTAIN":
                            reasoning_text += "→ NO TRADING (wait for clarity)\n→ High volatility or conflicting signals detected"
                        
                        reasoning_text += f"\n\nLast BTC Price: ${self.last_btc_price:.2f}" if self.last_btc_price else ""
                        reasoning_text += f"\nNext Update: {self.update_interval_hours}h or ±{self.price_change_threshold}% BTC move"
                        
                        state.update_ai_reasoning(reasoning_text)
                    except Exception as e:
                        print(f"⚠️ Failed to update GlobalBrainState: {e}")
                
                return detected_regime
            else:
                print(f"⚠️  AI Gateway failed")
                    
        except Exception as e:
            print(f"❌ Strategic Brain Error: {e}")
        
        # Если всё упало - возвращаем SIDEWAYS
        print(f"   → Fallback: SIDEWAYS regime (safe mode)")
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
            # СМЯГЧЕНО: Разрешаем торговлю, но с повышенной осторожностью
            # Multi-Agent система сама отфильтрует слабые сигналы
            print(f"⚠️  Strategic Warning: UNCERTAIN regime - trade with caution")
            return True
        
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
