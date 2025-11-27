"""
Виртуальный трейдер для Bybit
Управление позициями, балансом, Stop Loss / Take Profit
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from database.db import async_session
from database.models import Trade, WalletHistory, SystemLog, TradeStatus, TradeSide, LogLevel
from sqlalchemy import select, desc
from config import settings


class VirtualTrader:
    """Виртуальный трейдер (симуляция на реальных данных)"""
    
    def __init__(self):
        self.initial_balance = settings.initial_balance
    
    async def get_balance(self) -> float:
        """Получить текущий баланс"""
        async with async_session() as session:
            # Последняя запись в истории
            result = await session.execute(
                select(WalletHistory).order_by(desc(WalletHistory.time)).limit(1)
            )
            last_record = result.scalar_one_or_none()
            
            if last_record:
                return last_record.balance_usdt
            else:
                # Первый запуск - создаем начальный баланс
                wallet = WalletHistory(
                    balance_usdt=self.initial_balance,
                    equity=self.initial_balance,
                    change_amount=0.0,
                    change_reason="Initial balance"
                )
                session.add(wallet)
                await session.commit()
                
                return self.initial_balance
    
    async def get_open_trades(self) -> List[Trade]:
        """Получить открытые сделки"""
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.OPEN)
            )
            return result.scalars().all()
    
    async def open_trade(
        self,
        symbol: str,
        side: TradeSide,
        entry_price: float,
        quantity: float,
        ai_risk_score: float,
        ai_reasoning: str,
        extra_data: Optional[Dict] = None
    ) -> Optional[Trade]:
        """
        Открыть сделку
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            side: BUY, SELL
            entry_price: цена входа
            quantity: количество
            ai_risk_score: оценка риска от AI
            ai_reasoning: обоснование от AI
            extra_data: agent_type, indicators, etc.
        """
        balance = await self.get_balance()
        cost = entry_price * quantity
        fee = cost * 0.001  # 0.1% комиссия
        total_cost = cost + fee
        
        if total_cost > balance:
            print(f"❌ Insufficient balance: ${balance:.2f} < ${total_cost:.2f}")
            return None
        
        # Рассчитываем Stop Loss и Take Profit
        if side == TradeSide.BUY:
            stop_loss = entry_price * (1 - settings.stop_loss_pct / 100)
            take_profit = entry_price * (1 + settings.take_profit_pct / 100)
        else:  # SELL
            stop_loss = entry_price * (1 + settings.stop_loss_pct / 100)
            take_profit = entry_price * (1 - settings.take_profit_pct / 100)
        
        async with async_session() as session:
            # Создаем сделку
            trade = Trade(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                fee_entry=fee,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ai_risk_score=ai_risk_score,
                ai_reasoning=ai_reasoning,
                extra_data=extra_data
            )
            session.add(trade)
            
            # Обновляем баланс
            new_balance = balance - total_cost
            wallet = WalletHistory(
                balance_usdt=new_balance,
                equity=new_balance,  # Будет пересчитано позже
                change_amount=-total_cost,
                change_reason=f"Opened {side.value} {symbol}"
            )
            session.add(wallet)
            
            # Логируем
            log = SystemLog(
                level=LogLevel.BUY if side == TradeSide.BUY else LogLevel.SELL,
                component="Trader",
                message=f"Opened {side.value} {symbol} @ ${entry_price:.2f} (qty: {quantity}, cost: ${total_cost:.2f})",
                ai_reasoning=ai_reasoning,
                extra_data=extra_data
            )
            session.add(log)
            
            await session.commit()
            await session.refresh(trade)
            
            print(f"✅ Opened {side.value} {symbol} @ ${entry_price:.2f}")
            print(f"   Quantity: {quantity}, Cost: ${total_cost:.2f}")
            print(f"   Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
            
            return trade
    
    async def close_trade(self, trade: Trade, exit_price: float, reason: str) -> bool:
        """
        Закрыть сделку
        
        Args:
            trade: сделка
            exit_price: цена выхода
            reason: причина закрытия
        """
        async with async_session() as session:
            # Обновляем сделку
            trade.exit_price = exit_price
            trade.exit_time = datetime.utcnow()
            trade.status = TradeStatus.CLOSED
            
            # Рассчитываем PnL
            if trade.side == TradeSide.BUY:
                pnl = (exit_price - trade.entry_price) * trade.quantity
            else:  # SELL
                pnl = (trade.entry_price - exit_price) * trade.quantity
            
            fee_exit = exit_price * trade.quantity * 0.001  # 0.1% комиссия
            trade.fee_exit = fee_exit
            trade.pnl = pnl - fee_exit
            trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
            
            # Рассчитываем время в позиции
            duration = trade.exit_time - trade.entry_time
            duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
            
            session.add(trade)
            
            # Обновляем баланс
            balance = await self.get_balance()
            proceeds = exit_price * trade.quantity - fee_exit
            new_balance = balance + proceeds
            
            wallet = WalletHistory(
                balance_usdt=new_balance,
                equity=new_balance,
                change_amount=trade.pnl,
                change_reason=f"Closed {trade.side.value} {trade.symbol}: {reason}",
                trade_id=trade.id
            )
            session.add(wallet)
            
            # Логируем
            log = SystemLog(
                level=LogLevel.SELL if trade.side == TradeSide.BUY else LogLevel.BUY,
                component="Trader",
                message=f"Closed {trade.side.value} {trade.symbol} @ ${exit_price:.2f} (PnL: ${trade.pnl:+.2f}, {trade.pnl_pct:+.2f}%): {reason}",
                extra_data={"trade_id": trade.id, "pnl": trade.pnl}
            )
            session.add(log)
            
            await session.commit()
            
            emoji = "🟢" if trade.pnl > 0 else "🔴"
            print(f"{emoji} Closed {trade.side.value} {trade.symbol} @ ${exit_price:.2f}")
            print(f"   PnL: ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%)")
            print(f"   Reason: {reason}")
            
            # Возвращаем данные для уведомления
            return {
                "symbol": trade.symbol,
                "side": trade.side.value,
                "entry_price": trade.entry_price,
                "exit_price": exit_price,
                "pnl": trade.pnl,
                "pnl_pct": trade.pnl_pct,
                "reason": reason,
                "duration": duration_str
            }
    
    async def check_stop_loss_take_profit(self, current_prices: Dict[str, float], telegram_notifier=None):
        """
        Проверить Stop Loss и Take Profit для открытых позиций
        
        Args:
            current_prices: {"BTCUSDT": 43250.50, "ETHUSDT": 2250.30}
            telegram_notifier: TelegramNotifier instance (optional)
        """
        open_trades = await self.get_open_trades()
        
        for trade in open_trades:
            if trade.symbol not in current_prices:
                continue
            
            current_price = current_prices[trade.symbol]
            
            # Проверяем Stop Loss
            if trade.side == TradeSide.BUY and current_price <= trade.stop_loss:
                result = await self.close_trade(trade, current_price, "Stop Loss triggered")
                if telegram_notifier and result:
                    await telegram_notifier.notify_position_closed(result)
            
            elif trade.side == TradeSide.SELL and current_price >= trade.stop_loss:
                result = await self.close_trade(trade, current_price, "Stop Loss triggered")
                if telegram_notifier and result:
                    await telegram_notifier.notify_position_closed(result)
            
            # Проверяем Take Profit
            elif trade.side == TradeSide.BUY and current_price >= trade.take_profit:
                result = await self.close_trade(trade, current_price, "Take Profit reached")
                if telegram_notifier and result:
                    await telegram_notifier.notify_position_closed(result)
            
            elif trade.side == TradeSide.SELL and current_price <= trade.take_profit:
                result = await self.close_trade(trade, current_price, "Take Profit reached")
                if telegram_notifier and result:
                    await telegram_notifier.notify_position_closed(result)
    
    async def get_statistics(self) -> Dict:
        """Получить статистику торговли"""
        async with async_session() as session:
            # Все закрытые сделки
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.CLOSED)
            )
            closed_trades = result.scalars().all()
            
            if not closed_trades:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0
                }
            
            wins = sum(1 for t in closed_trades if t.pnl > 0)
            losses = len(closed_trades) - wins
            total_pnl = sum(t.pnl for t in closed_trades)
            avg_pnl = total_pnl / len(closed_trades)
            best_trade = max(t.pnl for t in closed_trades)
            worst_trade = min(t.pnl for t in closed_trades)
            winrate = (wins / len(closed_trades)) * 100
            
            return {
                "total_trades": len(closed_trades),
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "total_pnl": total_pnl,
                "avg_pnl": avg_pnl,
                "best_trade": best_trade,
                "worst_trade": worst_trade
            }


# Singleton
_trader = None

def get_trader() -> VirtualTrader:
    """Получить singleton instance"""
    global _trader
    if _trader is None:
        _trader = VirtualTrader()
    return _trader
