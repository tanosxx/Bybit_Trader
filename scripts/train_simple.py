"""
Simple Training Script - Direct approach
"""
import asyncio
import sys
import pickle
sys.path.insert(0, '/app')

from datetime import datetime
from sqlalchemy import select
from database.db import async_session, init_db
from database.models import Trade, TradeStatus

try:
    from river import forest, metrics
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    print("❌ River not available")
    sys.exit(1)


async def train():
    print("🧠 Simple Training on Historical Data")
    print("=" * 60)
    
    # Инициализируем БД
    await init_db()
    
    # Создаем модель напрямую
    model = forest.ARFClassifier(
        n_models=10,
        max_features='sqrt',
        lambda_value=6,
        grace_period=50,
        seed=42
    )
    metric = metrics.Accuracy()
    
    print(f"✅ Model created: {type(model)}")
    
    # Получаем сделки
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.pnl.isnot(None)
            ).order_by(Trade.exit_time).limit(500)  # Первые 500 для теста
        )
        trades = result.scalars().all()
    
    print(f"📊 Found {len(trades)} trades")
    
    wins = 0
    losses = 0
    
    # Обучаем
    for i, trade in enumerate(trades, 1):
        # Простые фичи
        features = {
            'rsi': 50.0,
            'confidence': trade.extra_data.get('confidence', 0.5) if trade.extra_data else 0.5,
            'leverage': trade.extra_data.get('leverage', 5) if trade.extra_data else 5,
        }
        
        result = 1 if trade.pnl > 0 else 0
        
        # Обучаем
        model.learn_one(features, result)
        y_pred = model.predict_one(features)
        metric.update(result, y_pred)
        
        if result == 1:
            wins += 1
        else:
            losses += 1
        
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(trades)} | WR: {wins/(wins+losses)*100:.1f}% | Acc: {metric.get():.2%}")
    
    print(f"\n✅ Training Complete!")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {wins/(wins+losses)*100:.1f}%")
    print(f"   Model Accuracy: {metric.get():.2%}")
    
    # Сохраняем
    data = {
        'model': model,
        'metric': metric,
        'predictions_count': 0,
        'learning_count': len(trades),
        'wins': wins,
        'losses': losses,
        'updated_at': datetime.utcnow().isoformat()
    }
    
    with open('ml_data/self_learner.pkl', 'wb') as f:
        pickle.dump(data, f)
    
    print(f"\n💾 Model saved to ml_data/self_learner.pkl")


if __name__ == "__main__":
    asyncio.run(train())
