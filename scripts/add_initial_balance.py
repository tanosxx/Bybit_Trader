"""
Добавить начальную запись баланса в БД
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import settings


async def add_initial_balance():
    """Добавить начальную запись баланса"""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Проверяем есть ли записи
        result = await session.execute(text("SELECT COUNT(*) FROM wallet_history"))
        count = result.scalar()
        
        if count == 0:
            print("📝 Добавляем начальную запись баланса...")
            
            # Добавляем начальную запись
            await session.execute(text("""
                INSERT INTO wallet_history (time, balance_usdt, equity, change_amount, change_reason)
                VALUES (:time, :balance, :equity, :change, :reason)
            """), {
                "time": datetime.utcnow(),
                "balance": 124471.32,
                "equity": 124471.32,
                "change": 0.0,
                "reason": "Initial balance"
            })
            
            await session.commit()
            print("✅ Начальная запись добавлена!")
        else:
            print(f"ℹ️ В БД уже есть {count} записей")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_initial_balance())
