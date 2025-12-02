"""
Train Self-Learning Model on Historical Trades

Обучает модель на закрытых сделках из БД.
Для старых сделок без ml_features - реконструирует фичи из доступных данных.
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime
from sqlalchemy import select
from database.db import async_session, init_db
from database.models import Trade, TradeStatus
from core.self_learning import get_self_learner


async def reconstruct_features_from_trade(trade: Trade) -> dict:
    """
    Реконструировать фичи из данных сделки
    
    Для старых сделок без ml_features используем доступные данные:
    - extra_data может содержать indicators
    - ai_reasoning может содержать RSI
    - Остальное - нейтральные значения
    """
    # Пытаемся извлечь из extra_data
    extra = trade.extra_data or {}
    
    # Базовые нейтральные фичи
    features = {
        'rsi': 50.0,
        'macd_bullish': 0.5,
        'bb_upper': 0.0,
        'bb_lower': 0.0,
        'trend_up': 0.5,
        'trend_strength': 0.5,
        'volatility': 0.02,
        'volume_ratio': 1.0,
        'news_score': 0.0,
        'ml_confidence': extra.get('confidence', 0.5)
    }
    
    # Пытаемся извлечь RSI из reasoning
    if trade.ai_reasoning:
        import re
        rsi_match = re.search(r'RSI[:\s]+(\d+\.?\d*)', trade.ai_reasoning)
        if rsi_match:
            features['rsi'] = float(rsi_match.group(1))
    
    # Определяем направление тренда по стороне сделки
    if trade.side.value == 'BUY':
        features['trend_up'] = 0.6  # Вероятно восходящий тренд
    else:
        features['trend_up'] = 0.4  # Вероятно нисходящий тренд
    
    return features


async def train_on_historical_trades():
    """Обучить модель на исторических сделках"""
    
    print("🧠 Training Self-Learning Model on Historical Data")
    print("=" * 60)
    
    # Инициализируем БД
    await init_db()
    
    # Создаем НОВЫЙ экземпляр (не Singleton) для обучения
    from core.self_learning import SelfLearner
    learner = SelfLearner()
    
    # Показываем текущее состояние
    if learner.enabled:
        stats = learner.get_stats()
        print(f"\n📊 Current Model State:")
        print(f"   Samples: {stats['learned_samples']}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Model: {type(learner.model)}")
    
    if not learner.enabled:
        print("❌ Self-Learner not available!")
        return
    
    # Получаем закрытые сделки
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.pnl.isnot(None)
            ).order_by(Trade.exit_time)
        )
        trades = result.scalars().all()
    
    print(f"\n📊 Found {len(trades)} closed trades")
    
    if len(trades) == 0:
        print("⚠️  No trades to learn from")
        return
    
    # Обучаем на каждой сделке
    learned_count = 0
    skipped_count = 0
    
    for i, trade in enumerate(trades, 1):
        try:
            # Получаем или реконструируем фичи
            if trade.ml_features:
                features = trade.ml_features
            else:
                features = await reconstruct_features_from_trade(trade)
            
            # Определяем результат: Win = 1, Loss = 0
            result = 1 if trade.pnl > 0 else 0
            
            # Обучаем
            success = learner.learn(features, result)
            
            if success:
                learned_count += 1
                if i % 50 == 0:
                    stats = learner.get_stats()
                    print(f"   Progress: {i}/{len(trades)} | Learned: {learned_count} | Win Rate: {stats['win_rate']:.1f}%")
            else:
                skipped_count += 1
                if i <= 3:  # Отладка первых 3 сделок
                    print(f"   ⚠️  Skipped trade {trade.id}: features={features}, result={result}")
        
        except Exception as e:
            print(f"   ⚠️  Error on trade {trade.id}: {e}")
            skipped_count += 1
            continue
    
    # Финальная статистика
    print(f"\n✅ Training Complete!")
    print(f"   Learned: {learned_count}")
    print(f"   Skipped: {skipped_count}")
    
    stats = learner.get_stats()
    print(f"\n📊 Model Statistics:")
    print(f"   Total Samples: {stats['learned_samples']}")
    print(f"   Wins: {stats['wins']}")
    print(f"   Losses: {stats['losses']}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Model Accuracy: {stats['model_accuracy']:.2%}")
    print(f"   Ready: {'✅ YES' if stats['ready'] else '❌ NO (need 50+)'}")
    
    # Сохраняем модель
    learner._save_model()
    print(f"\n💾 Model saved to: {learner.model_path}")


if __name__ == "__main__":
    asyncio.run(train_on_historical_trades())
