"""
AI Decision Logger - Полное логирование AI решений в БД
Не влияет на логику торговли, только записывает данные для анализа
"""
from datetime import datetime
from database.db import async_session
from database.models import AIDecision


class AILogger:
    """Логгер AI решений - записывает все данные для анализа"""
    
    def __init__(self):
        self.enabled = True
        self.stats = {'logged': 0, 'errors': 0}
    
    async def log_decision(
        self,
        symbol: str,
        # Рыночные данные
        price: float = None,
        rsi: float = None,
        macd: str = None,
        trend: str = None,
        # News
        news_sentiment: str = None,
        news_score: float = None,
        # ML
        ml_signal: str = None,
        ml_confidence: float = None,
        ml_predicted_change: float = None,
        # Local Brain
        local_decision: str = None,
        local_confidence: float = None,
        local_risk: int = None,
        # Multi-Agent
        agent_consensus: bool = None,
        agent_conservative: bool = None,
        agent_balanced: bool = None,
        agent_aggressive: bool = None,
        # Futures Brain
        futures_action: str = None,
        futures_score: int = None,
        futures_confidence: float = None,
        futures_leverage: int = None,
        # Итог
        final_action: str = None,
        execution_reason: str = None,
        extra_data: dict = None
    ):
        """Записать AI решение в БД"""
        if not self.enabled:
            return
        
        try:
            async with async_session() as session:
                decision = AIDecision(
                    time=datetime.utcnow(),
                    symbol=symbol,
                    price=price,
                    rsi=rsi,
                    macd=macd,
                    trend=trend,
                    news_sentiment=news_sentiment,
                    news_score=news_score,
                    ml_signal=ml_signal,
                    ml_confidence=ml_confidence,
                    ml_predicted_change=ml_predicted_change,
                    local_decision=local_decision,
                    local_confidence=local_confidence,
                    local_risk=local_risk,
                    agent_consensus=agent_consensus,
                    agent_conservative=agent_conservative,
                    agent_balanced=agent_balanced,
                    agent_aggressive=agent_aggressive,
                    futures_action=futures_action,
                    futures_score=futures_score,
                    futures_confidence=futures_confidence,
                    futures_leverage=futures_leverage,
                    final_action=final_action,
                    execution_reason=execution_reason,
                    extra_data=extra_data
                )
                session.add(decision)
                await session.commit()
                self.stats['logged'] += 1
        except Exception as e:
            self.stats['errors'] += 1
            print(f"⚠️ AILogger error: {e}")
    
    def print_stats(self):
        """Вывести статистику логирования"""
        print(f"📝 AILogger: {self.stats['logged']} logged, {self.stats['errors']} errors")


# Singleton
_ai_logger = None

def get_ai_logger() -> AILogger:
    """Получить singleton экземпляр AILogger"""
    global _ai_logger
    if _ai_logger is None:
        _ai_logger = AILogger()
    return _ai_logger
