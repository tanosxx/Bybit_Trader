"""
Асинхронное подключение к PostgreSQL
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import settings

# Создаем async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base для моделей
Base = declarative_base()


async def init_db():
    """Инициализация базы данных (создание таблиц)"""
    from .models import SystemLog, WalletHistory, Trade, Candle, AppConfig
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализация дефолтных настроек
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(AppConfig).where(AppConfig.key == "strategy_mode"))
        config = result.scalar_one_or_none()
        
        if not config:
            config = AppConfig(key="strategy_mode", value="balanced")
            session.add(config)
            await session.commit()
            print("✅ Default strategy set to 'balanced'")
    
    print("✅ Database initialized successfully")


async def get_strategy() -> str:
    """Получить текущую стратегию из БД"""
    async with async_session() as session:
        from sqlalchemy import select
        from .models import AppConfig
        
        result = await session.execute(select(AppConfig).where(AppConfig.key == "strategy_mode"))
        config = result.scalar_one_or_none()
        
        return config.value if config else "balanced"


async def set_strategy(mode: str) -> bool:
    """Установить стратегию в БД"""
    async with async_session() as session:
        from sqlalchemy import select
        from .models import AppConfig
        from datetime import datetime
        
        result = await session.execute(select(AppConfig).where(AppConfig.key == "strategy_mode"))
        config = result.scalar_one_or_none()
        
        if config:
            config.value = mode
            config.updated_at = datetime.utcnow()
        else:
            config = AppConfig(key="strategy_mode", value=mode)
            session.add(config)
        
        await session.commit()
        return True
