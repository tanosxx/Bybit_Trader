"""
Обучить Self-Learning на исторических свечах

Стратегия:
1. Берём исторические свечи из БД
2. Для каждой свечи рассчитываем фичи (RSI, MACD, etc.)
3. Смотрим что произошло через N свечей (цена выросла/упала)
4. Обучаем модель на этих данных

ВАЖНО: Используем ту же логику что и в боте!
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.self_learning import get_self_learner
from core.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands
from database.db import async_session
from database.models import Candle
from sqlalchemy import select
import pandas as pd


async def train_on_history(limit_per_symbol: int = 1000):
    """
    Обучить на исторических данных
    
    Args:
        limit_per_symbol: Сколько свечей использовать на символ (1000 = ~10 дней)
    """
    print(f"🧠 Training Self-Learning on historical data...")
    print(f"   Limit: {limit_per_symbol} candles per symbol\n")
    
    learner = get_self_learner()
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    
    total_learned = 0
    total_wins = 0
    total_losses = 0
    
    for symbol in symbols:
        print(f"📊 Processing {symbol}...")
        
        # Загружаем свечи
        async with async_session() as session:
            result = await session.execute(
                select(Candle).where(
                    Candle.symbol == symbol
                ).order_by(Candle.timestamp.desc()).limit(limit_per_symbol)
            )
            candles = list(result.scalars().all())
        
        if len(candles) < 50:
            print(f"   ⚠️ Not enough candles: {len(candles)}")
            continue
        
        # Конвертируем в DataFrame
        df = pd.DataFrame([{
            'time': c.timestamp,
            'open': float(c.open),
            'high': float(c.high),
            'low': float(c.low),
            'close': float(c.close),
            'volume': float(c.volume)
        } for c in reversed(candles)])
        
        # Рассчитываем индикаторы (простые версии)
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD (простая версия)
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        
        # Volatility
        df['volatility'] = df['close'].pct_change().rolling(20).std()
        
        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Удаляем NaN
        df = df.dropna()
        
        learned = 0
        wins = 0
        losses = 0
        
        # Обучаем на каждой свече
        for i in range(len(df) - 5):  # -5 чтобы смотреть вперёд
            row = df.iloc[i]
            
            # Фичи
            features = {
                'rsi': float(row['rsi']),
                'macd_bullish': 1.0 if row['macd'] > row['macd_signal'] else 0.0,
                'bb_upper': 1.0 if row['close'] > row['bb_upper'] else 0.0,
                'bb_lower': 1.0 if row['close'] < row['bb_lower'] else 0.0,
                'trend_up': 1.0 if row['close'] > df.iloc[max(0, i-20):i]['close'].mean() else 0.0,
                'trend_strength': abs(row['close'] - df.iloc[max(0, i-20):i]['close'].mean()) / row['close'],
                'volatility': float(row['volatility']) if pd.notna(row['volatility']) else 0.0,
                'volume_ratio': float(row['volume_ratio']) if pd.notna(row['volume_ratio']) else 1.0,
                'news_score': 0.0,  # Нет исторических новостей
                'ml_confidence': 0.5  # Нейтральный
            }
            
            # Результат: смотрим что произошло через 5 свечей
            future_price = df.iloc[i + 5]['close']
            current_price = row['close']
            price_change = (future_price - current_price) / current_price
            
            # Win если цена выросла > 0.5% (минимальный профит после комиссий)
            result = 1 if price_change > 0.005 else 0
            
            # Обучаем
            success = learner.learn(features, result)
            
            if success:
                learned += 1
                if result == 1:
                    wins += 1
                else:
                    losses += 1
        
        win_rate = (wins / learned * 100) if learned > 0 else 0
        print(f"   ✅ Learned: {learned} samples, WR: {win_rate:.1f}%")
        
        total_learned += learned
        total_wins += wins
        total_losses += losses
    
    # Финальная статистика
    total_wr = (total_wins / total_learned * 100) if total_learned > 0 else 0
    
    print(f"\n✅ Training complete!")
    print(f"   Total samples: {total_learned}")
    print(f"   Wins: {total_wins}")
    print(f"   Losses: {total_losses}")
    print(f"   Win Rate: {total_wr:.1f}%")
    
    # Статистика модели
    stats = learner.get_stats()
    print(f"\n📊 Model stats:")
    print(f"   Learned samples: {stats['learned_samples']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")


if __name__ == "__main__":
    # Обучаем на последних 1000 свечах на символ
    # 1000 свечей × 15 минут = ~10 дней данных
    asyncio.run(train_on_history(limit_per_symbol=1000))
