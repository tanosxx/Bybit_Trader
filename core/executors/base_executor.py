"""
Base Executor - Абстрактный класс для исполнителей
Определяет интерфейс для SPOT и FUTURES исполнителей
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class MarketType(Enum):
    """Тип рынка"""
    SPOT = "spot"
    FUTURES = "futures"


class OrderSide(Enum):
    """Сторона ордера"""
    BUY = "Buy"
    SELL = "Sell"


class PositionSide(Enum):
    """Сторона позиции (для фьючерсов)"""
    LONG = "Long"
    SHORT = "Short"


@dataclass
class TradeSignal:
    """Торговый сигнал от AI Brain"""
    action: str  # BUY, SELL, SKIP
    confidence: float  # 0.0 - 1.0
    risk_score: int  # 1-10
    reasoning: str
    symbol: str
    price: float
    extra_data: Optional[Dict] = None  # Дополнительные данные (ml_features, etc.)
    
    @property
    def is_buy(self) -> bool:
        return self.action == "BUY"
    
    @property
    def is_sell(self) -> bool:
        return self.action == "SELL"
    
    @property
    def is_skip(self) -> bool:
        return self.action == "SKIP"


@dataclass
class ExecutionResult:
    """Результат исполнения ордера"""
    success: bool
    market_type: MarketType
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: float = 0.0
    price: float = 0.0
    pnl: float = 0.0
    error: Optional[str] = None
    extra_data: Dict = None
    
    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}


class BaseExecutor(ABC):
    """
    Абстрактный базовый класс для исполнителей
    
    Определяет общий интерфейс для SPOT и FUTURES торговли
    """
    
    def __init__(self, market_type: MarketType):
        self.market_type = market_type
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0
        }
    
    @abstractmethod
    async def execute_signal(self, signal: TradeSignal) -> ExecutionResult:
        """
        Исполнить торговый сигнал
        
        Args:
            signal: TradeSignal от AI Brain
        
        Returns:
            ExecutionResult с информацией об исполнении
        """
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str, reason: str) -> ExecutionResult:
        """
        Закрыть позицию по символу
        
        Args:
            symbol: Торговая пара
            reason: Причина закрытия
        
        Returns:
            ExecutionResult
        """
        pass
    
    @abstractmethod
    async def get_open_positions(self) -> List[Dict]:
        """
        Получить список открытых позиций
        
        Returns:
            Список позиций
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """
        Получить доступный баланс
        
        Returns:
            Баланс в USDT
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, price: float, risk_pct: float) -> float:
        """
        Рассчитать размер позиции
        
        Args:
            price: Текущая цена
            risk_pct: Процент риска
        
        Returns:
            Размер позиции в базовой валюте
        """
        pass
    
    def record_trade(self, pnl: float):
        """Записать результат сделки в статистику"""
        self.stats['total_trades'] += 1
        self.stats['total_pnl'] += pnl
        if pnl > 0:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        win_rate = 0.0
        if self.stats['total_trades'] > 0:
            win_rate = (self.stats['wins'] / self.stats['total_trades']) * 100
        
        return {
            **self.stats,
            'win_rate': win_rate,
            'market_type': self.market_type.value
        }
    
    def print_stats(self):
        """Вывести статистику"""
        s = self.get_stats()
        print(f"\n📊 {self.market_type.value.upper()} Executor Stats:")
        print(f"   Trades: {s['total_trades']} | WR: {s['win_rate']:.1f}%")
        print(f"   PnL: ${s['total_pnl']:+.2f}")
