"""
Backtesting Engine v1.0
Тестирование стратегий на исторических данных

Функции:
- Загрузка исторических данных из БД или API
- Симуляция торговли с учётом комиссий
- Расчёт метрик (Sharpe, Sortino, Max Drawdown)
- Визуализация результатов
"""
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from core.technical_analyzer import TechnicalAnalyzer
from core.ta_lib import DynamicRiskManager, RiskLevel, MarketRegime
from core.indicators import add_all_indicators


class BacktestSide(Enum):
    """Сторона сделки"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BacktestTrade:
    """Сделка в бэктесте"""
    id: int
    symbol: str
    side: BacktestSide
    entry_time: datetime
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""
    fees: float = 0.0


@dataclass
class BacktestResult:
    """Результаты бэктеста"""
    # Основные метрики
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # PnL
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Risk метрики
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    
    # Временные метрики
    avg_trade_duration: float = 0.0  # в минутах
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Equity curve
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    
    # Сделки
    trades: List[BacktestTrade] = field(default_factory=list)


class BacktestEngine:
    """
    Движок для бэктестинга торговых стратегий
    
    Использование:
    ```python
    engine = BacktestEngine(initial_balance=10000)
    result = await engine.run(
        symbol="BTCUSDT",
        start_date="2024-01-01",
        end_date="2024-11-01",
        strategy="trend_following"
    )
    engine.print_report(result)
    ```
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission_pct: float = 0.1,  # 0.1% комиссия Bybit
        slippage_pct: float = 0.05,   # 0.05% проскальзывание
        use_dynamic_risk: bool = True
    ):
        self.initial_balance = initial_balance
        self.commission_pct = commission_pct / 100
        self.slippage_pct = slippage_pct / 100
        self.use_dynamic_risk = use_dynamic_risk
        
        self.technical_analyzer = TechnicalAnalyzer()
        self.risk_manager = DynamicRiskManager()
        
        # Состояние
        self.balance = initial_balance
        self.equity = initial_balance
        self.peak_equity = initial_balance
        self.trades: List[BacktestTrade] = []
        self.open_trades: List[BacktestTrade] = []
        self.trade_counter = 0
        
        # История
        self.equity_history: List[Tuple[datetime, float]] = []
        self.balance_history: List[Tuple[datetime, float]] = []

    
    def reset(self):
        """Сбросить состояние"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance
        self.trades = []
        self.open_trades = []
        self.trade_counter = 0
        self.equity_history = []
        self.balance_history = []
    
    def _apply_slippage(self, price: float, side: BacktestSide, is_entry: bool) -> float:
        """Применить проскальзывание"""
        if is_entry:
            # При входе: покупаем дороже, продаём дешевле
            if side == BacktestSide.BUY:
                return price * (1 + self.slippage_pct)
            else:
                return price * (1 - self.slippage_pct)
        else:
            # При выходе: наоборот
            if side == BacktestSide.BUY:
                return price * (1 - self.slippage_pct)
            else:
                return price * (1 + self.slippage_pct)
    
    def _calculate_commission(self, value: float) -> float:
        """Рассчитать комиссию"""
        return value * self.commission_pct
    
    def _open_trade(
        self,
        symbol: str,
        side: BacktestSide,
        price: float,
        timestamp: datetime,
        stop_loss: float,
        take_profit: float,
        position_size_pct: float = 0.1
    ) -> Optional[BacktestTrade]:
        """Открыть сделку"""
        # Применяем проскальзывание
        entry_price = self._apply_slippage(price, side, is_entry=True)
        
        # Размер позиции
        position_value = self.balance * position_size_pct
        quantity = position_value / entry_price
        
        # Комиссия
        commission = self._calculate_commission(position_value)
        self.balance -= commission
        
        self.trade_counter += 1
        
        trade = BacktestTrade(
            id=self.trade_counter,
            symbol=symbol,
            side=side,
            entry_time=timestamp,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fees=commission
        )
        
        self.open_trades.append(trade)
        return trade
    
    def _close_trade(
        self,
        trade: BacktestTrade,
        price: float,
        timestamp: datetime,
        reason: str
    ):
        """Закрыть сделку"""
        # Применяем проскальзывание
        exit_price = self._apply_slippage(price, trade.side, is_entry=False)
        
        # Рассчитываем PnL
        if trade.side == BacktestSide.BUY:
            pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity
        
        # Комиссия на выход
        exit_value = exit_price * trade.quantity
        commission = self._calculate_commission(exit_value)
        
        # Итоговый PnL с учётом комиссий
        net_pnl = pnl - commission
        pnl_pct = (net_pnl / (trade.entry_price * trade.quantity)) * 100
        
        # Обновляем сделку
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.pnl = net_pnl
        trade.pnl_pct = pnl_pct
        trade.exit_reason = reason
        trade.fees += commission
        
        # Обновляем баланс
        self.balance += net_pnl
        
        # Перемещаем в закрытые
        self.open_trades.remove(trade)
        self.trades.append(trade)
    
    def _check_sl_tp(self, candle: Dict, timestamp: datetime):
        """Проверить SL/TP для открытых позиций"""
        for trade in self.open_trades[:]:  # Копия списка для безопасного удаления
            high = candle['high']
            low = candle['low']
            
            if trade.side == BacktestSide.BUY:
                # Stop Loss
                if low <= trade.stop_loss:
                    self._close_trade(trade, trade.stop_loss, timestamp, "Stop Loss")
                # Take Profit
                elif high >= trade.take_profit:
                    self._close_trade(trade, trade.take_profit, timestamp, "Take Profit")
            else:  # SELL
                # Stop Loss
                if high >= trade.stop_loss:
                    self._close_trade(trade, trade.stop_loss, timestamp, "Stop Loss")
                # Take Profit
                elif low <= trade.take_profit:
                    self._close_trade(trade, trade.take_profit, timestamp, "Take Profit")
    
    def _update_equity(self, current_price: float, timestamp: datetime):
        """Обновить equity"""
        # Unrealized PnL
        unrealized_pnl = 0.0
        for trade in self.open_trades:
            if trade.side == BacktestSide.BUY:
                unrealized_pnl += (current_price - trade.entry_price) * trade.quantity
            else:
                unrealized_pnl += (trade.entry_price - current_price) * trade.quantity
        
        self.equity = self.balance + unrealized_pnl
        
        # Обновляем пик
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        # Сохраняем историю
        self.equity_history.append((timestamp, self.equity))
        self.balance_history.append((timestamp, self.balance))

    
    def _generate_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        strategy: str = "trend_following"
    ) -> Optional[BacktestSide]:
        """
        Генерировать торговый сигнал
        
        Стратегии:
        - trend_following: RSI + MACD + Trend + EMA filter
        - mean_reversion: RSI экстремумы + BB + confirmation
        - breakout: BB breakout + Volume + trend
        - rsi_extreme: RSI + trend confirmation
        - momentum: EMA crossover + RSI filter
        """
        if idx < 50:  # Недостаточно данных
            return None
        
        row = df.iloc[idx]
        
        rsi = row.get('rsi', 50)
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        macd_hist = row.get('macd_histogram', 0)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)
        bb_middle = row.get('bb_middle', 0)
        close = row['close']
        
        # EMA для фильтрации тренда
        ema_20 = row.get('ema_20', close)
        ema_50 = row.get('ema_50', close)
        
        # Предыдущие значения для crossover
        prev_row = df.iloc[idx - 1]
        prev_macd_hist = prev_row.get('macd_histogram', 0)
        prev_rsi = prev_row.get('rsi', 50)
        prev_close = prev_row['close']
        
        # Определяем тренд
        uptrend = close > ema_20 > ema_50
        downtrend = close < ema_20 < ema_50
        
        if strategy == "trend_following":
            # BUY: RSI < 40 + MACD bullish crossover + uptrend
            if rsi < 40 and macd_hist > 0 and prev_macd_hist <= 0:
                if close > ema_50:  # Фильтр: цена выше EMA50
                    return BacktestSide.BUY
            # SELL: RSI > 60 + MACD bearish crossover + downtrend
            elif rsi > 60 and macd_hist < 0 and prev_macd_hist >= 0:
                if close < ema_50:  # Фильтр: цена ниже EMA50
                    return BacktestSide.SELL
        
        elif strategy == "mean_reversion":
            # BUY: RSI < 25 + Price below lower BB + RSI turning up
            if rsi < 25 and close < bb_lower and rsi > prev_rsi:
                return BacktestSide.BUY
            # SELL: RSI > 75 + Price above upper BB + RSI turning down
            elif rsi > 75 and close > bb_upper and rsi < prev_rsi:
                return BacktestSide.SELL
        
        elif strategy == "breakout":
            # BUY: Price breaks above upper BB with volume + uptrend
            volume = row.get('volume', 0)
            avg_volume = df['volume'].iloc[idx-20:idx].mean()
            
            if close > bb_upper and volume > avg_volume * 1.5 and uptrend:
                return BacktestSide.BUY
            elif close < bb_lower and volume > avg_volume * 1.5 and downtrend:
                return BacktestSide.SELL
        
        elif strategy == "rsi_extreme":
            # RSI экстремумы с подтверждением разворота
            if rsi < 20 and rsi > prev_rsi and close > prev_close:
                return BacktestSide.BUY
            elif rsi > 80 and rsi < prev_rsi and close < prev_close:
                return BacktestSide.SELL
        
        elif strategy == "momentum":
            # EMA crossover + RSI filter
            prev_ema_20 = prev_row.get('ema_20', prev_close)
            prev_ema_50 = prev_row.get('ema_50', prev_close)
            
            # Golden cross + RSI not overbought
            if ema_20 > ema_50 and prev_ema_20 <= prev_ema_50 and rsi < 65:
                return BacktestSide.BUY
            # Death cross + RSI not oversold
            elif ema_20 < ema_50 and prev_ema_20 >= prev_ema_50 and rsi > 35:
                return BacktestSide.SELL
        
        return None
    
    async def run(
        self,
        klines: List[Dict],
        symbol: str = "BTCUSDT",
        strategy: str = "trend_following",
        position_size_pct: float = 0.1,
        max_open_trades: int = 1
    ) -> BacktestResult:
        """
        Запустить бэктест
        
        Args:
            klines: Исторические свечи
            symbol: Торговая пара
            strategy: Стратегия (trend_following, mean_reversion, breakout, rsi_extreme)
            position_size_pct: Размер позиции (% от баланса)
            max_open_trades: Максимум открытых позиций
        
        Returns:
            BacktestResult с метриками
        """
        self.reset()
        
        if len(klines) < 100:
            print("❌ Недостаточно данных для бэктеста")
            return BacktestResult()
        
        # Подготавливаем DataFrame с индикаторами
        df = pd.DataFrame(klines)
        df = add_all_indicators(df)
        df = df.dropna().reset_index(drop=True)
        
        print(f"📊 Backtesting {symbol} | Strategy: {strategy}")
        print(f"   Period: {len(df)} candles")
        print(f"   Initial Balance: ${self.initial_balance:,.2f}")
        print(f"   Position Size: {position_size_pct*100:.0f}%")
        
        # Основной цикл
        for idx in range(50, len(df)):
            row = df.iloc[idx]
            timestamp = pd.to_datetime(row['timestamp'], unit='ms')
            current_price = row['close']
            
            # Проверяем SL/TP
            self._check_sl_tp(row.to_dict(), timestamp)
            
            # Обновляем equity
            self._update_equity(current_price, timestamp)
            
            # Генерируем сигнал
            if len(self.open_trades) < max_open_trades:
                signal = self._generate_signal(df, idx, strategy)
                
                if signal:
                    # Рассчитываем SL/TP
                    klines_slice = df.iloc[max(0, idx-60):idx].to_dict('records')
                    
                    if self.use_dynamic_risk:
                        sl, tp = self.risk_manager.calculate_dynamic_sl_tp(
                            current_price, signal.value, klines_slice
                        )
                    else:
                        # Фиксированные 2%/3%
                        if signal == BacktestSide.BUY:
                            sl = current_price * 0.98
                            tp = current_price * 1.03
                        else:
                            sl = current_price * 1.02
                            tp = current_price * 0.97
                    
                    self._open_trade(
                        symbol=symbol,
                        side=signal,
                        price=current_price,
                        timestamp=timestamp,
                        stop_loss=sl,
                        take_profit=tp,
                        position_size_pct=position_size_pct
                    )
        
        # Закрываем оставшиеся позиции
        final_price = df.iloc[-1]['close']
        final_time = pd.to_datetime(df.iloc[-1]['timestamp'], unit='ms')
        
        for trade in self.open_trades[:]:
            self._close_trade(trade, final_price, final_time, "End of backtest")
        
        # Рассчитываем результаты
        return self._calculate_results()

    
    def _calculate_results(self) -> BacktestResult:
        """Рассчитать итоговые метрики"""
        result = BacktestResult()
        result.trades = self.trades
        
        if not self.trades:
            return result
        
        # Основные метрики
        result.total_trades = len(self.trades)
        result.winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        result.losing_trades = sum(1 for t in self.trades if t.pnl <= 0)
        result.win_rate = (result.winning_trades / result.total_trades) * 100
        
        # PnL
        pnls = [t.pnl for t in self.trades]
        result.total_pnl = sum(pnls)
        result.total_pnl_pct = (result.total_pnl / self.initial_balance) * 100
        result.avg_pnl = np.mean(pnls)
        
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl <= 0]
        
        result.avg_win = np.mean(wins) if wins else 0
        result.avg_loss = np.mean(losses) if losses else 0
        
        # Profit Factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Equity curve
        result.equity_curve = [e[1] for e in self.equity_history]
        
        # Max Drawdown
        if result.equity_curve:
            peak = result.equity_curve[0]
            max_dd = 0
            drawdowns = []
            
            for equity in result.equity_curve:
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak
                drawdowns.append(dd)
                if dd > max_dd:
                    max_dd = dd
            
            result.max_drawdown = peak * max_dd
            result.max_drawdown_pct = max_dd * 100
            result.drawdown_curve = drawdowns
        
        # Sharpe Ratio (annualized, assuming 1-minute candles)
        if len(pnls) > 1:
            returns = np.array(pnls) / self.initial_balance
            if np.std(returns) > 0:
                # Annualize: sqrt(525600) for 1-min candles
                result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(525600 / len(self.trades))
        
        # Sortino Ratio (only downside deviation)
        if losses:
            downside_returns = np.array([t.pnl / self.initial_balance for t in self.trades if t.pnl < 0])
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                result.sortino_ratio = (np.mean(pnls) / self.initial_balance) / np.std(downside_returns) * np.sqrt(525600 / len(self.trades))
        
        # Trade duration
        durations = []
        for t in self.trades:
            if t.exit_time and t.entry_time:
                duration = (t.exit_time - t.entry_time).total_seconds() / 60
                durations.append(duration)
        result.avg_trade_duration = np.mean(durations) if durations else 0
        
        # Consecutive wins/losses
        result.max_consecutive_wins = self._max_consecutive(self.trades, win=True)
        result.max_consecutive_losses = self._max_consecutive(self.trades, win=False)
        
        return result
    
    def _max_consecutive(self, trades: List[BacktestTrade], win: bool) -> int:
        """Найти максимальную серию побед/поражений"""
        max_streak = 0
        current_streak = 0
        
        for trade in trades:
            is_win = trade.pnl > 0
            if is_win == win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def print_report(self, result: BacktestResult):
        """Вывести отчёт о бэктесте"""
        print("\n" + "="*60)
        print("📊 BACKTEST REPORT")
        print("="*60)
        
        print(f"\n💰 PERFORMANCE:")
        print(f"   Initial Balance: ${self.initial_balance:,.2f}")
        print(f"   Final Balance:   ${self.balance:,.2f}")
        print(f"   Total PnL:       ${result.total_pnl:+,.2f} ({result.total_pnl_pct:+.2f}%)")
        
        print(f"\n📈 TRADES:")
        print(f"   Total Trades:    {result.total_trades}")
        print(f"   Winning:         {result.winning_trades} ({result.win_rate:.1f}%)")
        print(f"   Losing:          {result.losing_trades}")
        print(f"   Avg Win:         ${result.avg_win:+,.2f}")
        print(f"   Avg Loss:        ${result.avg_loss:+,.2f}")
        print(f"   Profit Factor:   {result.profit_factor:.2f}")
        
        print(f"\n⚠️  RISK METRICS:")
        print(f"   Max Drawdown:    ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
        print(f"   Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        print(f"   Sortino Ratio:   {result.sortino_ratio:.2f}")
        
        print(f"\n⏱️  TIME METRICS:")
        print(f"   Avg Trade Duration: {result.avg_trade_duration:.1f} min")
        print(f"   Max Win Streak:     {result.max_consecutive_wins}")
        print(f"   Max Loss Streak:    {result.max_consecutive_losses}")
        
        print("\n" + "="*60)
        
        # Топ 5 лучших и худших сделок
        if result.trades:
            sorted_trades = sorted(result.trades, key=lambda t: t.pnl, reverse=True)
            
            print("\n🏆 TOP 5 BEST TRADES:")
            for t in sorted_trades[:5]:
                print(f"   {t.side.value} @ ${t.entry_price:.2f} → ${t.exit_price:.2f} | PnL: ${t.pnl:+.2f} ({t.pnl_pct:+.2f}%)")
            
            print("\n💀 TOP 5 WORST TRADES:")
            for t in sorted_trades[-5:]:
                print(f"   {t.side.value} @ ${t.entry_price:.2f} → ${t.exit_price:.2f} | PnL: ${t.pnl:+.2f} ({t.pnl_pct:+.2f}%)")


# Singleton
_backtester = None

def get_backtester(initial_balance: float = 10000.0) -> BacktestEngine:
    """Получить singleton instance"""
    global _backtester
    if _backtester is None:
        _backtester = BacktestEngine(initial_balance=initial_balance)
    return _backtester
