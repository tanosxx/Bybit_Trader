"""
Тест гибридного AI Brain
"""
import sys
sys.path.append('.')

import asyncio
from core.ai_brain_hybrid import get_ai_brain_hybrid


async def test_hybrid():
    """Тест гибридной логики"""
    
    print("="*60)
    print("🧪 Тест Гибридного AI Brain (ML-First)")
    print("="*60)
    
    # Тестовые данные
    test_data = {
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
            "lower": 93500.0
        },
        "stochastic": {
            "k": 62.3,
            "d": 58.1
        },
        "trend": "uptrend",
        "volume_trend": "increasing"
    }
    
    ai = get_ai_brain_hybrid()
    
    # Тест 1: Первый запрос
    print(f"\n📊 Тест 1: Первый анализ")
    result1 = await ai.analyze_market(test_data)
    
    if result1:
        print(f"\n✅ Результат:")
        print(f"   Решение: {result1['decision']}")
        print(f"   Уверенность: {result1['confidence']:.0%}")
        print(f"   Источник: {result1.get('source', 'UNKNOWN')}")
        print(f"   Обоснование: {result1.get('reasoning', 'N/A')}")
    else:
        print(f"\n❌ Анализ не удался")
    
    # Тест 2: Повторный запрос (должен использовать кэш)
    print(f"\n📊 Тест 2: Повторный анализ (кэш)")
    result2 = await ai.analyze_market(test_data)
    
    if result2:
        print(f"✅ Результат из кэша")
    
    # Тест 3: Изменение цены на 0.05% (должен использовать кэш)
    print(f"\n📊 Тест 3: Цена изменилась на 0.05%")
    test_data['price'] = 95280.0  # +0.05%
    result3 = await ai.analyze_market(test_data)
    
    # Тест 4: Изменение цены на 0.2% (новый анализ)
    print(f"\n📊 Тест 4: Цена изменилась на 0.2%")
    test_data['price'] = 95430.0  # +0.2%
    result4 = await ai.analyze_market(test_data)
    
    # Статистика
    ai.print_stats()
    
    print("\n" + "="*60)
    print("✅ Тест завершен")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_hybrid())
