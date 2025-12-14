"""Показать открытые позиции с уровнями SL/TP"""
import asyncio
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select
from core.bybit_api import get_bybit_api

async def main():
    api = get_bybit_api()
    
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        trades = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"ОТКРЫТЫЕ ПОЗИЦИИ ({len(trades)})")
        print(f"{'='*80}\n")
        
        for trade in trades:
            # Получаем текущую цену
            ticker = await api.get_ticker(trade.symbol)
            current_price = 0
            if ticker:
                current_price = float(ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price') or 0)
            
            # Рассчитываем PnL
            pnl = (current_price - trade.entry_price) * trade.quantity
            pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
            
            # Рассчитываем расстояние до SL/TP
            distance_to_sl = ((current_price - trade.stop_loss) / trade.stop_loss) * 100
            distance_to_tp = ((trade.take_profit - current_price) / current_price) * 100
            
            print(f"📊 {trade.symbol} ({trade.side.value})")
            print(f"   Entry: ${trade.entry_price:.2f}")
            print(f"   Current: ${current_price:.2f}")
            print(f"   Stop Loss: ${trade.stop_loss:.2f} (до SL: {distance_to_sl:+.2f}%)")
            print(f"   Take Profit: ${trade.take_profit:.2f} (до TP: {distance_to_tp:+.2f}%)")
            print(f"   Quantity: {trade.quantity:.4f}")
            print(f"   PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
            print(f"   Entry Time: {trade.entry_time}")
            
            # Проверяем условия закрытия
            if current_price <= trade.stop_loss:
                print(f"   🛑 ДОЛЖЕН ЗАКРЫТЬСЯ! Stop Loss достигнут!")
            elif current_price >= trade.take_profit:
                print(f"   🎯 ДОЛЖЕН ЗАКРЫТЬСЯ! Take Profit достигнут!")
            else:
                print(f"   ⏳ Ждем...")
            
            print()

if __name__ == "__main__":
    asyncio.run(main())
