"""
Тест Smart AI Brain (ML Gatekeeper Architecture)
"""
import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_brain_smart import get_smart_ai_brain


async def test_smart_ai():
    """Тест Smart AI Brain"""
    
    print("="*80)
    print("🧪 Testing Smart AI Brain (ML Gatekeeper)")
    print("="*80)
    
    brain = get_smart_ai_brain()
    
    # Тестовые сценарии
    test_cases = [
        {
            "name": "Сильный BUY сигнал (ML уверен + TA подтверждает)",
            "data": {
                "symbol": "BTCUSDT",
                "price": 43500.0,
                "rsi": 45.0,  # Нейтральный
                "macd": {"value": 50.0, "signal": 30.0, "trend": "BULLISH"},
                "bollinger_bands": {"upper": 44000, "middle": 43000, "lower": 42000, "position": "MIDDLE"},
                "trend": "BULLISH",
                "volume_trend": "HIGH",
                "technical_signal": "BUY",
                "ema_20": 43200,
                "ema_50": 42800,
                "volume": 1000000
            }
        },
        {
            "name": "Противоречие (ML говорит BUY, TA говорит SELL)",
            "data": {
                "symbol": "ETHUSDT",
                "price": 2250.0,
                "rsi": 75.0,  # Перекупленность
                "macd": {"value": -10.0, "signal": 5.0, "trend": "BEARISH"},
                "bollinger_bands": {"upper": 2300, "middle": 2200, "lower": 2100, "position": "ABOVE_UPPER"},
                "trend": "BEARISH",
                "volume_trend": "LOW",
                "technical_signal": "SELL",
                "ema_20": 2260,
                "ema_50": 2280,
                "volume": 500000
            }
        },
        {
            "name": "Нейтральная ситуация (HOLD)",
            "data": {
                "symbol": "BTCUSDT",
                "price": 43000.0,
                "rsi": 50.0,
                "macd": {"value": 0.0, "signal": 0.0, "trend": "NEUTRAL"},
                "bollinger_bands": {"upper": 44000, "middle": 43000, "lower": 42000, "position": "MIDDLE"},
                "trend": "NEUTRAL",
                "volume_trend": "NORMAL",
                "technical_signal": "SKIP",
                "ema_20": 43000,
                "ema_50": 43000,
                "volume": 800000
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case #{i}: {test_case['name']}")
        print(f"{'='*80}")
        
        result = await brain.decide_trade(test_case['data'])
        
        print(f"\n📊 Result:")
        print(f"   Decision: {result['decision']}")
        print(f"   Confidence: {result['confidence']:.0%}")
        print(f"   Risk Score: {result['risk_score']}/10")
        print(f"   Source: {result['source']}")
        print(f"   Position Multiplier: {result['position_size_multiplier']:.0%}")
        print(f"   Reasoning: {result['reasoning']}")
        
        await asyncio.sleep(2)
    
    # Статистика
    print(f"\n{'='*80}")
    brain.print_stats()
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_smart_ai())
