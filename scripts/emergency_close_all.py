"""
Экстренное закрытие ВСЕХ открытых позиций
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select
from core.bybit_api import get_bybit_api
from core.real_trader import get_real_trader

async def main():
    api = get_bybit_api()
    trader = get_real_trader()
    
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        trades = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"🚨 EMERGENCY CLOSE - {len(trades)} открытых позиций")
        print(f"{'='*80}\n")
        
        closed_count = 0
        failed_count = 0
        
        for i, trade in enumerate(trades, 1):
            print(f"\n[{i}/{len(trades)}] Закрываем {trade.symbol} {trade.side.value}...")
            
            # Получаем текущую цену
            ticker = await api.get_ticker(trade.symbol)
            if not ticker:
                print(f"   ❌ Не удалось получить цену")
                failed_count += 1
                continue
            
            current_price = ticker.get('last_price', 0)
            
            # Закрываем
            result = await trader.close_trade(trade, current_price, "Emergency close")
            
            if result.get('success'):
                closed_count += 1
                print(f"   ✅ Закрыто! PnL: ${result.get('pnl', 0):+.2f}")
            else:
                failed_count += 1
                print(f"   ❌ Ошибка закрытия")
            
            # Небольшая задержка чтобы не спамить API
            await asyncio.sleep(0.5)
        
        print(f"\n{'='*80}")
        print(f"✅ Закрыто: {closed_count}")
        print(f"❌ Ошибок: {failed_count}")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
