"""
Technical Analysis Library v2.0
МОДУЛЬ 2: Динамический Риск-менеджмент

Функции:
- Динамический расчёт SL/TP на основе ATR
- Адаптивный размер позиции (волатильность + баланс)
- Trailing Stop Loss
- Risk/Reward оптимизация
- Корреляция позиций
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """Уровни риска"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class MarketRegime(Enum):
    """Режим рынка"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CHOPPY = "CHOPPY"  # Боковой с высоким шумом


class TradingRecommendation(Enum):
    """Рекомендация по торговле"""
    TRADE = "TRADE"
    REDUCE_SIZE = "REDUCE_SIZE"
    SKIP = "SKIP"
    CLOSE_ALL = "CLOSE_ALL"


@dataclass
class RiskParameters:
    """Параметры риска для сделки"""
    stop_loss_price: float
    take_profit_price: float
    position_size_usd: float
    position_size_qty: float
    risk_amount_usd: float
    reward_amount_usd: float
    risk_reward_ratio: float
    risk_percent: float
    atr_value: float
    volatility_adjusted: bool
    trailing_stop_distance: float


class DynamicRiskManager:
    """Динамический риск-менеджер с ATR-based SL/TP"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.atr_multiplier_sl = self.config.get('atr_multiplier_sl', 2.0)
        self.atr_multiplier_tp = self.config.get('atr_multiplier_tp', 3.0)
        self.stats = {'calculations': 0, 'risk_adjusted': 0}
    
    def calculate_atr(self, klines: List[Dict], period: int = 14) -> float:
        """Рассчитать ATR (Average True Range)"""
        if len(klines) < period + 1:
            return 0.0
        df = pd.DataFrame(klines)
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['prev_close'])
        df['tr3'] = abs(df['low'] - df['prev_close'])
        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr = df['true_range'].rolling(window=period).mean().iloc[-1]
        return float(atr) if not np.isnan(atr) else 0.0
    
    def calculate_volatility(self, klines: List[Dict], period: int = 20) -> Dict:
        """Рассчитать метрики волатильности"""
        if len(klines) < period:
            return {'atr': 0.0, 'atr_percent': 0.0, 'std_dev': 0.0, 'regime': MarketRegime.RANGING}
        df = pd.DataFrame(klines)
        current_price = df['close'].iloc[-1]
        atr = self.calculate_atr(klines, period)
        atr_percent = (atr / current_price) * 100 if current_price > 0 else 0
        df['returns'] = df['close'].pct_change()
        std_dev = df['returns'].rolling(window=period).std().iloc[-1] * 100
        regime = self._detect_market_regime(df, atr_percent)
        return {'atr': atr, 'atr_percent': atr_percent, 'std_dev': std_dev if not np.isnan(std_dev) else 0.0, 'regime': regime}
    
    def _detect_market_regime(self, df: pd.DataFrame, atr_percent: float) -> MarketRegime:
        """Определить режим рынка"""
        if len(df) < 50:
            return MarketRegime.RANGING
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Проверяем волатильность
        if atr_percent > 4.0:
            return MarketRegime.HIGH_VOLATILITY
        elif atr_percent < 0.3:
            return MarketRegime.LOW_VOLATILITY
        
        # Проверяем тренд
        if current_price > ema_20 > ema_50:
            return MarketRegime.TRENDING_UP
        elif current_price < ema_20 < ema_50:
            return MarketRegime.TRENDING_DOWN
        
        # Проверяем choppy market (много пересечений EMA)
        ema_20_series = df['close'].ewm(span=20).mean()
        ema_50_series = df['close'].ewm(span=50).mean()
        crossovers = ((ema_20_series > ema_50_series) != (ema_20_series.shift(1) > ema_50_series.shift(1))).sum()
        if crossovers > 5:  # Много пересечений за период
            return MarketRegime.CHOPPY
        
        return MarketRegime.RANGING
    
    def get_trading_recommendation(self, klines: List[Dict]) -> Dict:
        """Получить рекомендацию по торговле на основе режима рынка"""
        volatility = self.calculate_volatility(klines)
        regime = volatility['regime']
        atr_pct = volatility['atr_percent']
        
        recommendations = {
            MarketRegime.TRENDING_UP: (TradingRecommendation.TRADE, 1.0, "Uptrend - full size"),
            MarketRegime.TRENDING_DOWN: (TradingRecommendation.TRADE, 1.0, "Downtrend - full size"),
            MarketRegime.RANGING: (TradingRecommendation.REDUCE_SIZE, 0.5, "Ranging - reduce size 50%"),
            MarketRegime.CHOPPY: (TradingRecommendation.REDUCE_SIZE, 0.3, "Choppy market - reduce size 70%"),
            MarketRegime.HIGH_VOLATILITY: (TradingRecommendation.REDUCE_SIZE, 0.5, "High volatility - reduce size 50%"),
            MarketRegime.LOW_VOLATILITY: (TradingRecommendation.REDUCE_SIZE, 0.3, "Low volatility - reduce size 70%"),
        }
        
        rec, size_mult, reason = recommendations.get(regime, (TradingRecommendation.TRADE, 1.0, "Default"))
        
        return {
            'recommendation': rec,
            'regime': regime,
            'size_multiplier': size_mult,
            'reason': reason,
            'atr_percent': atr_pct,
            'can_trade': rec in [TradingRecommendation.TRADE, TradingRecommendation.REDUCE_SIZE]
        }
    
    def calculate_dynamic_sl_tp(self, entry_price: float, side: str, klines: List[Dict], 
                                 atr_sl_multiplier: float = None, atr_tp_multiplier: float = None) -> Tuple[float, float]:
        """Рассчитать динамический SL/TP на основе ATR"""
        atr = self.calculate_atr(klines)
        if atr == 0:
            if side == 'BUY':
                return entry_price * 0.98, entry_price * 1.03
            else:
                return entry_price * 1.02, entry_price * 0.97
        sl_mult = atr_sl_multiplier or self.atr_multiplier_sl
        tp_mult = atr_tp_multiplier or self.atr_multiplier_tp
        if side == 'BUY':
            stop_loss = entry_price - (atr * sl_mult)
            take_profit = entry_price + (atr * tp_mult)
        else:
            stop_loss = entry_price + (atr * sl_mult)
            take_profit = entry_price - (atr * tp_mult)
        return round(stop_loss, 2), round(take_profit, 2)
    
    def calculate_position_size(self, balance: float, entry_price: float, stop_loss: float,
                                 risk_level: RiskLevel = RiskLevel.MEDIUM, max_position_pct: float = 0.20) -> Dict:
        """Рассчитать размер позиции на основе риска"""
        risk_pct_map = {RiskLevel.VERY_LOW: 0.005, RiskLevel.LOW: 0.01, RiskLevel.MEDIUM: 0.02, RiskLevel.HIGH: 0.03, RiskLevel.VERY_HIGH: 0.05}
        risk_percent = risk_pct_map.get(risk_level, 0.02)
        risk_amount_usd = balance * risk_percent
        sl_distance = abs(entry_price - stop_loss)
        sl_distance_pct = sl_distance / entry_price if sl_distance > 0 else 0.02
        position_size_usd = min(risk_amount_usd / sl_distance_pct, balance * max_position_pct)
        position_size_qty = position_size_usd / entry_price
        self.stats['calculations'] += 1
        return {'position_size_usd': round(position_size_usd, 2), 'position_size_qty': round(position_size_qty, 8),
                'risk_amount_usd': round(risk_amount_usd, 2), 'risk_percent': risk_percent * 100}

    
    def calculate_kelly_position(self, balance: float, entry_price: float, stop_loss: float,
                                  take_profit: float, win_rate: float, max_kelly_fraction: float = 0.25) -> Dict:
        """Рассчитать размер позиции по Kelly Criterion"""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk == 0:
            return {'kelly_percent': 0, 'adjusted_kelly': 0, 'position_size_usd': 0, 'position_size_qty': 0, 'risk_reward_ratio': 0}
        rr_ratio = reward / risk
        kelly = max(0, min(win_rate - ((1 - win_rate) / rr_ratio), max_kelly_fraction))
        adjusted_kelly = kelly * 0.5
        position_size_usd = balance * adjusted_kelly
        return {'kelly_percent': round(kelly * 100, 2), 'adjusted_kelly': round(adjusted_kelly * 100, 2),
                'position_size_usd': round(position_size_usd, 2), 'position_size_qty': round(position_size_usd / entry_price, 8),
                'risk_reward_ratio': round(rr_ratio, 2)}
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float, side: str,
                                 initial_stop_loss: float, trailing_percent: float = None, klines: List[Dict] = None) -> Dict:
        """Рассчитать Trailing Stop Loss"""
        if trailing_percent:
            trailing_distance = current_price * (trailing_percent / 100)
        elif klines:
            trailing_distance = self.calculate_atr(klines) * 1.5
        else:
            trailing_distance = current_price * 0.015
        if side == 'BUY':
            potential_new_sl = current_price - trailing_distance
            if potential_new_sl > initial_stop_loss:
                profit_locked = potential_new_sl - entry_price
                return {'new_stop_loss': round(potential_new_sl, 2), 'trailing_distance': round(trailing_distance, 2),
                        'profit_locked': round(profit_locked, 2), 'profit_locked_pct': round((profit_locked / entry_price) * 100, 2), 'should_update': True}
        else:
            potential_new_sl = current_price + trailing_distance
            if potential_new_sl < initial_stop_loss:
                profit_locked = entry_price - potential_new_sl
                return {'new_stop_loss': round(potential_new_sl, 2), 'trailing_distance': round(trailing_distance, 2),
                        'profit_locked': round(profit_locked, 2), 'profit_locked_pct': round((profit_locked / entry_price) * 100, 2), 'should_update': True}
        return {'new_stop_loss': initial_stop_loss, 'trailing_distance': round(trailing_distance, 2), 'profit_locked': 0, 'profit_locked_pct': 0, 'should_update': False}
    
    def calculate_full_risk_params(self, balance: float, entry_price: float, side: str, klines: List[Dict],
                                    risk_level: RiskLevel = RiskLevel.MEDIUM, win_rate: float = 0.55) -> RiskParameters:
        """Рассчитать все параметры риска для сделки"""
        volatility = self.calculate_volatility(klines)
        atr = volatility['atr']
        regime = volatility['regime']
        if regime == MarketRegime.HIGH_VOLATILITY:
            sl_mult, tp_mult = 2.5, 4.0
        elif regime == MarketRegime.LOW_VOLATILITY:
            sl_mult, tp_mult = 1.5, 2.5
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            sl_mult, tp_mult = 2.0, 3.5
        else:
            sl_mult, tp_mult = 2.0, 3.0
        stop_loss, take_profit = self.calculate_dynamic_sl_tp(entry_price, side, klines, sl_mult, tp_mult)
        position_data = self.calculate_position_size(balance, entry_price, stop_loss, risk_level)
        kelly_data = self.calculate_kelly_position(balance, entry_price, stop_loss, take_profit, win_rate)
        final_position_usd = min(position_data['position_size_usd'], kelly_data['position_size_usd']) if kelly_data['position_size_usd'] > 0 else position_data['position_size_usd']
        final_position_qty = final_position_usd / entry_price
        risk_amount = abs(entry_price - stop_loss) * final_position_qty
        reward_amount = abs(take_profit - entry_price) * final_position_qty
        rr_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        trailing_distance = atr * 1.5 if atr > 0 else entry_price * 0.015
        self.stats['risk_adjusted'] += 1
        return RiskParameters(stop_loss_price=stop_loss, take_profit_price=take_profit, position_size_usd=round(final_position_usd, 2),
                              position_size_qty=round(final_position_qty, 8), risk_amount_usd=round(risk_amount, 2), reward_amount_usd=round(reward_amount, 2),
                              risk_reward_ratio=round(rr_ratio, 2), risk_percent=position_data['risk_percent'], atr_value=round(atr, 2),
                              volatility_adjusted=regime != MarketRegime.RANGING, trailing_stop_distance=round(trailing_distance, 2))



class PortfolioRiskManager:
    """Управление рисками на уровне портфеля"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_portfolio_risk = self.config.get('max_portfolio_risk', 0.10)
        self.max_daily_loss = self.config.get('max_daily_loss', 0.05)
        self.max_drawdown = self.config.get('max_drawdown', 0.20)
        self.max_positions = self.config.get('max_positions', 5)
        self.max_correlation = self.config.get('max_correlation', 0.7)
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.last_reset_date = datetime.utcnow().date()
        self.correlation_matrix = {
            ('BTCUSDT', 'ETHUSDT'): 0.85, ('BTCUSDT', 'SOLUSDT'): 0.75, ('BTCUSDT', 'BNBUSDT'): 0.70,
            ('BTCUSDT', 'XRPUSDT'): 0.65, ('ETHUSDT', 'SOLUSDT'): 0.80, ('ETHUSDT', 'BNBUSDT'): 0.65,
            ('ETHUSDT', 'XRPUSDT'): 0.60, ('SOLUSDT', 'BNBUSDT'): 0.55, ('SOLUSDT', 'XRPUSDT'): 0.50, ('BNBUSDT', 'XRPUSDT'): 0.45
        }
    
    def check_daily_limit(self, current_pnl: float, balance: float) -> Dict:
        """Проверить дневной лимит убытков"""
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today
        self.daily_pnl = current_pnl
        daily_pnl_pct = (self.daily_pnl / balance) * 100 if balance > 0 else 0
        max_loss_usd = balance * self.max_daily_loss
        can_trade = self.daily_pnl > -max_loss_usd
        return {'can_trade': can_trade, 'daily_pnl': round(self.daily_pnl, 2), 'daily_pnl_pct': round(daily_pnl_pct, 2),
                'remaining_risk': round(max(0, max_loss_usd + self.daily_pnl), 2), 'max_daily_loss': round(max_loss_usd, 2)}
    
    def check_drawdown(self, current_balance: float) -> Dict:
        """Проверить просадку от пика"""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance if self.peak_balance > 0 else 0
        can_trade = self.current_drawdown < self.max_drawdown
        return {'can_trade': can_trade, 'current_drawdown': round(self.current_drawdown * 100, 2),
                'peak_balance': round(self.peak_balance, 2), 'max_drawdown': self.max_drawdown * 100, 'emergency_stop': not can_trade}
    
    def check_correlation(self, new_symbol: str, open_positions: List[Dict]) -> Dict:
        """Проверить корреляцию с открытыми позициями"""
        correlated = []
        total_correlated_exposure = 0.0
        for pos in open_positions:
            pos_symbol = pos.get('symbol', '')
            pos_size = pos.get('size_usd', 0)
            correlation = self.correlation_matrix.get((new_symbol, pos_symbol)) or self.correlation_matrix.get((pos_symbol, new_symbol)) or 0
            if correlation >= self.max_correlation:
                correlated.append({'symbol': pos_symbol, 'correlation': correlation, 'size_usd': pos_size})
                total_correlated_exposure += pos_size
        can_open = len(correlated) == 0
        recommendation = f"⚠️ Высокая корреляция с {[c['symbol'] for c in correlated]}" if correlated else "✅ OK"
        return {'can_open': can_open, 'correlated_positions': correlated, 'total_correlated_exposure': round(total_correlated_exposure, 2), 'recommendation': recommendation}
    
    def check_portfolio_risk(self, balance: float, open_positions: List[Dict], new_position_risk: float) -> Dict:
        """Проверить общий риск портфеля"""
        current_risk = sum(pos.get('risk_amount', 0) for pos in open_positions)
        new_total_risk = current_risk + new_position_risk
        max_risk_usd = balance * self.max_portfolio_risk
        can_open = new_total_risk <= max_risk_usd
        return {'can_open': can_open, 'current_portfolio_risk': round(current_risk, 2),
                'current_portfolio_risk_pct': round((current_risk / balance) * 100, 2) if balance > 0 else 0,
                'new_portfolio_risk': round(new_total_risk, 2), 'new_portfolio_risk_pct': round((new_total_risk / balance) * 100, 2) if balance > 0 else 0,
                'max_allowed_risk': round(max_risk_usd, 2), 'max_allowed_risk_pct': self.max_portfolio_risk * 100}
    
    def full_risk_check(self, balance: float, daily_pnl: float, open_positions: List[Dict], new_symbol: str, new_position_risk: float) -> Dict:
        """Полная проверка рисков перед открытием позиции"""
        reasons = []
        daily_check = self.check_daily_limit(daily_pnl, balance)
        if not daily_check['can_trade']:
            reasons.append(f"❌ Дневной лимит: ${daily_check['daily_pnl']:.2f}")
        drawdown_check = self.check_drawdown(balance)
        if not drawdown_check['can_trade']:
            reasons.append(f"❌ Просадка: {drawdown_check['current_drawdown']:.1f}%")
        correlation_check = self.check_correlation(new_symbol, open_positions)
        if not correlation_check['can_open']:
            reasons.append(f"⚠️ Корреляция: {correlation_check['recommendation']}")
        portfolio_check = self.check_portfolio_risk(balance, open_positions, new_position_risk)
        if not portfolio_check['can_open']:
            reasons.append(f"❌ Портфель: {portfolio_check['new_portfolio_risk_pct']:.1f}%")
        if len(open_positions) >= self.max_positions:
            reasons.append(f"❌ Макс позиций: {len(open_positions)}/{self.max_positions}")
        return {'can_trade': len(reasons) == 0, 'reasons': reasons, 'daily_check': daily_check,
                'drawdown_check': drawdown_check, 'correlation_check': correlation_check, 'portfolio_check': portfolio_check}


# Singletons
_dynamic_risk_manager = None
_portfolio_risk_manager = None

def get_dynamic_risk_manager(config: Dict = None) -> DynamicRiskManager:
    global _dynamic_risk_manager
    if _dynamic_risk_manager is None:
        _dynamic_risk_manager = DynamicRiskManager(config)
    return _dynamic_risk_manager

def get_portfolio_risk_manager(config: Dict = None) -> PortfolioRiskManager:
    global _portfolio_risk_manager
    if _portfolio_risk_manager is None:
        _portfolio_risk_manager = PortfolioRiskManager(config)
    return _portfolio_risk_manager
