"""
SPOT Executor - Исполнитель для спотовой торговли
Работает с реальным балансом, только LONG (BUY) позиции
"""
from typing import Dict, List, Optional
from datetime import datetime

from .base_executor import (
    BaseExecutor, MarketType, TradeSignal, 
    ExecutionResult, OrderSide
)
from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from sqlalchemy import select
from config import settings


class SpotExecutor(BaseExecutor):
    """
    SPOT Executor - Спотовая торговля
    
    Особенности:
    - Только LONG позиции (покупка)
    - SELL = продажа имеющихся монет
    - Использует реальный баланс или spot_virtual_balance
    """
    
    # Правила округления для разных монет
    QUANTITY_PRECISION = {
        'BTCUSDT': 6,
        'ETHUSDT': 5,
        'BNBUSDT': 3,
        'SOLUSDT': 2,
        'XRPUSDT': 0,
        'DOGEUSDT': 0,
        'ADAUSDT': 0,
    }
    
    def __init__(self):
        super().__init__(MarketType.SPOT)
        self.api = get_bybit_api()
        self.virtual_balance = settings.spot_virtual_balance
        self.risk_per_trade = settings.spot_risk_per_trade
    
    def round_quantity(self, symbol: str, quantity: float) -> float:
        """Округлить количество согласно требованиям Bybit"""
        precision = self.QUANTITY_PRECISION.get(symbol, 2)
        if precision == 0:
            return int(quantity)
        return round(quantity, precision)
    
    async def get_balance(self) -> float:
        """Получить USDT баланс"""
        balances = await self.api.get_wallet_balance()
        if balances and "USDT" in balances:
            real_balance = balances["USDT"]["total"]
            # Используем минимум из реального и виртуального
            return min(real_balance, self.virtual_balance)
        return 0.0
    
    def calculate_position_size(self, price: float, risk_pct: float = None) -> float:
        """
        Рассчитать размер позиции для SPOT
        
        Position_Size_USD = Virtual_Balance * Risk_Pct
        Quantity = Position_Size_USD / Price
        """
        risk = risk_pct or self.risk_per_trade
        position_usd = self.virtual_balance * risk
        return position_usd / price
    
    async def execute_signal(self, signal: TradeSignal) -> ExecutionResult:
        """
        Исполнить сигнал на SPOT рынке
        
        BUY -> Покупаем монеты
        SELL -> Продаём имеющиеся монеты
        """
        if signal.is_skip:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Signal is SKIP"
            )
        
        symbol = signal.symbol
        price = signal.price
        
        try:
            if signal.is_buy:
                return await self._execute_buy(symbol, price, signal)
            elif signal.is_sell:
                return await self._execute_sell(symbol, price, signal)
        except Exception as e:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=str(e)
            )
        
        return ExecutionResult(
            success=False,
            market_type=self.market_type,
            error="Unknown signal action"
        )
    
    async def _execute_buy(self, symbol: str, price: float, signal: TradeSignal) -> ExecutionResult:
        """Исполнить покупку"""
        # Рассчитываем размер позиции
        quantity = self.calculate_position_size(price)
        quantity = self.round_quantity(symbol, quantity)
        
        if quantity <= 0:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Quantity too small"
            )
        
        # Размещаем ордер
        order = await self.api.place_order(
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=quantity,
            category="spot"
        )
        
        if not order:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Failed to place order"
            )
        
        # Сохраняем в БД
        trade = await self._save_trade(
            symbol=symbol,
            side=TradeSide.BUY,
            price=price,
            quantity=quantity,
            order_id=order.get('order_id'),
            signal=signal
        )
        
        print(f"✅ [SPOT] BUY {symbol}: {quantity} @ ${price:.2f}")
        
        return ExecutionResult(
            success=True,
            market_type=self.market_type,
            order_id=order.get('order_id'),
            symbol=symbol,
            side="BUY",
            quantity=quantity,
            price=price,
            extra_data={'trade_id': trade.id if trade else None}
        )
    
    async def _execute_sell(self, symbol: str, price: float, signal: TradeSignal) -> ExecutionResult:
        """Продать имеющиеся монеты"""
        # Получаем баланс монеты
        base_coin = symbol.replace('USDT', '').replace('USDC', '')
        balances = await self.api.get_wallet_balance()
        
        if not balances or base_coin not in balances:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=f"No {base_coin} balance"
            )
        
        quantity = balances[base_coin]['total']
        quantity = self.round_quantity(symbol, quantity)
        
        if quantity <= 0:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="No coins to sell"
            )
        
        # Размещаем ордер на продажу
        order = await self.api.place_order(
            symbol=symbol,
            side="Sell",
            order_type="Market",
            qty=quantity,
            category="spot"
        )
        
        if not order:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Failed to place sell order"
            )
        
        # Закрываем открытые позиции в БД
        pnl = await self._close_open_trades(symbol, price, "SELL signal")
        self.record_trade(pnl)
        
        print(f"✅ [SPOT] SELL {symbol}: {quantity} @ ${price:.2f} | PnL: ${pnl:+.2f}")
        
        return ExecutionResult(
            success=True,
            market_type=self.market_type,
            order_id=order.get('order_id'),
            symbol=symbol,
            side="SELL",
            quantity=quantity,
            price=price,
            pnl=pnl
        )
    
    async def _save_trade(self, symbol: str, side: TradeSide, price: float, 
                          quantity: float, order_id: str, signal: TradeSignal) -> Optional[Trade]:
        """Сохранить сделку в БД"""
        try:
            async with async_session() as session:
                # Рассчитываем SL/TP
                if side == TradeSide.BUY:
                    stop_loss = price * (1 - settings.stop_loss_pct / 100)
                    take_profit = price * (1 + settings.take_profit_pct / 100)
                else:
                    stop_loss = price * (1 + settings.stop_loss_pct / 100)
                    take_profit = price * (1 - settings.take_profit_pct / 100)
                
                trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_price=price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=TradeStatus.OPEN,
                    ai_risk_score=signal.risk_score,
                    ai_reasoning=signal.reasoning,
                    market_type='spot',  # Новое поле!
                    extra_data={
                        'bybit_order_id': order_id,
                        'confidence': signal.confidence,
                        'executor': 'SpotExecutor'
                    }
                )
                session.add(trade)
                await session.commit()
                await session.refresh(trade)
                return trade
        except Exception as e:
            print(f"❌ Error saving trade: {e}")
            return None
    
    async def _close_open_trades(self, symbol: str, exit_price: float, reason: str) -> float:
        """Закрыть открытые сделки по символу"""
        total_pnl = 0.0
        
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'spot'
                )
            )
            trades = result.scalars().all()
            
            for trade in trades:
                pnl = (exit_price - trade.entry_price) * trade.quantity
                pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
                
                trade.status = TradeStatus.CLOSED
                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                trade.exit_reason = reason
                
                session.add(trade)
                total_pnl += pnl
            
            await session.commit()
        
        return total_pnl
    
    async def close_position(self, symbol: str, reason: str) -> ExecutionResult:
        """Закрыть позицию (продать монеты)"""
        ticker = await self.api.get_ticker(symbol)
        if not ticker:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Cannot get price"
            )
        
        price = float(ticker.get('lastPrice') or ticker.get('last_price', 0))
        
        # Создаём фейковый сигнал для продажи
        signal = TradeSignal(
            action="SELL",
            confidence=1.0,
            risk_score=1,
            reasoning=reason,
            symbol=symbol,
            price=price
        )
        
        return await self._execute_sell(symbol, price, signal)
    
    async def get_open_positions(self) -> List[Dict]:
        """Получить открытые SPOT позиции"""
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'spot'
                )
            )
            trades = result.scalars().all()
            
            return [{
                'id': t.id,
                'symbol': t.symbol,
                'side': t.side.value,
                'entry_price': float(t.entry_price),
                'quantity': float(t.quantity),
                'market_type': 'spot'
            } for t in trades]


# Singleton
_spot_executor = None

def get_spot_executor() -> SpotExecutor:
    global _spot_executor
    if _spot_executor is None:
        _spot_executor = SpotExecutor()
    return _spot_executor
