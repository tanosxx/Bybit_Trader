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
        
        # Decision Reasoning (per symbol) - WHY ML made this decision
        self.decision_reasoning: Dict[str, Dict] = {}  # {Symbol: {filters, indicators, scores}}
        
        # Active Positions
        self.active_positions: List[str] = []  # List of symbols with open positions
        
        # System Status
        self.bot_running: bool = False
        self.last_scan_time: Optional[datetime] = None
        self.total_decisions: int = 0
        
        # Trading Performance
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_pnl: float = 0.0
        self.current_balance: float = 0.0
        self.performance_24h: float = 0.0
        
        # Recent Trades (last 5)
        self.recent_trades: List[Dict] = []
        
        # Price Changes (24h)
        self.price_changes_24h: Dict[str, float] = {}  # {Symbol: % change}
        
        # Volume data
        self.volumes: Dict[str, float] = {}  # {Symbol: volume}
        
        # AI Reasoning Text (NEW - для Neural HUD)
        self.ai_reasoning_text: str = "Waiting for AI analysis..."  # Полное объяснение от Strategic Brain
        self.news_analysis_text: str = "No news analysis yet..."  # Анализ новостей
        
        # Decision Flow State (NEW - для интерактивной схемы)
        self.decision_flow: Dict[str, any] = {
            'step_0_strategic': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_1_trading_hours': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_2_chop_filter': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_3_pattern_filter': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_4_ml_confidence': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_5_fee_check': {'status': 'pending', 'result': None, 'time_ms': 0},
            'step_6_futures_brain': {'status': 'pending', 'result': None, 'time_ms': 0},
            'final_decision': {'action': 'SKIP', 'reason': 'Not analyzed yet'}
        }
        
        self._initialized = True
    
    # ========== UPDATE METHODS ==========
    
    def update_strategic(self, regime: str, reason: str = ""):
        """Обновить данные Strategic Brain"""
        with self._lock:
            self.strategic_regime = regime
            self.strategic_reason = reason or f"Market regime: {regime}"
            self.strategic_last_update = datetime.now()
        self.save_to_file()  # Сохраняем в файл для dashboard
    
    def update_news(self, sentiment: float, headline: str, count: int = 0):
        """Обновить данные News Brain"""
        with self._lock:
            self.news_sentiment = sentiment
            self.latest_headline = headline
            self.news_count = count
            self.news_last_update = datetime.now()
        self.save_to_file()
    
    def update_market_data(self, symbol: str, chop: float = None, rsi: float = None, price: float = None):
        """Обновить рыночные индикаторы для символа"""
        with self._lock:
            if chop is not None:
                self.chop_index[symbol] = chop
            if rsi is not None:
                self.rsi_values[symbol] = rsi
            if price is not None:
                self.current_prices[symbol] = price
        self.save_to_file()
    
    def update_ml_prediction(self, symbol: str, decision: str, confidence: float, change_pct: float):
        """Обновить ML предсказание для символа"""
        with self._lock:
            self.ml_predictions[symbol] = {
                'decision': decision,
                'confidence': confidence,
                'change_pct': change_pct,
                'timestamp': datetime.now().isoformat()
            }
        self.save_to_file()
    
    def update_gatekeeper(self, symbol: str, status: str):
        """Обновить статус Gatekeeper для символа"""
        with self._lock:
            self.gatekeeper_status[symbol] = status
        self.save_to_file()
    
    def update_decision_reasoning(self, symbol: str, reasoning: Dict):
        """Обновить reasoning для решения по символу"""
        with self._lock:
            self.decision_reasoning[symbol] = reasoning
        self.save_to_file()
    
    def update_positions(self, positions: List[str]):
        """Обновить список активных позиций"""
        with self._lock:
            self.active_positions = positions
        self.save_to_file()
    
    def update_system_status(self, running: bool = None, scan_time: datetime = None):
        """Обновить системный статус"""
        with self._lock:
            if running is not None:
                self.bot_running = running
            if scan_time is not None:
                self.last_scan_time = scan_time
            self.total_decisions += 1
        self.save_to_file()
    
    def update_trading_performance(self, total_trades: int = None, winning_trades: int = None, 
                                   losing_trades: int = None, total_pnl: float = None,
                                   current_balance: float = None, performance_24h: float = None):
        """Обновить торговую статистику"""
        with self._lock:
            if total_trades is not None:
                self.total_trades = total_trades
            if winning_trades is not None:
                self.winning_trades = winning_trades
            if losing_trades is not None:
                self.losing_trades = losing_trades
            if total_pnl is not None:
                self.total_pnl = total_pnl
            if current_balance is not None:
                self.current_balance = current_balance
            if performance_24h is not None:
                self.performance_24h = performance_24h
        self.save_to_file()
    
    def add_recent_trade(self, trade: Dict):
        """Добавить сделку в список последних (макс 5)"""
        with self._lock:
            self.recent_trades.insert(0, trade)  # Добавляем в начало
            self.recent_trades = self.recent_trades[:5]  # Оставляем только 5
        self.save_to_file()
    
    def update_price_change_24h(self, symbol: str, change_pct: float):
        """Обновить изменение цены за 24ч"""
        with self._lock:
            self.price_changes_24h[symbol] = change_pct
        self.save_to_file()
    
    def update_volume(self, symbol: str, volume: float):
        """Обновить объём торгов"""
        with self._lock:
            self.volumes[symbol] = volume
        self.save_to_file()
    
    def update_ai_reasoning(self, reasoning_text: str, news_analysis: str = None):
        """Обновить текстовое объяснение AI (Strategic Brain + News)"""
        with self._lock:
            self.ai_reasoning_text = reasoning_text
            if news_analysis:
                self.news_analysis_text = news_analysis
        self.save_to_file()
    
    def update_decision_flow(self, step: str, status: str, result: any = None, time_ms: float = 0):
        """Обновить состояние шага в decision flow"""
        with self._lock:
            if step in self.decision_flow:
                self.decision_flow[step] = {
                    'status': status,  # 'pending', 'pass', 'fail', 'skip'
                    'result': result,
                    'time_ms': time_ms
                }
        self.save_to_file()
    
    def set_final_decision(self, action: str, reason: str):
        """Установить финальное решение"""
        with self._lock:
            self.decision_flow['final_decision'] = {
                'action': action,  # 'BUY', 'SELL', 'SKIP'
                'reason': reason
            }
        self.save_to_file()
    
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
                'decision_reasoning': self.decision_reasoning,
                'positions': {
                    'active': self.active_positions,
                    'count': len(self.active_positions)
                },
                'system': {
                    'bot_running': self.bot_running,
                    'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
                    'total_decisions': self.total_decisions
                },
                'performance': {
                    'total_trades': self.total_trades,
                    'winning_trades': self.winning_trades,
                    'losing_trades': self.losing_trades,
                    'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                    'total_pnl': self.total_pnl,
                    'current_balance': self.current_balance,
                    'performance_24h': self.performance_24h
                },
                'recent_trades': self.recent_trades,
                'price_changes_24h': self.price_changes_24h,
                'volumes': self.volumes,
                'ai_reasoning': {
                    'strategic_text': self.ai_reasoning_text,
                    'news_analysis': self.news_analysis_text
                },
                'decision_flow': self.decision_flow
            }
    
    def to_json(self) -> str:
        """Экспорт в JSON строку"""
        return json.dumps(self.to_dict(), indent=2)
    
    def save_to_file(self, filepath: str = "/app/ml_data/brain_state.json"):
        """Сохранить состояние в файл (для передачи между контейнерами)"""
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(self.to_json())
        except Exception as e:
            print(f"⚠️ Failed to save brain state: {e}")
    
    def load_from_file(self, filepath: str = "/app/ml_data/brain_state.json") -> bool:
        """Загрузить состояние из файла"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            with self._lock:
                # Strategic
                if 'strategic' in data:
                    self.strategic_regime = data['strategic'].get('regime', 'SIDEWAYS')
                    self.strategic_reason = data['strategic'].get('reason', '')
                    last_update = data['strategic'].get('last_update')
                    if last_update:
                        self.strategic_last_update = datetime.fromisoformat(last_update)
                
                # News
                if 'news' in data:
                    self.news_sentiment = data['news'].get('sentiment', 0.0)
                    self.latest_headline = data['news'].get('latest_headline', 'No news yet')
                    self.news_count = data['news'].get('count', 0)
                    last_update = data['news'].get('last_update')
                    if last_update:
                        self.news_last_update = datetime.fromisoformat(last_update)
                
                # Market
                if 'market' in data:
                    self.chop_index = data['market'].get('chop_index', {})
                    self.rsi_values = data['market'].get('rsi_values', {})
                    self.current_prices = data['market'].get('current_prices', {})
                
                # ML Predictions
                if 'ml_predictions' in data:
                    self.ml_predictions = data['ml_predictions']
                
                # Gatekeeper
                if 'gatekeeper' in data:
                    self.gatekeeper_status = data['gatekeeper']
                
                # Decision Reasoning
                if 'decision_reasoning' in data:
                    self.decision_reasoning = data['decision_reasoning']
                
                # Positions
                if 'positions' in data:
                    self.active_positions = data['positions'].get('active', [])
                
                # System
                if 'system' in data:
                    self.bot_running = data['system'].get('bot_running', False)
                    self.total_decisions = data['system'].get('total_decisions', 0)
                    last_scan = data['system'].get('last_scan')
                    if last_scan:
                        self.last_scan_time = datetime.fromisoformat(last_scan)
                
                # Performance
                if 'performance' in data:
                    self.total_trades = data['performance'].get('total_trades', 0)
                    self.winning_trades = data['performance'].get('winning_trades', 0)
                    self.losing_trades = data['performance'].get('losing_trades', 0)
                    self.total_pnl = data['performance'].get('total_pnl', 0.0)
                    self.current_balance = data['performance'].get('current_balance', 0.0)
                    self.performance_24h = data['performance'].get('performance_24h', 0.0)
                
                # Recent Trades
                if 'recent_trades' in data:
                    self.recent_trades = data['recent_trades']
                
                # Price Changes 24h
                if 'price_changes_24h' in data:
                    self.price_changes_24h = data['price_changes_24h']
                
                # Volumes
                if 'volumes' in data:
                    self.volumes = data['volumes']
                
                # AI Reasoning
                if 'ai_reasoning' in data:
                    self.ai_reasoning_text = data['ai_reasoning'].get('strategic_text', 'Waiting...')
                    self.news_analysis_text = data['ai_reasoning'].get('news_analysis', 'No news...')
                
                # Decision Flow
                if 'decision_flow' in data:
                    self.decision_flow = data['decision_flow']
            
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"⚠️ Failed to load brain state: {e}")
            return False
    
    def reset(self):
        """Сброс всех данных (для тестов)"""
        with self._lock:
            self.__init__()


# Singleton getter
def get_global_brain_state() -> GlobalBrainState:
    """Получить singleton instance GlobalBrainState"""
    return GlobalBrainState()
