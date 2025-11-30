"""
Синхронизация позиций с биржей - закрываем фантомные позиции в БД
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select
from core.bybit_api import get_bybit_api
from config import settings

async def main():
    api = get_bybit_api()
    
    print("\n" + "="*80)
    print("🔄 SYNC POSITIONS WITH EXCHANGE")
    print("="*80 + "\n")
    
    # 1. Получаем реальные позиции с биржи
    print("📊 Получаем позиции с биржи...")
    real_positions = {}
    for symbol in settings.futures_pairs:
        positions = await api.get_positions(symbol)
        for pos in positions:
            if pos['size'] > 0:
                real_positions[symbol] = pos
                print(f"   ✅ {symbol} {pos['side']}: {pos['size']} @ ${pos['entry_price']:.2f}")
    
    if not real_positions:
        print("   📭 Нет открытых позиций на бирже")
    
    # 2. Получаем позиции из БД
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        db_trades = list(result.scalars().all())
        
        print(f"\n📋 Позиций в БД: {len(db_trades)}")
        
        # 3. Закрываем фантомные позиции
        phantom_count = 0
        for trade in db_trades:
            # Проверяем есть ли эта позиция на бирже
            if trade.symbol not in real_positions:
                # Фантомная позиция - закрываем в БД
                trade.status = TradeStatus.CLOSED
                trade.exit_time = datetime.utcnow()
                trade.exit_price = trade.entry_price
                trade.pnl = 0.0
                trade.pnl_pct = 0.0
                trade.exit_reason = "Phantom position (not on exchange)"
                phantom_count += 1
                print(f"   🗑️ Закрыта фантомная: {trade.symbol} {trade.side.value}")
        
        await session.commit()
        
        print(f"\n✅ Закрыто фантомных позиций: {phantom_count}")
        print(f"✅ Осталось реальных позиций: {len(db_trades) - phantom_count}")
    
    print("\n" + "="*80)
    print("✅ SYNC COMPLETE!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
