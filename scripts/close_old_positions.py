"""
Скрипт для закрытия старых позиций
Закрывает позиции старше N часов или все позиции

Использование:
  python scripts/close_old_positions.py --hours 24  # Закрыть позиции старше 24 часов
  python scripts/close_old_positions.py --all       # Закрыть ВСЕ позиции
  python scripts/close_old_positions.py --limit 5   # Оставить только 5 последних
"""
import asyncio
import sys
import argparse
sys.path.insert(0, '/app')

from datetime import datetime, timedelta
from database.db import async_session, init_db
from database.models import Trade, TradeStatus
from sqlalchemy import select, desc
from core.bybit_api import get_bybit_api
from core.real_trader import get_real_trader


async def get_open_positions():
    """Получить все открытые позиции"""
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN).order_by(desc(Trade.entry_time))
        )
        return result.scalars().all()


async def close_position(trade: Trade, reason: str):
    """Закрыть позицию"""
    api = get_bybit_api()
    trader = get_real_trader()
    
    # Получаем текущую цену
    ticker = await api.get_ticker(trade.symbol)
    if not ticker:
        print(f"❌ Cannot get price for {trade.symbol}")
        return False
    
    price = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
    if not price:
        print(f"❌ Invalid price for {trade.symbol}")
        return False
    
    current_price = float(price)
    
    # Закрываем
    result = await trader.close_trade(trade, current_price, reason)
    
    if result.get("success"):
        pnl = result.get("pnl", 0)
        print(f"✅ Closed {trade.symbol}: ${current_price:.2f} | PnL: ${pnl:+.2f}")
        return True
    else:
        print(f"❌ Failed to close {trade.symbol}: {result.get('error')}")
        return False


async def close_old_positions(hours: int):
    """Закрыть позиции старше N часов"""
    positions = await get_open_positions()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    old_positions = [p for p in positions if p.entry_time < cutoff]
    
    print(f"\n📊 Found {len(positions)} open positions")
    print(f"   {len(old_positions)} older than {hours} hours")
    
    if not old_positions:
        print("✅ No old positions to close")
        return
    
    closed = 0
    total_pnl = 0.0
    
    for trade in old_positions:
        age_hours = (datetime.utcnow() - trade.entry_time).total_seconds() / 3600
        print(f"\n🔄 Closing {trade.symbol} (age: {age_hours:.1f}h)...")
        
        if await close_position(trade, f"Auto-close: older than {hours}h"):
            closed += 1
    
    print(f"\n✅ Closed {closed}/{len(old_positions)} old positions")


async def close_all_positions():
    """Закрыть ВСЕ позиции"""
    positions = await get_open_positions()
    
    print(f"\n🚨 Closing ALL {len(positions)} positions...")
    
    if not positions:
        print("✅ No positions to close")
        return
    
    closed = 0
    
    for trade in positions:
        print(f"\n🔄 Closing {trade.symbol}...")
        if await close_position(trade, "Manual close: close_all"):
            closed += 1
    
    print(f"\n✅ Closed {closed}/{len(positions)} positions")


async def keep_only_recent(limit: int):
    """Оставить только N последних позиций"""
    positions = await get_open_positions()
    
    print(f"\n📊 Found {len(positions)} open positions")
    print(f"   Keeping {limit} most recent")
    
    if len(positions) <= limit:
        print("✅ No positions to close")
        return
    
    # Позиции уже отсортированы по времени (новые первые)
    to_close = positions[limit:]
    
    print(f"   Closing {len(to_close)} oldest positions...")
    
    closed = 0
    
    for trade in to_close:
        age_hours = (datetime.utcnow() - trade.entry_time).total_seconds() / 3600
        print(f"\n🔄 Closing {trade.symbol} (age: {age_hours:.1f}h)...")
        
        if await close_position(trade, f"Auto-close: keeping only {limit} positions"):
            closed += 1
    
    print(f"\n✅ Closed {closed}/{len(to_close)} positions")


async def main():
    parser = argparse.ArgumentParser(description='Close old positions')
    parser.add_argument('--hours', type=int, help='Close positions older than N hours')
    parser.add_argument('--all', action='store_true', help='Close ALL positions')
    parser.add_argument('--limit', type=int, help='Keep only N most recent positions')
    parser.add_argument('--list', action='store_true', help='List open positions')
    
    args = parser.parse_args()
    
    await init_db()
    
    if args.list:
        positions = await get_open_positions()
        print(f"\n📊 Open positions: {len(positions)}")
        for p in positions[:20]:
            age = (datetime.utcnow() - p.entry_time).total_seconds() / 3600
            print(f"   {p.symbol}: ${p.entry_price:.2f} x {p.quantity:.4f} | Age: {age:.1f}h")
        if len(positions) > 20:
            print(f"   ... and {len(positions) - 20} more")
    
    elif args.all:
        await close_all_positions()
    
    elif args.hours:
        await close_old_positions(args.hours)
    
    elif args.limit:
        await keep_only_recent(args.limit)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
