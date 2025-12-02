"""
Скрипт для безопасной остановки торговли
Закрывает все открытые позиции и останавливает бота
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select, update


async def close_all_positions():
    """Закрыть все открытые позиции на бирже"""
    api = get_bybit_api()
    
    print("🔍 Checking open positions on Bybit...")
    positions = await api.get_positions()
    
    if not positions:
        print("✅ No open positions on exchange")
        return True
    
    print(f"⚠️  Found {len(positions)} open positions:")
    for pos in positions:
        print(f"   - {pos['symbol']}: {pos['side']} {pos['size']} @ ${pos['entry_price']}")
    
    print("\n❓ Close all positions? (yes/no): ", end="")
    confirm = input().strip().lower()
    
    if confirm != "yes":
        print("❌ Cancelled by user")
        return False
    
    print("\n🔄 Closing positions...")
    for pos in positions:
        symbol = pos['symbol']
        side = pos['side']
        size = pos['size']
        
        # Определяем противоположную сторону для закрытия
        close_side = "Sell" if side == "Buy" else "Buy"
        
        print(f"   Closing {symbol} {side} {size}...")
        result = await api.place_futures_order(
            symbol=symbol,
            side=close_side,
            order_type="Market",
            qty=size,
            reduce_only=True
        )
        
        if result:
            print(f"   ✅ {symbol} closed")
        else:
            print(f"   ❌ {symbol} failed to close")
    
    print("\n✅ All positions closed")
    return True


async def update_db_positions():
    """Обновить статус позиций в БД"""
    print("\n🔄 Updating database...")
    
    async with async_session() as session:
        # Закрываем все OPEN позиции в БД
        result = await session.execute(
            update(Trade)
            .where(Trade.status == TradeStatus.OPEN)
            .values(
                status=TradeStatus.CLOSED,
                exit_reason="Manual stop - maintenance"
            )
        )
        await session.commit()
        
        count = result.rowcount
        print(f"✅ Updated {count} positions in database")


async def show_statistics():
    """Показать статистику торговли"""
    print("\n" + "="*60)
    print("📊 TRADING STATISTICS")
    print("="*60)
    
    async with async_session() as session:
        # Всего сделок
        result = await session.execute(
            select(Trade)
        )
        all_trades = result.scalars().all()
        
        total = len(all_trades)
        open_count = sum(1 for t in all_trades if t.status == TradeStatus.OPEN)
        closed_count = sum(1 for t in all_trades if t.status == TradeStatus.CLOSED)
        
        # PnL
        total_pnl = sum(t.pnl for t in all_trades if t.status == TradeStatus.CLOSED and t.pnl)
        profitable = sum(1 for t in all_trades if t.status == TradeStatus.CLOSED and t.pnl and t.pnl > 0)
        
        print(f"\n📈 Total Trades: {total}")
        print(f"   Open: {open_count}")
        print(f"   Closed: {closed_count}")
        print(f"\n💰 Total PnL: ${total_pnl:.2f}")
        print(f"   Profitable: {profitable}/{closed_count} ({profitable/closed_count*100:.1f}%)" if closed_count > 0 else "   No closed trades")
        
        # По символам
        print(f"\n📊 By Symbol:")
        symbols = {}
        for trade in all_trades:
            if trade.symbol not in symbols:
                symbols[trade.symbol] = {'count': 0, 'pnl': 0}
            symbols[trade.symbol]['count'] += 1
            if trade.status == TradeStatus.CLOSED and trade.pnl:
                symbols[trade.symbol]['pnl'] += trade.pnl
        
        for symbol, data in sorted(symbols.items(), key=lambda x: x[1]['pnl'], reverse=True):
            print(f"   {symbol}: {data['count']} trades, PnL: ${data['pnl']:.2f}")
    
    print("\n" + "="*60)


async def main():
    """Главная функция"""
    print("="*60)
    print("🛑 STOP TRADING - Maintenance Mode")
    print("="*60)
    
    # 1. Показать статистику
    await show_statistics()
    
    # 2. Закрыть позиции на бирже
    print("\n" + "="*60)
    print("🔄 STEP 1: Close Exchange Positions")
    print("="*60)
    success = await close_all_positions()
    
    if not success:
        print("\n❌ Operation cancelled")
        return
    
    # 3. Обновить БД
    print("\n" + "="*60)
    print("🔄 STEP 2: Update Database")
    print("="*60)
    await update_db_positions()
    
    # 4. Финальная статистика
    await show_statistics()
    
    print("\n" + "="*60)
    print("✅ TRADING STOPPED")
    print("="*60)
    print("\n📝 Next steps:")
    print("   1. Stop Docker containers: docker-compose down")
    print("   2. Make necessary changes")
    print("   3. Deploy: docker-compose up -d --build")
    print("   4. Check logs: docker logs -f bybit_bot")


if __name__ == "__main__":
    asyncio.run(main())
