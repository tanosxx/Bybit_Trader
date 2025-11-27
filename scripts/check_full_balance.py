"""
Полная проверка баланса с учетом открытых позиций
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api
from core.real_trader import get_real_trader
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select, func


async def main():
    api = get_bybit_api()
    trader = get_real_trader()
    
    print("="*80)
    print("💰 ПОЛНЫЙ АНАЛИЗ БАЛАНСА")
    print("="*80)
    
    # 1. Свободный баланс
    free_balance = await trader.get_balance()
    print(f"\n1️⃣ Свободный баланс (USDT): ${free_balance:,.2f}")
    
    # 2. Открытые позиции
    open_trades = await trader.get_open_trades()
    print(f"\n2️⃣ Открытые позиции: {len(open_trades)}")
    
    total_invested = 0
    total_current_value = 0
    total_unrealized = 0
    
    for trade in open_trades:
        ticker = await api.get_ticker(trade.symbol)
        current_price = ticker['last_price']
        
        invested = trade.entry_price * trade.quantity
        current_value = current_price * trade.quantity
        
        if trade.side.value == "BUY":
            unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
        else:
            unrealized_pnl = (trade.entry_price - current_price) * trade.quantity
        
        total_invested += invested
        total_current_value += current_value
        total_unrealized += unrealized_pnl
        
        emoji = "🟢" if unrealized_pnl > 0 else "🔴"
        print(f"   {emoji} {trade.symbol}: ${invested:,.2f} → ${current_value:,.2f} ({unrealized_pnl:+.2f})")
    
    print(f"\n   Total Invested: ${total_invested:,.2f}")
    print(f"   Current Value: ${total_current_value:,.2f}")
    print(f"   Unrealized PnL: ${total_unrealized:+,.2f}")
    
    # 3. Закрытые сделки
    async with async_session() as session:
        result = await session.execute(
            select(
                func.count(Trade.id).label('total'),
                func.sum(Trade.pnl).label('total_pnl'),
                func.count(Trade.id).filter(Trade.pnl > 0).label('wins'),
                func.count(Trade.id).filter(Trade.pnl < 0).label('losses')
            ).where(Trade.status == TradeStatus.CLOSED)
        )
        stats = result.first()
    
    print(f"\n3️⃣ Закрытые сделки: {stats.total}")
    print(f"   Wins: {stats.wins}")
    print(f"   Losses: {stats.losses}")
    print(f"   Realized PnL: ${stats.total_pnl:+,.2f}")
    
    # 4. Итоговый equity
    total_equity = free_balance + total_current_value
    
    print(f"\n{'='*80}")
    print(f"💎 ИТОГОВЫЙ EQUITY")
    print(f"{'='*80}")
    print(f"Свободный баланс:     ${free_balance:>15,.2f}")
    print(f"Открытые позиции:     ${total_current_value:>15,.2f}")
    print(f"{'─'*80}")
    print(f"TOTAL EQUITY:         ${total_equity:>15,.2f}")
    print(f"{'='*80}")
    
    # 5. Сравнение с начальным балансом
    initial_balance = 150000.0  # Из конфига
    total_pnl = total_equity - initial_balance
    total_pnl_pct = (total_pnl / initial_balance) * 100
    
    print(f"\n📊 PERFORMANCE")
    print(f"{'='*80}")
    print(f"Начальный баланс:     ${initial_balance:>15,.2f}")
    print(f"Текущий equity:       ${total_equity:>15,.2f}")
    print(f"{'─'*80}")
    emoji = "🟢" if total_pnl > 0 else "🔴"
    print(f"{emoji} Total PnL:           ${total_pnl:>15,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"{'='*80}")
    
    print(f"\n📈 BREAKDOWN")
    print(f"   Realized PnL:      ${stats.total_pnl:>15,.2f}")
    print(f"   Unrealized PnL:    ${total_unrealized:>15,.2f}")
    print(f"   {'─'*60}")
    print(f"   Total:             ${(stats.total_pnl + total_unrealized):>15,.2f}")


if __name__ == "__main__":
    asyncio.run(main())
