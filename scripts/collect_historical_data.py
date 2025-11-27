"""
Скрипт для сбора исторических данных с Bybit API
Собирает максимум исторических свечей и сохраняет в PostgreSQL

Запускать на сервере в Docker:
docker exec bybit_bot python scripts/collect_historical_data.py
"""
import asyncio
import sys
sys.path.append('/app')

from datetime import datetime, timedelta
from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Candle
from sqlalchemy import select, and_
from config import settings


class HistoricalDataCollector:
    """Сборщик исторических данных"""
    
    def __init__(self):
        self.api = get_bybit_api()
        # Расширенный список торговых пар
        self.symbols = [
            "BTCUSDT",   # Bitcoin
            "ETHUSDT",   # Ethereum
            "SOLUSDT",   # Solana
            "BNBUSDT",   # Binance Coin
            "XRPUSDT"    # Ripple
        ]
        self.intervals = ["60"]  # 1 hour (можно добавить "240", "D")
        
    async def collect_all_data(self, days_back: int = 90):
        """
        Собрать все исторические данные
        
        Args:
            days_back: сколько дней назад собирать (default: 90 дней = 3 месяца)
        """
        print("\n" + "="*60)
        print("🚀 Starting Historical Data Collection")
        print("="*60)
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Intervals: {', '.join(self.intervals)}")
        print(f"Period: Last {days_back} days")
        print("="*60 + "\n")
        
        total_collected = 0
        
        for symbol in self.symbols:
            for interval in self.intervals:
                collected = await self.collect_symbol_data(
                    symbol, interval, days_back
                )
                total_collected += collected
        
        print("\n" + "="*60)
        print(f"✅ Collection Complete!")
        print(f"Total candles collected: {total_collected}")
        print("="*60 + "\n")
        
        return total_collected
    
    async def collect_symbol_data(
        self, 
        symbol: str, 
        interval: str, 
        days_back: int
    ) -> int:
        """
        Собрать данные для одного символа
        
        Returns:
            Количество собранных свечей
        """
        print(f"\n📊 Collecting {symbol} ({interval} interval)...")
        
        # Рассчитываем временной диапазон
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
        
        print(f"   Period: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
        
        # Проверяем что уже есть в БД
        existing_count = await self.get_existing_count(symbol, interval)
        print(f"   Existing in DB: {existing_count} candles")
        
        # Получаем данные с API
        klines = await self.api.get_klines_historical(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        if not klines:
            print(f"   ❌ No data received from API")
            return 0
        
        # Сохраняем в БД
        saved_count = await self.save_to_database(symbol, interval, klines)
        
        print(f"   ✅ Saved {saved_count} new candles to database")
        
        return saved_count
    
    async def get_existing_count(self, symbol: str, interval: str) -> int:
        """Получить количество существующих записей в БД"""
        async with async_session() as session:
            result = await session.execute(
                select(Candle).where(
                    and_(
                        Candle.symbol == symbol,
                        Candle.interval == interval
                    )
                )
            )
            candles = result.scalars().all()
            return len(candles)
    
    async def save_to_database(
        self, 
        symbol: str, 
        interval: str, 
        klines: list
    ) -> int:
        """
        Сохранить свечи в БД (избегая дубликатов)
        
        Returns:
            Количество сохранённых записей
        """
        saved_count = 0
        
        async with async_session() as session:
            for kline in klines:
                # Проверяем существует ли уже эта свеча
                timestamp_dt = datetime.fromtimestamp(kline['timestamp'] / 1000)
                
                result = await session.execute(
                    select(Candle).where(
                        and_(
                            Candle.symbol == symbol,
                            Candle.interval == interval,
                            Candle.timestamp == timestamp_dt
                        )
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Свеча уже существует, пропускаем
                    continue
                
                # Создаём новую свечу
                candle = Candle(
                    symbol=symbol,
                    interval=interval,
                    timestamp=timestamp_dt,
                    open=kline['open'],
                    high=kline['high'],
                    low=kline['low'],
                    close=kline['close'],
                    volume=kline['volume']
                )
                
                session.add(candle)
                saved_count += 1
            
            await session.commit()
        
        return saved_count
    
    async def get_statistics(self):
        """Получить статистику по собранным данным"""
        print("\n" + "="*60)
        print("📈 Database Statistics")
        print("="*60)
        
        async with async_session() as session:
            for symbol in self.symbols:
                for interval in self.intervals:
                    result = await session.execute(
                        select(Candle).where(
                            and_(
                                Candle.symbol == symbol,
                                Candle.interval == interval
                            )
                        ).order_by(Candle.timestamp)
                    )
                    candles = result.scalars().all()
                    
                    if candles:
                        first = candles[0]
                        last = candles[-1]
                        
                        print(f"\n{symbol} ({interval}):")
                        print(f"   Total candles: {len(candles)}")
                        print(f"   First: {first.timestamp}")
                        print(f"   Last: {last.timestamp}")
                        print(f"   Period: {(last.timestamp - first.timestamp).days} days")
                    else:
                        print(f"\n{symbol} ({interval}): No data")
        
        print("\n" + "="*60)


async def main():
    """Главная функция"""
    collector = HistoricalDataCollector()
    
    # Собираем данные за последний год (365 дней)
    # Это даст нам ~8,760 свечей на пару (1h интервал)
    # Всего: 5 пар × 8,760 = ~43,800 свечей
    await collector.collect_all_data(days_back=365)
    
    # Показываем статистику
    await collector.get_statistics()


if __name__ == "__main__":
    asyncio.run(main())
