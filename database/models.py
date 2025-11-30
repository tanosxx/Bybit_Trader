"""
SQLAlchemy модели для Bybit_Trader
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, JSON, Boolean
import enum
from .db import Base


class LogLevel(str, enum.Enum):
    """Уровни логирования"""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    BUY = "BUY"
    SELL = "SELL"
    DEBUG = "DEBUG"


class TradeStatus(str, enum.Enum):
    """Статусы сделок"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TradeSide(str, enum.Enum):
    """Сторона сделки"""
    BUY = "BUY"
    SELL = "SELL"


class SystemLog(Base):
    """Системные логи"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    level = Column(Enum(LogLevel), nullable=False, index=True)
    component = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    ai_reasoning = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<SystemLog {self.time} [{self.level}] {self.component}: {self.message[:50]}>"


class WalletHistory(Base):
    """История изменений баланса"""
    __tablename__ = "wallet_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    balance_usdt = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    change_amount = Column(Float, default=0.0)
    change_reason = Column(String(200), nullable=False)
    trade_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<WalletHistory {self.time} Balance: ${self.balance_usdt:.2f} ({self.change_reason})>"


class Trade(Base):
    """Торговые сделки"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(TradeSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_reason = Column(String(200), nullable=True)  # Причина закрытия
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN, nullable=False, index=True)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    fee_entry = Column(Float, default=0.0)
    fee_exit = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    ai_risk_score = Column(Float, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    
    # ========== HYBRID TRADING ==========
    market_type = Column(String(20), default='spot', nullable=False, index=True)  # 'spot' или 'futures'
    
    extra_data = Column(JSON, nullable=True)  # agent_type, indicators, leverage, position_side, etc.
    
    def __repr__(self):
        return f"<Trade {self.id} [{self.market_type}] {self.side} {self.symbol} @ ${self.entry_price:.2f} [{self.status}]>"
    
    @property
    def total_cost(self):
        """Полная стоимость сделки"""
        return (self.entry_price * self.quantity) + self.fee_entry
    
    @property
    def is_futures(self):
        """Проверить, фьючерсная ли сделка"""
        return self.market_type == 'futures'
    
    @property
    def is_spot(self):
        """Проверить, спотовая ли сделка"""
        return self.market_type == 'spot'


class Candle(Base):
    """Исторические свечи (для анализа и обучения)"""
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False)  # 1, 5, 15, 60
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    def __repr__(self):
        return f"<Candle {self.symbol} {self.interval} {self.timestamp} C:{self.close}>"


class AppConfig(Base):
    """Настройки приложения"""
    __tablename__ = "app_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AppConfig {self.key}={self.value}>"


class AIDecision(Base):
    """Полное логирование AI решений для анализа"""
    __tablename__ = "ai_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    # Рыночные данные
    price = Column(Float, nullable=True)
    rsi = Column(Float, nullable=True)
    macd = Column(String(20), nullable=True)  # bullish/bearish
    trend = Column(String(50), nullable=True)
    
    # News Brain
    news_sentiment = Column(String(20), nullable=True)  # FEAR/GREED/NEUTRAL
    news_score = Column(Float, nullable=True)
    
    # ML Predictor
    ml_signal = Column(String(10), nullable=True)  # BUY/SELL/HOLD
    ml_confidence = Column(Float, nullable=True)
    ml_predicted_change = Column(Float, nullable=True)
    
    # Local Brain решение
    local_decision = Column(String(10), nullable=True)  # BUY/SELL/HOLD/SKIP
    local_confidence = Column(Float, nullable=True)
    local_risk = Column(Integer, nullable=True)
    
    # Multi-Agent
    agent_consensus = Column(Boolean, nullable=True)
    agent_conservative = Column(Boolean, nullable=True)
    agent_balanced = Column(Boolean, nullable=True)
    agent_aggressive = Column(Boolean, nullable=True)
    
    # Futures Brain
    futures_action = Column(String(10), nullable=True)  # LONG/SHORT/SKIP
    futures_score = Column(Integer, nullable=True)
    futures_confidence = Column(Float, nullable=True)
    futures_leverage = Column(Integer, nullable=True)
    
    # Итоговое действие
    final_action = Column(String(20), nullable=True)  # EXECUTED/SKIPPED/BLOCKED
    execution_reason = Column(String(200), nullable=True)
    
    # Дополнительные данные
    extra_data = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AIDecision {self.time} {self.symbol} {self.final_action}>"
