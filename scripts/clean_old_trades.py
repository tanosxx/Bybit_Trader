"""
Очистка старых виртуальных сделок из БД
"""
import asyncio
import sys
sys.path.append('/app')

from database.db import async_session, init_db
from database.models import Trade, WalletHistory
from sqlalchemy import delete


async def clean_old_data():
    """Удалить все старые данные"""
    await init_db()
    
    async with async_session() as session:
        # Удаляем все сделки
        await session.execute(delete(Trade))
        print("✅ Удалены все старые сделки")
        
        # Удаляем историю кошелька
        await session.execute(delete(WalletHistory))
        print("✅ Удалена история кошелька")
        
        await session.commit()
        print("✅ База данных очищена!")


if __name__ == "__main__":
    asyncio.run(clean_old_data())
