"""
Скрипт для экспорта исторических данных в CSV для ML обучения
Добавляет технические индикаторы и временные фичи

Запускать на сервере в Docker:
docker exec bybit_bot python scripts/export_historical_data.py
"""
import asyncio
import sys
sys.path.append('/app')

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from database.db import async_session
from database.models import Candle
from sqlalchemy import select, and_
from core.indicators import add_all_indicators


class HistoricalDataExporter:
    """Экспортер исторических данных для ML"""
    
    def __init__(self):
        self.export_dir = Path("/data/ml_export")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
        self.intervals = ["60"]  # 1 hour
        
    async def export_all_data(self):
        """Экспортировать все данные"""
        print("\n" + "="*60)
        print("🚀 Starting Data Export for ML")
        print("="*60)
        print(f"Export directory: {self.export_dir}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print("="*60 + "\n")
        
        exported_files = []
        total_records = 0
        
        for symbol in self.symbols:
            for interval in self.intervals:
                file_path, records = await self.export_symbol_data(symbol, interval)
                if file_path:
                    exported_files.append(file_path)
                    total_records += records
        
        # Создаём metadata файл
        metadata = await self.create_metadata(exported_files, total_records)
        
        print("\n" + "="*60)
        print(f"✅ Export Complete!")
        print(f"Total files: {len(exported_files)}")
        print(f"Total records: {total_records}")
        print(f"Metadata: {self.export_dir}/metadata.json")
        print("="*60 + "\n")
        
        return exported_files
    
    async def export_symbol_data(self, symbol: str, interval: str) -> tuple:
        """
        Экспортировать данные для одного символа
        
        Returns:
            (file_path, record_count)
        """
        print(f"\n📊 Exporting {symbol} ({interval})...")
        
        # Читаем данные из БД
        async with async_session() as session:
            result = await session.execute(
                select(Candle).where(
                    and_(
                        Candle.symbol == symbol,
                        Candle.interval == interval
                    )
                ).order_by(Candle.timestamp)
            )
            candles = result.scalars().all()
        
        if not candles:
            print(f"   ❌ No data found in database")
            return None, 0
        
        print(f"   Loaded {len(candles)} candles from database")
        
        # Конвертируем в DataFrame
        df = pd.DataFrame([
            {
                'timestamp': c.timestamp,
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume
            }
            for c in candles
        ])
        
        # Добавляем технические индикаторы
        print(f"   Calculating technical indicators...")
        df = add_all_indicators(df)
        
        # Добавляем временные фичи
        print(f"   Adding temporal features...")
        df = self.add_temporal_features(df)
        
        # Удаляем NaN (первые строки где индикаторы не рассчитаны)
        df = df.dropna()
        
        print(f"   After cleaning: {len(df)} records")
        
        # Сохраняем в CSV
        filename = f"klines_{symbol}_{interval}.csv"
        file_path = self.export_dir / filename
        
        df.to_csv(file_path, index=False)
        
        print(f"   ✅ Saved to {filename}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Records: {len(df)}")
        
        return str(file_path), len(df)
    
    def add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить временные фичи
        
        Args:
            df: DataFrame с колонкой timestamp
        
        Returns:
            DataFrame с добавленными временными фичами
        """
        # Конвертируем timestamp в datetime если нужно
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Временные фичи
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['quarter'] = df['timestamp'].dt.quarter
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Циклические фичи (для лучшего представления времени)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        return df
    
    async def create_metadata(self, exported_files: list, total_records: int) -> dict:
        """Создать metadata файл с описанием датасета"""
        metadata = {
            "export_date": datetime.now().isoformat(),
            "total_files": len(exported_files),
            "total_records": total_records,
            "symbols": self.symbols,
            "intervals": self.intervals,
            "files": []
        }
        
        # Информация о каждом файле
        for file_path in exported_files:
            file_path = Path(file_path)
            if file_path.exists():
                df = pd.read_csv(file_path, nrows=1)
                
                metadata["files"].append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "columns": list(df.columns),
                    "column_count": len(df.columns)
                })
        
        # Сохраняем metadata
        metadata_path = self.export_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n📄 Metadata saved to {metadata_path}")
        
        return metadata
    
    async def show_sample_data(self):
        """Показать пример данных из первого файла"""
        print("\n" + "="*60)
        print("📋 Sample Data (first 5 rows)")
        print("="*60)
        
        csv_files = list(self.export_dir.glob("klines_*.csv"))
        if csv_files:
            df = pd.read_csv(csv_files[0], nrows=5)
            print(f"\nFile: {csv_files[0].name}")
            print(f"Columns: {list(df.columns)}")
            print(f"\n{df.to_string()}")
        
        print("\n" + "="*60)


async def main():
    """Главная функция"""
    exporter = HistoricalDataExporter()
    
    # Экспортируем все данные
    await exporter.export_all_data()
    
    # Показываем пример данных
    await exporter.show_sample_data()


if __name__ == "__main__":
    import numpy as np  # Нужен для циклических фичей
    asyncio.run(main())
