"""
Position Monitor - Мониторинг и закрытие позиций по SL/TP

Обходит баг Bybit API с установкой SL/TP
Проверяет открытые позиции каждые 5 секунд и закрывает по условиям
"""
import asyncio
from datetime import datetime
from typing import Dict, List
from sqlalchemy import select, update
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from core.bybit_api import get_bybit_api
from config import settings


class PositionMonitor:
    """Мониторинг позиций и закрытие по SL/TP"""
    
    def __init__(self):
        self.api = get_bybit_api()
        self.check_interval = 5  # Проверка каждые 5 секунд
        self.running = False
        
    async def get_current_price(self, symbol: str) -> float:
        """Получить текущую цену"""
        try:
            ticker = await self.api.get_ticker(symbol)
            if ticker:
                return float(ticker.get('last_price', 0))
            return 0
        except Exception as e:
            print(f"⚠️ Error getting price for {symbol}: {e}")
            return 0
    
    async def close_position(self, trade: Trade, reason: str, current_price: float):
        """Закрыть позицию на бирже"""
        try:
            symbol = trade.symbol
            quantity = float(trade.quantity)
            
            # Определяем противоположную сторону
            close_side = "Sell" if trade.side == TradeSide.BUY else "Buy"
            
            print(f"\n🔴 Closing {symbol} {trade.side.value}: {reason}")
            print(f"   Entry: ${trade.entry_price:.2f} → Current: ${current_price:.2f}")
            
            # Закрываем на бирже
            result = await self.api.place_futures_order(
                symbol=symbol,
                side=close_side,
                order_type="Market",
                qty=quantity,
                reduce_only=True
            )
            
            if result:
                # Рассчитываем PnL
                if trade.side == TradeSide.BUY:  # LONG
                    pnl = (current_price - trade.entry_price) * quantity
                else:  # SHORT
                    pnl = (trade.entry_price - current_price) * quantity
                
                pnl_pct = (pnl / (trade.entry_price * quantity)) * 100
                
                # Обновляем в БД
                async with async_session() as session:
                    await session.execute(
                        update(Trade)
                        .where(Trade.id == trade.id)
                        .values(
                            status=TradeStatus.CLOSED,
                            exit_price=current_price,
                            exit_time=datetime.utcnow(),
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            exit_reason=reason
                        )
                    )
                    await session.commit()
                
                print(f"   ✅ Closed: PnL ${pnl:.2f} ({pnl_pct:+.2f}%)")
                return True
            else:
                print(f"   ❌ Failed to close on exchange")
                return False
                
        except Exception as e:
            print(f"   ❌ Error closing position: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def check_position(self, trade: Trade):
        """Проверить одну позицию на SL/TP"""
        try:
            symbol = trade.symbol
            current_price = await self.get_current_price(symbol)
            
            if current_price == 0:
                return
            
            entry_price = float(trade.entry_price)
            stop_loss = float(trade.stop_loss) if trade.stop_loss else None
            take_profit = float(trade.take_profit) if trade.take_profit else None
            
            # Проверяем SL/TP в зависимости от стороны
            if trade.side == TradeSide.BUY:  # LONG
                # Stop Loss: цена упала ниже SL
                if stop_loss and current_price <= stop_loss:
                    await self.close_position(trade, f"Stop Loss hit: ${stop_loss:.2f}", current_price)
                    return
                
                # Take Profit: цена выросла выше TP
                if take_profit and current_price >= take_profit:
                    await self.close_position(trade, f"Take Profit hit: ${take_profit:.2f}", current_price)
                    return
            
            else:  # SHORT
                # Stop Loss: цена выросла выше SL
                if stop_loss and current_price >= stop_loss:
                    await self.close_position(trade, f"Stop Loss hit: ${stop_loss:.2f}", current_price)
                    return
                
                # Take Profit: цена упала ниже TP
                if take_profit and current_price <= take_profit:
                    await self.close_position(trade, f"Take Profit hit: ${take_profit:.2f}", current_price)
                    return
        
        except Exception as e:
            print(f"⚠️ Error checking position {trade.symbol}: {e}")
    
    async def monitor_loop(self):
        """Основной цикл мониторинга"""
        print("🔍 Position Monitor started")
        print(f"   Check interval: {self.check_interval}s")
        
        while self.running:
            try:
                # Получаем открытые позиции из БД
                async with async_session() as session:
                    result = await session.execute(
                        select(Trade).where(
                            Trade.status == TradeStatus.OPEN,
                            Trade.market_type == 'futures'
                        )
                    )
                    open_trades = result.scalars().all()
                
                if open_trades:
                    print(f"\n🔍 Checking {len(open_trades)} open positions...")
                    
                    # Проверяем каждую позицию
                    for trade in open_trades:
                        await self.check_position(trade)
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Error in monitor loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(self.check_interval)
    
    async def start(self):
        """Запустить мониторинг"""
        self.running = True
        await self.monitor_loop()
    
    def stop(self):
        """Остановить мониторинг"""
        self.running = False
        print("🛑 Position Monitor stopped")


# Singleton
_monitor = None

def get_position_monitor() -> PositionMonitor:
    """Получить singleton instance"""
    global _monitor
    if _monitor is None:
        _monitor = PositionMonitor()
    return _monitor


async def main():
    """Запуск мониторинга как отдельного процесса"""
    monitor = get_position_monitor()
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
