"""
Очистка фантомных позиций - закрываем в БД без продажи на бирже
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select, update

async def main():
    async with async_session() as session:
        # Получаем все открытые позиции
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        trades = list(result.scalars().all())
        
        print(f"\n{'='*80}")
        print(f"🧹 CLEANUP PHANTOM TRADES - {len(trades)} открытых позиций")
        print(f"{'='*80}\n")
        
        if len(trades) == 0:
            print("✅ Нет открытых позиций")
            return
        
        # Закрываем все в БД
        for trade in trades:
            trade.status = TradeStatus.CLOSED
            trade.exit_time = datetime.utcnow()
            trade.exit_price = trade.entry_price  # Закрываем по цене входа (0 PnL)
            trade.pnl = 0.0
            trade.pnl_pct = 0.0
            trade.exit_reason = "Phantom trade cleanup"
        
        await session.commit()
        
        print(f"✅ Закрыто {len(trades)} позиций в БД")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
