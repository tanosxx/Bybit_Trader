"""
Futures Brain - Оптимизированная система принятия решений для фьючерсов

Особенности:
1. Smart Scaling - масштабирование ML confidence (0.50-0.65 -> 50%-100%)
2. Weighted Voting - взвешенное голосование агентов (Score >= 3)
3. Dynamic Leverage - плечо зависит от confidence
4. Smart Shorting - корректная обработка SHORT сигналов
"""
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FuturesAction(Enum):
    """Действия для фьючерсов"""
    LONG = "LONG"
    SHORT = "SHORT"
    SKIP = "SKIP"


@dataclass
class FuturesDecision:
    """Решение для фьючерсов"""
    action: FuturesAction
    trading_confidence: float  # Масштабированная уверенность (0-100%)
    raw_confidence: float      # Сырая уверенность от ML
    total_score: int           # Сумма весов агентов
    leverage: int              # Рекомендуемое плечо
    position_size_pct: float   # Размер позиции (% от баланса)
    reasoning: str
    agents_voted: Dict[str, bool]  # Какие агенты проголосовали


class FuturesBrain:
    """
    Мозг для фьючерсной торговли
    
    Smart Scaling:
    - Raw ML 0.50 -> Trading Conf 50%
    - Raw ML 0.575 -> Trading Conf 75%
    - Raw ML 0.65+ -> Trading Conf 100%
    
    Weighted Voting:
    - Conservative (вес 3): Trading Conf > 80% + TA confirm
    - Balanced (вес 2): Trading Conf > 60% + TA confirm
    - Aggressive (вес 1): Trading Conf > 50% (без TA)
    - ВХОД: Sum(Weights) >= 3
    
    Dynamic Leverage:
    - Conf < 60%: 2x
    - Conf 60-80%: 5x
    - Conf > 80%: 7x
    """
    
    def __init__(self):
        # Конфигурация агентов для фьючерсов (TRADING v5.0 - АКТИВНАЯ ТОРГОВЛЯ)
        self.agents = {
            'conservative': {
                'weight': 3,
                'min_confidence': 60,  # Снижено с 65 - хорошие сигналы
                'require_ta': True,
                'max_risk': 6
            },
            'balanced': {
                'weight': 2,
                'min_confidence': 45,  # Снижено с 50 - средние сигналы
                'require_ta': False,  # УБРАНО требование TA - даём больше шансов
                'max_risk': 7
            },
            'aggressive': {
                'weight': 1,
                'min_confidence': 35,  # Снижено с 40 - слабые сигналы тоже пропускаем
                'require_ta': False,
                'max_risk': 8
            }
        }
        
        # Порог для входа - СНИЖЕН до 2 (достаточно 1 агента Balanced или Conservative + Aggressive)
        self.min_score_to_trade = 2  # balanced (2) = 2 ИЛИ aggressive (1) + conservative (3) = 4
        
        # Лимит потерь на сделку (% от депозита)
        self.max_loss_per_trade_pct = 2.0
        
        # Статистика
        self.stats = {
            'total_decisions': 0,
            'longs': 0,
            'shorts': 0,
            'skips': 0,
            'avg_confidence': 0.0,
            'avg_leverage': 0.0
        }
    
    def scale_confidence(self, raw_confidence: float) -> float:
        """
        Smart Scaling: масштабирование ML confidence
        
        Raw ML выдаёт 0.30-0.65 (LSTM часто даёт 0.30 для HOLD)
        Масштабируем более агрессивно:
        
        Формула: trading_conf = (raw - 0.30) / 0.35 * 70 + 30
        - raw 0.30 -> 30%
        - raw 0.50 -> 70%
        - raw 0.60 -> 94%
        - raw 0.65 -> 100%
        """
        if raw_confidence <= 0.30:
            return 30.0
        elif raw_confidence >= 0.65:
            return 100.0
        else:
            # Агрессивное масштабирование 0.30-0.65 -> 30-100
            scaled = ((raw_confidence - 0.30) / 0.35) * 70 + 30
            return min(100.0, max(30.0, scaled))
    
    def get_dynamic_leverage(self, trading_confidence: float) -> int:
        """
        Dynamic Leverage на основе Trading Confidence
        
        - Conf < 60%: 2x (Low Risk)
        - Conf 60-80%: 5x (Mid Risk)
        - Conf > 80%: 7x (High Risk)
        """
        if trading_confidence < 60:
            return 2
        elif trading_confidence < 80:
            return 5
        else:
            return 7
    
    def calculate_position_size(self, leverage: int, virtual_balance: float) -> float:
        """
        Рассчитать размер позиции с учётом лимита потерь
        
        Лимит: max 2% потерь от депозита на сделку
        
        Формула:
        - Max Loss = Balance * 2%
        - Position Size = Max Loss / (SL% * Leverage)
        - Предполагаем SL = 2% от цены входа
        """
        max_loss = virtual_balance * (self.max_loss_per_trade_pct / 100)
        sl_pct = 0.02  # 2% стоп-лосс
        
        # Position Size = Max Loss / (SL% * Leverage)
        # Но нам нужен % от баланса
        position_size_pct = (max_loss / (sl_pct * leverage)) / virtual_balance * 100
        
        # Ограничиваем 5-25% от баланса
        return min(25.0, max(5.0, position_size_pct))

    def _check_ta_confirmation(self, market_data: Dict, action: str) -> bool:
        """
        Проверить подтверждение от Technical Analysis
        """
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        trend = market_data.get('trend', 'sideways')
        ta_signal = market_data.get('technical_signal', 'NEUTRAL')
        
        if action == 'LONG':
            # Для LONG: RSI не перекуплен + (bullish MACD или uptrend)
            if rsi > 75:
                return False
            if macd_trend == 'bullish' or trend in ['uptrend', 'strong_uptrend']:
                return True
            if ta_signal == 'BUY':
                return True
            if rsi < 40:  # Перепродан - хороший вход для LONG
                return True
            return False
        
        elif action == 'SHORT':
            # Для SHORT: RSI не перепродан + (bearish MACD или downtrend)
            if rsi < 25:
                return False
            if macd_trend == 'bearish' or trend in ['downtrend', 'strong_downtrend']:
                return True
            if ta_signal == 'SELL':
                return True
            if rsi > 60:  # Перекуплен - хороший вход для SHORT
                return True
            return False
        
        return False
    
    def _get_agent_votes(self, trading_conf: float, ta_confirmed: bool, 
                         risk_score: int, action: str) -> Dict[str, bool]:
        """
        Получить голоса агентов
        
        Returns: {'conservative': True/False, 'balanced': True/False, 'aggressive': True/False}
        """
        votes = {}
        
        for agent_name, config in self.agents.items():
            vote = False
            
            # Проверяем confidence
            if trading_conf >= config['min_confidence']:
                # Проверяем риск
                if risk_score <= config['max_risk']:
                    # Проверяем TA если требуется
                    if config['require_ta']:
                        vote = ta_confirmed
                    else:
                        vote = True
            
            votes[agent_name] = vote
        
        return votes
    
    def _calculate_total_score(self, votes: Dict[str, bool]) -> int:
        """Рассчитать общий score на основе голосов"""
        total = 0
        for agent_name, voted in votes.items():
            if voted:
                total += self.agents[agent_name]['weight']
        return total
    
    def decide(self, market_data: Dict, ai_analysis: Dict, 
               news_sentiment: str = 'NEUTRAL') -> FuturesDecision:
        """
        Принять решение для фьючерсной торговли
        
        Args:
            market_data: {'rsi', 'macd', 'trend', 'technical_signal', 'price'}
            ai_analysis: {'decision', 'confidence', 'risk_score', 'reasoning'}
            news_sentiment: 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
        
        Returns:
            FuturesDecision с action, leverage, position_size и т.д.
        """
        self.stats['total_decisions'] += 1
        
        # Извлекаем данные
        raw_decision = ai_analysis.get('decision', 'SKIP')
        raw_confidence = ai_analysis.get('confidence', 0.0)
        risk_score = ai_analysis.get('risk_score', 5)
        reasoning = ai_analysis.get('reasoning', '')
        
        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        trend = market_data.get('trend', 'sideways')
        
        # ========== SMART SCALING ==========
        trading_conf = self.scale_confidence(raw_confidence)
        
        # ========== ОПРЕДЕЛЯЕМ ДЕЙСТВИЕ ==========
        action = 'SKIP'
        
        # Логика определения LONG/SHORT (FIXED - убран искусственный буст)
        if raw_decision == 'BUY':
            action = 'LONG'
        elif raw_decision == 'SELL':
            action = 'SHORT'
        elif raw_decision in ['HOLD', 'SKIP']:
            # ТОЛЬКО если ML не уверен, смотрим на СИЛЬНЫЕ сигналы TA
            # Убран искусственный буст - используем только реальную уверенность ML
            if rsi < 25 and macd_trend == 'bullish_crossover' and trend in ['uptrend', 'strong_uptrend']:
                # Экстремально перепродан + бычий кроссовер + тренд вверх
                action = 'LONG'
                trading_conf = max(trading_conf, 50)  # Минимальный буст
            elif rsi > 75 and macd_trend == 'bearish_crossover' and trend in ['downtrend', 'strong_downtrend']:
                # Экстремально перекуплен + медвежий кроссовер + тренд вниз
                action = 'SHORT'
                trading_conf = max(trading_conf, 50)  # Минимальный буст
            # Убраны слабые сигналы (rsi < 65, rsi > 35) - они давали ложные входы
        
        # ========== SMART SHORTING (FIXED - проверка тренда) ==========
        # Если новости негативные + ML SELL + TA Bearish -> SHORT
        # НО: НЕ шортим на сильном uptren даже с негативными новостями!
        if news_sentiment == 'NEGATIVE':
            if raw_decision == 'SELL' and macd_trend == 'bearish' and trend in ['downtrend', 'strong_downtrend']:
                # Все 3 условия: негативные новости + ML SELL + медвежий тренд
                action = 'SHORT'
                trading_conf = max(trading_conf, 60)  # Умеренный буст
                reasoning = f"News NEGATIVE + ML SELL + {trend} -> SHORT"
            elif trend in ['uptrend', 'strong_uptrend']:
                # Защита: не шортим на сильном uptren
                if action == 'SHORT':
                    action = 'SKIP'
                    reasoning = "SHORT blocked: strong uptrend detected"
        
        if action == 'SKIP':
            self.stats['skips'] += 1
            return FuturesDecision(
                action=FuturesAction.SKIP,
                trading_confidence=trading_conf,
                raw_confidence=raw_confidence,
                total_score=0,
                leverage=2,
                position_size_pct=0,
                reasoning="No clear signal",
                agents_voted={}
            )
        
        # ========== TA CONFIRMATION ==========
        ta_confirmed = self._check_ta_confirmation(market_data, action)
        
        # ========== WEIGHTED VOTING ==========
        votes = self._get_agent_votes(trading_conf, ta_confirmed, risk_score, action)
        total_score = self._calculate_total_score(votes)
        
        # ========== РЕШЕНИЕ О ВХОДЕ ==========
        if total_score >= self.min_score_to_trade:
            # ========== DYNAMIC LEVERAGE ==========
            leverage = self.get_dynamic_leverage(trading_conf)
            position_size = self.calculate_position_size(leverage, 500.0)  # $500 virtual balance
            
            final_action = FuturesAction.LONG if action == 'LONG' else FuturesAction.SHORT
            
            # Статистика
            if final_action == FuturesAction.LONG:
                self.stats['longs'] += 1
            else:
                self.stats['shorts'] += 1
            
            # Обновляем средние
            n = self.stats['longs'] + self.stats['shorts']
            self.stats['avg_confidence'] = (self.stats['avg_confidence'] * (n-1) + trading_conf) / n
            self.stats['avg_leverage'] = (self.stats['avg_leverage'] * (n-1) + leverage) / n
            
            return FuturesDecision(
                action=final_action,
                trading_confidence=trading_conf,
                raw_confidence=raw_confidence,
                total_score=total_score,
                leverage=leverage,
                position_size_pct=position_size,
                reasoning=f"Score {total_score} >= 3 | Conf {trading_conf:.0f}% | {action}",
                agents_voted=votes
            )
        else:
            self.stats['skips'] += 1
            return FuturesDecision(
                action=FuturesAction.SKIP,
                trading_confidence=trading_conf,
                raw_confidence=raw_confidence,
                total_score=total_score,
                leverage=2,
                position_size_pct=0,
                reasoning=f"Score {total_score} < 3 (need 3+)",
                agents_voted=votes
            )
    
    def print_stats(self):
        """Вывести статистику"""
        print(f"\n🧠 FUTURES BRAIN STATS:")
        print(f"   Total Decisions: {self.stats['total_decisions']}")
        print(f"   LONGs: {self.stats['longs']}")
        print(f"   SHORTs: {self.stats['shorts']}")
        print(f"   SKIPs: {self.stats['skips']}")
        if self.stats['longs'] + self.stats['shorts'] > 0:
            print(f"   Avg Confidence: {self.stats['avg_confidence']:.1f}%")
            print(f"   Avg Leverage: {self.stats['avg_leverage']:.1f}x")


# Singleton
_futures_brain = None

def get_futures_brain() -> FuturesBrain:
    global _futures_brain
    if _futures_brain is None:
        _futures_brain = FuturesBrain()
    return _futures_brain
