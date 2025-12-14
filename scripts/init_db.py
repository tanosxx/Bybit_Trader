"""
Инициализация базы данных
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.db import init_db


async def main():
    """Инициализация БД"""
    print("🔧 Initializing database...")
    await init_db()
    print("✅ Database initialized!")


if __name__ == "__main__":
    asyncio.run(main())
