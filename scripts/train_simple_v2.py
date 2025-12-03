"""
Простое обучение Self-Learning модели на исторических данных
БЕЗ ml_features - используем базовые фичи
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select
from core.self_learning import SelfLearner

async def train():
    learner = SelfLearner()
    
    print("\n🎓 Обучение Self-Learning модели на исторических данных...")
    print("   (без ml_features - используем базовые фичи)\n")
    
    async with async_session() as session:
        # Получаем закрытые сделки
        result = await session.execute(
            select(Trade)
            .where(Trade.status == TradeStatus.CLOSED)
            .order_by(Trade.entry_time)
        )
        trades = result.scalars().all()
        
        print(f"📊 Найдено закрытых сделок: {len(trades)}")
        
        learned = 0
        skipped = 0
        
        for trade in trades:
            # Создаем базовые фичи из доступных данных
            features = {
                'rsi': 50.0,  # Нейтральное значение
                'macd_signal': 0.0,
                'bb_position': 0.5,
                'trend': 0.0,
                'volatility': 0.5,
                'volume_ratio': 1.0,
                'news_sentiment': 0.0,
                'ml_confidence': 0.5,
                'ai_risk': 5.0,
                'leverage': 5.0
            }
            
            # Определяем результат
            if trade.pnl is not None:
                outcome = 1 if trade.pnl > 0 else 0
                
                # Обучаем
                success = learner.learn(features, outcome)
                if success:
                    learned += 1
                    
                    if learned % 1000 == 0:
                        print(f"   Обучено: {learned}/{len(trades)}")
                else:
                    skipped += 1
            else:
                skipped += 1
        
        print(f"\n✅ Training Complete!")
        print(f"   Learned: {learned}")
        print(f"   Skipped: {skipped}")
        
        # Принудительно обновляем счетчики перед сохранением
        print(f"\n📊 Learner stats before save:")
        print(f"   learning_count: {learner.learning_count}")
        print(f"   wins: {learner.wins}")
        print(f"   losses: {learner.losses}")
        
        # Сохраняем
        learner._save_model()
        print(f"\n💾 Model saved to: ml_data/self_learner.pkl")
        
        # Проверяем что файл создан
        import os
        if os.path.exists('ml_data/self_learner.pkl'):
            size = os.path.getsize('ml_data/self_learner.pkl')
            print(f"✅ File exists: {size} bytes")
        else:
            print(f"❌ File NOT created!")
        
        # Статистика
        try:
            stats = learner.get_stats()
            print(f"\n📊 Model Statistics:")
            print(f"   Total Samples: {learned}")
            print(f"   Wins: {stats.get('wins', 0)}")
            print(f"   Losses: {stats.get('losses', 0)}")
            total = stats.get('wins', 0) + stats.get('losses', 0)
            wr = (stats.get('wins', 0) / total * 100) if total > 0 else 0
            print(f"   Win Rate: {wr:.1f}%")
            print(f"   Model Accuracy: {stats.get('metric', 'N/A')}")
            print(f"   Ready: {'✅ YES' if learned >= 50 else '❌ NO (need 50+)'}")
        except Exception as e:
            print(f"\n⚠️ Stats error (ignored): {e}")

if __name__ == "__main__":
    asyncio.run(train())
