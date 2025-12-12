"""
Пересоздать Self-Learning модель с правильными данными из БД
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.self_learning import get_self_learner
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select


async def reset_and_retrain():
    print("🔄 Resetting Self-Learning model...\n")
    
    # Удаляем старую модель
    import os
    model_path = "ml_data/self_learner.pkl"
    if os.path.exists(model_path):
        os.remove(model_path)
        print(f"✅ Removed old model: {model_path}\n")
    
    # Создаём новую модель
    learner = get_self_learner()
    print(f"✅ Created new model\n")
    
    # Получаем все закрытые сделки из БД
    print("📊 Loading trades from database...")
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.ml_features.isnot(None)  # Только с фичами
            ).order_by(Trade.exit_time)
        )
        trades = list(result.scalars().all())
    
    print(f"   Found {len(trades)} trades with ML features\n")
    
    # Обучаем на каждой сделке
    print("🧠 Training model...")
    learned = 0
    wins = 0
    losses = 0
    
    for trade in trades:
        if not trade.ml_features:
            continue
        
        # Определяем результат: Win если net PnL > 0
        net_pnl = trade.pnl - (trade.fee_entry + trade.fee_exit)
        result = 1 if net_pnl > 0 else 0
        
        # Обучаем
        success = learner.learn(trade.ml_features, result)
        
        if success:
            learned += 1
            if result == 1:
                wins += 1
            else:
                losses += 1
            
            if learned % 50 == 0:
                print(f"   Processed {learned}/{len(trades)} trades...")
    
    # Финальная статистика
    win_rate = (wins / learned * 100) if learned > 0 else 0
    
    print(f"\n✅ Training complete!")
    print(f"   Total trades: {learned}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {win_rate:.1f}%")
    
    # Проверяем статистику модели
    stats = learner.get_stats()
    print(f"\n📊 Model stats:")
    print(f"   Learned samples: {stats['learned_samples']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")
    print(f"   Accuracy: {stats.get('accuracy', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(reset_and_retrain())
