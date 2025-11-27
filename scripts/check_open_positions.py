"""Проверка открытых позиций"""
import asyncio
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select

async def main():
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        trades = result.scalars().all()
        
        print(f"Открытых позиций в БД: {len(trades)}")
        for t in trades:
            print(f"\nID: {t.id}")
            print(f"Symbol: {t.symbol}")
            print(f"Side: {t.side.value}")
            print(f"Entry Price: ${t.entry_price:.2f}")
            print(f"Quantity: {t.quantity}")
            print(f"Entry Time: {t.entry_time}")
            print(f"Stop Loss: ${t.stop_loss:.2f}")
            print(f"Take Profit: ${t.take_profit:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
