"""
Multi-Agent Trading System v1.0
Несколько агентов с разными стратегиями + Meta-Agent

Архитектура:
- Conservative Agent: низкий риск, высокая уверенность
- Balanced Agent: средний риск, средняя уверенность  
- Aggressive Agent: высокий риск, низкая уверенность
- Meta-Agent: выбирает лучшего на основе последних результатов
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

from core.ta_lib import RiskLevel, get_dynamic_risk_manager


class AgentType(Enum):
    """Типы агентов"""
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


@dataclass
class AgentConfig:
    """Конфигурация агента"""
    name: str
    agent_type: AgentType
    max_risk_score: int          # Максимальный риск AI (1-10)
    min_confidence: float        # Минимальная уверенность (0-1)
    position_size_pct: float     # Размер позиции (% от баланса)
    risk_level: RiskLevel        # Уровень риска для ta_lib
    rsi_oversold: int            # RSI для покупки
    rsi_overbought: int          # RSI для продажи
    require_ta_confirm: bool     # Требовать подтверждение TA
    max_daily_trades: int        # Макс сделок в день


@dataclass
class AgentDecision:
    """Решение агента"""
    agent_type: AgentType
    decision: str                # BUY/SELL/SKIP
    confidence: float
    risk_score: int
    reasoning: str
    position_size_pct: float
    approved: bool = True        # Одобрено Meta-Agent


@dataclass
class AgentStats:
    """Статистика агента"""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    win_rate: float = 0.0
    last_trades: deque = field(default_factory=lambda: deque(maxlen=50))
    daily_trades: int = 0
    last_trade_date: Optional[datetime] = None


# Конфигурации агентов
AGENT_CONFIGS = {
    AgentType.CONSERVATIVE: AgentConfig(
        name="Conservative",
        agent_type=AgentType.CONSERVATIVE,
        max_risk_score=4,
        min_confidence=0.75,
        position_size_pct=0.08,      # 8% от баланса
        risk_level=RiskLevel.LOW,
        rsi_oversold=25,
        rsi_overbought=75,
        require_ta_confirm=True,
        max_daily_trades=3
    ),
    AgentType.BALANCED: AgentConfig(
        name="Balanced",
        agent_type=AgentType.BALANCED,
        max_risk_score=6,
        min_confidence=0.60,
        position_size_pct=0.12,      # 12% от баланса
        risk_level=RiskLevel.MEDIUM,
        rsi_oversold=30,
        rsi_overbought=70,
        require_ta_confirm=True,
        max_daily_trades=5
    ),
    AgentType.AGGRESSIVE: AgentConfig(
        name="Aggressive",
        agent_type=AgentType.AGGRESSIVE,
        max_risk_score=8,
        min_confidence=0.45,
        position_size_pct=0.18,      # 18% от баланса
        risk_level=RiskLevel.HIGH,
        rsi_oversold=35,
        rsi_overbought=65,
        require_ta_confirm=False,
        max_daily_trades=10
    )
}


class TradingAgent:
    """Торговый агент с определённой стратегией"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.stats = AgentStats()
        self.risk_manager = get_dynamic_risk_manager()
    
    def _reset_daily_counter(self):
        """Сброс дневного счётчика"""
        today = datetime.utcnow().date()
        if self.stats.last_trade_date != today:
            self.stats.daily_trades = 0
            self.stats.last_trade_date = today
    
    def can_trade(self) -> Tuple[bool, str]:
        """Проверить может ли агент торговать"""
        self._reset_daily_counter()
        
        if self.stats.daily_trades >= self.config.max_daily_trades:
            return False, f"Daily limit reached ({self.stats.daily_trades}/{self.config.max_daily_trades})"
        
        return True, "OK"
    
    def evaluate(self, market_data: Dict, ai_analysis: Dict) -> AgentDecision:
        """
        Оценить рынок и принять решение
        
        Args:
            market_data: Данные рынка (price, rsi, macd, etc.)
            ai_analysis: Анализ от AI Brain
        
        Returns:
            AgentDecision
        """
        can_trade, reason = self.can_trade()
        if not can_trade:
            return AgentDecision(
                agent_type=self.config.agent_type,
                decision="SKIP",
                confidence=0,
                risk_score=10,
                reasoning=reason,
                position_size_pct=0,
                approved=False
            )
        
        # Получаем данные
        ai_decision = ai_analysis.get('decision', 'SKIP')
        ai_confidence = ai_analysis.get('confidence', 0)
        ai_risk = ai_analysis.get('risk_score', 10)
        
        rsi = market_data.get('rsi', 50)
        ta_signal = market_data.get('technical_signal', 'SKIP')
        macd = market_data.get('macd', {})
        macd_trend = macd.get('trend', 'neutral')
        
        # Проверяем фильтры агента
        decision = "SKIP"
        confidence = ai_confidence
        reasoning_parts = []
        
        # 1. Проверка риска
        if ai_risk > self.config.max_risk_score:
            reasoning_parts.append(f"Risk too high: {ai_risk} > {self.config.max_risk_score}")
            return AgentDecision(
                agent_type=self.config.agent_type,
                decision="SKIP",
                confidence=0,
                risk_score=ai_risk,
                reasoning=" | ".join(reasoning_parts),
                position_size_pct=0
            )
        
        # 2. Проверка уверенности
        if ai_confidence < self.config.min_confidence:
            reasoning_parts.append(f"Confidence too low: {ai_confidence:.0%} < {self.config.min_confidence:.0%}")
            return AgentDecision(
                agent_type=self.config.agent_type,
                decision="SKIP",
                confidence=ai_confidence,
                risk_score=ai_risk,
                reasoning=" | ".join(reasoning_parts),
                position_size_pct=0
            )
        
        # 3. RSI фильтр
        if ai_decision == "BUY" and rsi > self.config.rsi_overbought:
            reasoning_parts.append(f"RSI overbought: {rsi:.0f} > {self.config.rsi_overbought}")
            return AgentDecision(
                agent_type=self.config.agent_type,
                decision="SKIP",
                confidence=ai_confidence * 0.5,
                risk_score=ai_risk,
                reasoning=" | ".join(reasoning_parts),
                position_size_pct=0
            )
        
        if ai_decision == "SELL" and rsi < self.config.rsi_oversold:
            reasoning_parts.append(f"RSI oversold: {rsi:.0f} < {self.config.rsi_oversold}")
            return AgentDecision(
                agent_type=self.config.agent_type,
                decision="SKIP",
                confidence=ai_confidence * 0.5,
                risk_score=ai_risk,
                reasoning=" | ".join(reasoning_parts),
                position_size_pct=0
            )
        
        # 4. TA подтверждение (если требуется)
        if self.config.require_ta_confirm:
            if ai_decision == "BUY" and ta_signal != "BUY":
                # Проверяем MACD как альтернативу
                if macd_trend not in ['bullish', 'bullish_crossover']:
                    reasoning_parts.append(f"No TA confirmation (signal: {ta_signal}, MACD: {macd_trend})")
                    confidence *= 0.7
        
        # 5. Принимаем решение
        if ai_decision in ["BUY", "SELL"]:
            decision = ai_decision
            reasoning_parts.append(f"AI: {ai_decision} ({ai_confidence:.0%})")
            reasoning_parts.append(f"RSI: {rsi:.0f}")
            
            # Бонус за сильные сигналы
            if ai_decision == "BUY" and rsi < self.config.rsi_oversold:
                confidence = min(confidence * 1.1, 0.95)
                reasoning_parts.append("RSI oversold bonus")
            elif ai_decision == "SELL" and rsi > self.config.rsi_overbought:
                confidence = min(confidence * 1.1, 0.95)
                reasoning_parts.append("RSI overbought bonus")
        
        return AgentDecision(
            agent_type=self.config.agent_type,
            decision=decision,
            confidence=confidence,
            risk_score=ai_risk,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "No signal",
            position_size_pct=self.config.position_size_pct
        )
    
    def record_trade(self, pnl: float):
        """Записать результат сделки"""
        self.stats.total_trades += 1
        self.stats.daily_trades += 1
        self.stats.total_pnl += pnl
        
        if pnl > 0:
            self.stats.wins += 1
            self.stats.last_trades.append(1)
        else:
            self.stats.losses += 1
            self.stats.last_trades.append(0)
        
        if self.stats.total_trades > 0:
            self.stats.win_rate = (self.stats.wins / self.stats.total_trades) * 100
            self.stats.avg_pnl = self.stats.total_pnl / self.stats.total_trades



class MetaAgent:
    """
    Meta-Agent: выбирает лучшего агента на основе последних результатов
    
    Алгоритм:
    1. Собирает решения от всех агентов
    2. Взвешивает по последним результатам (win rate за последние 50 сделок)
    3. Выбирает агента с лучшим score
    4. Может отклонить все решения если нет консенсуса
    """
    
    def __init__(self):
        self.agents: Dict[AgentType, TradingAgent] = {}
        
        # Создаём агентов
        for agent_type, config in AGENT_CONFIGS.items():
            self.agents[agent_type] = TradingAgent(config)
        
        # Веса агентов (динамически обновляются)
        self.agent_weights: Dict[AgentType, float] = {
            AgentType.CONSERVATIVE: 1.0,
            AgentType.BALANCED: 1.0,
            AgentType.AGGRESSIVE: 1.0
        }
        
        # Статистика Meta-Agent
        self.stats = {
            'total_decisions': 0,
            'conservative_selected': 0,
            'balanced_selected': 0,
            'aggressive_selected': 0,
            'consensus_decisions': 0,
            'no_consensus': 0
        }
    
    def _update_weights(self):
        """Обновить веса агентов на основе последних результатов"""
        for agent_type, agent in self.agents.items():
            if len(agent.stats.last_trades) >= 10:
                # Win rate за последние сделки
                recent_wr = sum(agent.stats.last_trades) / len(agent.stats.last_trades)
                
                # Вес = win_rate * (1 + avg_pnl_normalized)
                avg_pnl_factor = 1.0
                if agent.stats.avg_pnl != 0:
                    avg_pnl_factor = 1.0 + min(max(agent.stats.avg_pnl / 100, -0.5), 0.5)
                
                self.agent_weights[agent_type] = recent_wr * avg_pnl_factor
            else:
                # Дефолтные веса пока мало данных
                default_weights = {
                    AgentType.CONSERVATIVE: 0.8,
                    AgentType.BALANCED: 1.0,
                    AgentType.AGGRESSIVE: 0.7
                }
                self.agent_weights[agent_type] = default_weights[agent_type]
    
    def _calculate_consensus(self, decisions: Dict[AgentType, AgentDecision]) -> Optional[str]:
        """Проверить консенсус агентов"""
        buy_votes = sum(1 for d in decisions.values() if d.decision == "BUY")
        sell_votes = sum(1 for d in decisions.values() if d.decision == "SELL")
        
        # Консенсус = 2+ агента согласны
        if buy_votes >= 2:
            return "BUY"
        elif sell_votes >= 2:
            return "SELL"
        
        return None
    
    def decide(self, market_data: Dict, ai_analysis: Dict) -> Dict:
        """
        Принять решение с учётом всех агентов
        
        Returns:
            {
                'decision': 'BUY'/'SELL'/'SKIP',
                'selected_agent': AgentType,
                'confidence': float,
                'risk_score': int,
                'position_size_pct': float,
                'reasoning': str,
                'all_decisions': Dict[AgentType, AgentDecision],
                'consensus': bool
            }
        """
        self.stats['total_decisions'] += 1
        self._update_weights()
        
        # Собираем решения от всех агентов
        decisions: Dict[AgentType, AgentDecision] = {}
        
        for agent_type, agent in self.agents.items():
            decision = agent.evaluate(market_data, ai_analysis)
            decisions[agent_type] = decision
        
        # Проверяем консенсус
        consensus = self._calculate_consensus(decisions)
        
        if consensus:
            self.stats['consensus_decisions'] += 1
            
            # Выбираем лучшего агента среди согласных
            best_agent = None
            best_score = -1
            
            for agent_type, decision in decisions.items():
                if decision.decision == consensus:
                    # Score = confidence * weight
                    score = decision.confidence * self.agent_weights[agent_type]
                    if score > best_score:
                        best_score = score
                        best_agent = agent_type
            
            if best_agent:
                selected = decisions[best_agent]
                self._record_selection(best_agent)
                
                return {
                    'decision': consensus,
                    'selected_agent': best_agent,
                    'confidence': selected.confidence,
                    'risk_score': selected.risk_score,
                    'position_size_pct': selected.position_size_pct,
                    'reasoning': f"[{best_agent.value}] {selected.reasoning} | Consensus: {consensus}",
                    'all_decisions': decisions,
                    'consensus': True
                }
        
        # Нет консенсуса - выбираем по весам
        self.stats['no_consensus'] += 1
        
        best_agent = None
        best_score = -1
        
        for agent_type, decision in decisions.items():
            if decision.decision in ["BUY", "SELL"]:
                score = decision.confidence * self.agent_weights[agent_type]
                if score > best_score:
                    best_score = score
                    best_agent = agent_type
        
        if best_agent and best_score > 0.5:  # Минимальный порог
            selected = decisions[best_agent]
            self._record_selection(best_agent)
            
            return {
                'decision': selected.decision,
                'selected_agent': best_agent,
                'confidence': selected.confidence * 0.8,  # Снижаем без консенсуса
                'risk_score': selected.risk_score,
                'position_size_pct': selected.position_size_pct * 0.7,  # Уменьшаем размер
                'reasoning': f"[{best_agent.value}] {selected.reasoning} | No consensus (reduced size)",
                'all_decisions': decisions,
                'consensus': False
            }
        
        # Все агенты говорят SKIP
        return {
            'decision': 'SKIP',
            'selected_agent': None,
            'confidence': 0,
            'risk_score': 10,
            'position_size_pct': 0,
            'reasoning': "All agents: SKIP",
            'all_decisions': decisions,
            'consensus': False
        }
    
    def _record_selection(self, agent_type: AgentType):
        """Записать выбор агента"""
        if agent_type == AgentType.CONSERVATIVE:
            self.stats['conservative_selected'] += 1
        elif agent_type == AgentType.BALANCED:
            self.stats['balanced_selected'] += 1
        elif agent_type == AgentType.AGGRESSIVE:
            self.stats['aggressive_selected'] += 1
    
    def record_trade_result(self, agent_type: AgentType, pnl: float):
        """Записать результат сделки для агента"""
        if agent_type in self.agents:
            self.agents[agent_type].record_trade(pnl)
    
    def print_stats(self):
        """Вывести статистику"""
        print(f"\n🤖 MULTI-AGENT SYSTEM STATS:")
        print(f"   Total Decisions: {self.stats['total_decisions']}")
        print(f"   Consensus: {self.stats['consensus_decisions']} ({self.stats['consensus_decisions']/max(1,self.stats['total_decisions'])*100:.1f}%)")
        print(f"   No Consensus: {self.stats['no_consensus']}")
        
        print(f"\n   Agent Selection:")
        print(f"   - Conservative: {self.stats['conservative_selected']}")
        print(f"   - Balanced: {self.stats['balanced_selected']}")
        print(f"   - Aggressive: {self.stats['aggressive_selected']}")
        
        print(f"\n   Agent Weights:")
        for agent_type, weight in self.agent_weights.items():
            print(f"   - {agent_type.value}: {weight:.2f}")
        
        print(f"\n   Agent Performance:")
        for agent_type, agent in self.agents.items():
            s = agent.stats
            print(f"   - {agent_type.value}: {s.total_trades} trades, {s.win_rate:.1f}% WR, ${s.total_pnl:+.2f} PnL")


# Singleton
_meta_agent = None

def get_meta_agent() -> MetaAgent:
    """Получить singleton instance"""
    global _meta_agent
    if _meta_agent is None:
        _meta_agent = MetaAgent()
    return _meta_agent
