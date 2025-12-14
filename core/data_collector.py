"""
Сбор и сохранение исторических данных для обучения ML
"""
import asyncio
from datetime import datetime
from typing import List, Dict
from database.db import async_session
from database.models import Candle
from core.bybit_api import get_bybit_api
from sqlalchemy import select, and_


class DataCollector:
    """Сборщик исторических данных"""
    
    def __init__(self):
        self.bybit_api = get_bybit_api()
    
    async def save_candles(self, symbol: str, interval: str, candles: List[Dict]):
        """
        Сохранить свечи в БД
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            interval: 1, 5, 15, 60
            candles: список свечей
        """
        if not candles:
            return
        
        async with async_session() as session:
            saved_count = 0
            
            for candle_data in candles:
                # Проверяем существует ли уже
                timestamp = datetime.fromtimestamp(candle_data['timestamp'] / 1000)
                
                result = await session.execute(
                    select(Candle).where(
                        and_(
                            Candle.symbol == symbol,
                            Candle.interval == interval,
                            Candle.timestamp == timestamp
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    candle = Candle(
                        symbol=symbol,
                        interval=interval,
                        timestamp=timestamp,
                        open=candle_data['open'],
                        high=candle_data['high'],
                        low=candle_data['low'],
                        close=candle_data['close'],
                        volume=candle_data['volume']
                    )
                    session.add(candle)
                    saved_count += 1
            
            await session.commit()
            
            if saved_count > 0:
                print(f"💾 Saved {saved_count} new candles for {symbol} ({interval}m)")
    
    async def collect_historical_data(self, symbol: str, interval: str = "1", limit: int = 1000):
        """
        Собрать исторические данные
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            interval: 1, 5, 15, 60
            limit: количество свечей
        """
        print(f"📊 Collecting historical data for {symbol} ({interval}m)...")
        
        candles = await self.bybit_api.get_klines(symbol, interval, limit=limit)
        
        if candles:
            await self.save_candles(symbol, interval, candles)
            print(f"✅ Collected {len(candles)} candles for {symbol}")
        else:
            print(f"❌ Failed to collect data for {symbol}")
    
    async def get_training_data(self, symbol: str, interval: str = "1", limit: int = 1000) -> List[Candle]:
        """
        Получить данные для обучения из БД
        
        Returns:
            List of Candle objects
        """
        async with async_session() as session:
            result = await session.execute(
                select(Candle)
                .where(
                    and_(
                        Candle.symbol == symbol,
                        Candle.interval == interval
                    )
                )
                .order_by(Candle.timestamp.desc())
                .limit(limit)
            )
            candles = result.scalars().all()
            
            # Возвращаем в хронологическом порядке
            return list(reversed(candles))


# Singleton
_data_collector = None

def get_data_collector() -> DataCollector:
    """Получить singleton instance"""
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
    return _data_collector
