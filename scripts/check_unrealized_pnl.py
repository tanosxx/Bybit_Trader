"""
Проверка нереализованного PnL открытых позиций
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api
from core.real_trader import get_real_trader


async def main():
    api = get_bybit_api()
    trader = get_real_trader()
    
    print("=== ОТКРЫТЫЕ ПОЗИЦИИ И UNREALIZED PNL ===\n")
    
    open_trades = await trader.get_open_trades()
    
    if not open_trades:
        print("Нет открытых позиций")
        return
    
    total_unrealized = 0
    total_invested = 0
    
    for trade in open_trades:
        ticker = await api.get_ticker(trade.symbol)
        current_price = ticker['last_price']
        
        # Рассчитываем unrealized PnL
        if trade.side.value == "BUY":
            unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
        else:  # SELL
            unrealized_pnl = (trade.entry_price - current_price) * trade.quantity
        
        unrealized_pct = (unrealized_pnl / (trade.entry_price * trade.quantity)) * 100
        invested = trade.entry_price * trade.quantity
        
        total_unrealized += unrealized_pnl
        total_invested += invested
        
        emoji = "🟢" if unrealized_pnl > 0 else "🔴"
        
        print(f"{emoji} {trade.symbol} {trade.side.value}")
        print(f"   Entry: ${trade.entry_price:.2f} × {trade.quantity:.4f} = ${invested:.2f}")
        print(f"   Current: ${current_price:.2f}")
        print(f"   Unrealized PnL: ${unrealized_pnl:+.2f} ({unrealized_pct:+.2f}%)")
        print(f"   Entry Time: {trade.entry_time}")
        print()
    
    print("="*60)
    print(f"Total Invested: ${total_invested:.2f}")
    print(f"Total Unrealized PnL: ${total_unrealized:+.2f}")
    print(f"Unrealized %: {(total_unrealized/total_invested)*100:+.2f}%")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
