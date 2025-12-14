"""Очистка старых открытых позиций из БД"""
import asyncio
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select, update

async def main():
    async with async_session() as session:
        # Получаем все открытые позиции
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = result.scalars().all()
        
        print(f"Найдено открытых позиций: {len(open_trades)}")
        
        if len(open_trades) > 0:
            print("\nУдаляем старые открытые позиции:")
            for trade in open_trades:
                print(f"  - {trade.symbol} {trade.side.value} @ ${trade.entry_price:.2f} (ID: {trade.id})")
                await session.delete(trade)
            
            await session.commit()
            print(f"\n✅ Удалено {len(open_trades)} позиций")
        else:
            print("✅ Нет открытых позиций для удаления")

if __name__ == "__main__":
    asyncio.run(main())
