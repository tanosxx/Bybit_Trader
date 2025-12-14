"""
Тест Gemini Live API (WebSockets)
Запуск: python scripts/test_live_api.py
"""
import sys
sys.path.append('.')

import asyncio
from core.ai_brain_live import get_ai_brain_live


async def test_live_api():
    """Тестируем Live API с реальными данными"""
    
    print("="*60)
    print("🧪 Тест Gemini Live API (WebSockets)")
    print("="*60)
    
    # Тестовые данные рынка
    test_market_data = {
        "symbol": "BTCUSDT",
        "price": 95234.50,
        "price_change_24h": 2.34,
        "volume_24h": 28500000000,
        "rsi": 58.5,
        "macd": {
            "value": 125.3,
            "signal": 98.7,
            "histogram": 26.6
        },
        "bollinger_bands": {
            "upper": 96500.0,
            "middle": 95000.0,
            "lower": 93500.0,
            "position": "middle"
        },
        "stochastic": {
            "k": 62.3,
            "d": 58.1
        },
        "trend": "uptrend",
        "volume_trend": "increasing",
        "signal": "BUY"
    }
    
    # Получаем AI Brain
    ai = get_ai_brain_live()
    
    print(f"\n📊 Тестовые данные:")
    print(f"   Symbol: {test_market_data['symbol']}")
    print(f"   Price: ${test_market_data['price']:,.2f}")
    print(f"   RSI: {test_market_data['rsi']}")
    print(f"   Trend: {test_market_data['trend']}")
    
    print(f"\n🤖 Запрос анализа через Live API...")
    
    # Анализируем
    result = await ai.analyze_market(test_market_data)
    
    if result:
        print(f"\n✅ Результат анализа:")
        print(f"   Решение: {result['decision']}")
        print(f"   Риск: {result['risk_score']}/10")
        print(f"   Уверенность: {result['confidence']:.0%}")
        print(f"   Обоснование: {result['reasoning']}")
        print(f"   Ключевые факторы:")
        for factor in result.get('key_factors', []):
            print(f"      - {factor}")
    else:
        print(f"\n❌ Не удалось получить анализ")
    
    print("\n" + "="*60)
    print("✅ Тест завершен")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_live_api())
