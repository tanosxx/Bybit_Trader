"""
Проверка исторических данных в БД
"""
import sys
sys.path.append('/app')

import asyncio
from database.db import async_session
from sqlalchemy import text


async def check_data():
    """Проверить данные в БД"""
    print("\n" + "="*60)
    print("📊 Checking Historical Data in Database")
    print("="*60)
    
    async with async_session() as session:
        # Проверяем klines
        result = await session.execute(text("""
            SELECT 
                symbol,
                COUNT(*) as count,
                MIN(timestamp) as first_date,
                MAX(timestamp) as last_date
            FROM klines
            GROUP BY symbol
            ORDER BY symbol
        """))
        
        klines_data = result.fetchall()
        
        if klines_data:
            print("\n📈 Klines Data:")
            print(f"{'Symbol':<15} {'Count':<10} {'First Date':<25} {'Last Date':<25}")
            print("-" * 80)
            for row in klines_data:
                print(f"{row[0]:<15} {row[1]:<10} {str(row[2]):<25} {str(row[3]):<25}")
        else:
            print("\n❌ No klines data found")
        
        # Проверяем trades
        result = await session.execute(text("""
            SELECT COUNT(*) FROM trades
        """))
        trades_count = result.scalar()
        print(f"\n💼 Trades: {trades_count}")
        
        # Проверяем wallet history
        result = await session.execute(text("""
            SELECT COUNT(*) FROM wallet_history
        """))
        wallet_count = result.scalar()
        print(f"💰 Wallet History: {wallet_count}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(check_data())
