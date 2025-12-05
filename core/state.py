"""
Global Brain State - Оперативная память бота
Хранит текущие "мысли" всех модулей для визуализации в Neural HUD
НИКАКИХ запросов к БД - только in-memory данные
"""

from typing import Dict, List, Optional
from datetime import datetime
from threading import Lock
import json


class GlobalBrainState:
    """
    Singleton для хранения текущего состояния всех AI модулей
    Обновляется в реальном времени при работе бота
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Strategic Brain (Claude - Генерал)
        self.strategic_regime: str = "SIDEWAYS"
        self.strategic_reason: str = "Initializing..."
        self.strategic_last_update: Optional[datetime] = None
        
        # News Brain (VADER Sentiment)
        self.news_sentiment: float = 0.0  # -1.0 to +1.0
        self.latest_headline: str = "No news yet"
        self.news_count: int = 0
        self.news_last_update: Optional[datetime] = None
        
        # Market Indicators (per symbol)
        self.chop_index: Dict[str, float] = {}  # {Symbol: CHOP value}
        self.rsi_values: Dict[str, float] = {}  # {Symbol: RSI}
        self.current_prices: Dict[str, float] = {}  # {Symbol: Price}
        
        # ML Predictions (per symbol)
        self.ml_predictions: Dict[str, Dict] = {}  # {Symbol: {decision, confidence, change_pct}}
        
        # Gatekeeper Status (per symbol)
        self.gatekeeper_status: Dict[str, str] = {}  # {Symbol: "PASS" or "BLOCK: Reason"}
        
        # Active Positions
        self.active_positions: List[str] = []  # List of symbols with open positions
        
        # System Status
        self.bot_running: bool = False
        self.last_scan_time: Optional[datetime] = None
        self.total_decisions: int = 0
        
        self._initialized = True
    
    # ========== UPDATE METHODS ==========
    
    def update_strategic(self, regime: str, reason: str = ""):
        """Обновить данные Strategic Brain"""
        with self._lock:
            self.strategic_regime = regime
            self.strategic_reason = reason or f"Market regime: {regime}"
            self.strategic_last_update = datetime.now()
    
    def update_news(self, sentiment: float, headline: str, count: int = 0):
        """Обновить данные News Brain"""
        with self._lock:
            self.news_sentiment = sentiment
            self.latest_headline = headline
            self.news_count = count
            self.news_last_update = datetime.now()
    
    def update_market_data(self, symbol: str, chop: float = None, rsi: float = None, price: float = None):
        """Обновить рыночные индикаторы для символа"""
        with self._lock:
            if chop is not None:
                self.chop_index[symbol] = chop
            if rsi is not None:
                self.rsi_values[symbol] = rsi
            if price is not None:
                self.current_prices[symbol] = price
    
    def update_ml_prediction(self, symbol: str, decision: str, confidence: float, change_pct: float):
        """Обновить ML предсказание для символа"""
        with self._lock:
            self.ml_predictions[symbol] = {
                'decision': decision,
                'confidence': confidence,
                'change_pct': change_pct,
                'timestamp': datetime.now().isoformat()
            }
    
    def update_gatekeeper(self, symbol: str, status: str):
        """Обновить статус Gatekeeper для символа"""
        with self._lock:
            self.gatekeeper_status[symbol] = status
    
    def update_positions(self, positions: List[str]):
        """Обновить список активных позиций"""
        with self._lock:
            self.active_positions = positions
    
    def update_system_status(self, running: bool = None, scan_time: datetime = None):
        """Обновить системный статус"""
        with self._lock:
            if running is not None:
                self.bot_running = running
            if scan_time is not None:
                self.last_scan_time = scan_time
            self.total_decisions += 1
    
    # ========== EXPORT METHODS ==========
    
    def to_dict(self) -> Dict:
        """Экспорт всех данных в dict для JSON API"""
        with self._lock:
            return {
                'strategic': {
                    'regime': self.strategic_regime,
                    'reason': self.strategic_reason,
                    'last_update': self.strategic_last_update.isoformat() if self.strategic_last_update else None
                },
                'news': {
                    'sentiment': self.news_sentiment,
                    'latest_headline': self.latest_headline,
                    'count': self.news_count,
                    'last_update': self.news_last_update.isoformat() if self.news_last_update else None
                },
                'market': {
                    'chop_index': self.chop_index,
                    'rsi_values': self.rsi_values,
                    'current_prices': self.current_prices
                },
                'ml_predictions': self.ml_predictions,
                'gatekeeper': self.gatekeeper_status,
                'positions': {
                    'active': self.active_positions,
                    'count': len(self.active_positions)
                },
                'system': {
                    'bot_running': self.bot_running,
                    'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
                    'total_decisions': self.total_decisions
                }
            }
    
    def to_json(self) -> str:
        """Экспорт в JSON строку"""
        return json.dumps(self.to_dict(), indent=2)
    
    def reset(self):
        """Сброс всех данных (для тестов)"""
        with self._lock:
            self.__init__()


# Singleton getter
def get_global_brain_state() -> GlobalBrainState:
    """Получить singleton instance GlobalBrainState"""
    return GlobalBrainState()
