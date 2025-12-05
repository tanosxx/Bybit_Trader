"""
Тест Strategic Brain - проверка работы Claude 3.5 Sonnet
"""
import asyncio
import os
from datetime import datetime, timedelta

# Установим переменные окружения для теста
os.environ['OHMYGPT_KEY'] = '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'
os.environ['STRATEGIC_DRIVER_URL'] = 'https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/'
os.environ['STRATEGIC_MODEL'] = 'claude-3-5-sonnet-20240620'

from core.strategic_brain import get_strategic_brain, REGIME_BULL_RUSH, REGIME_BEAR_CRASH, REGIME_SIDEWAYS, REGIME_UNCERTAIN


async def test_strategic_brain():
    """Тестируем Strategic Brain с реальными данными"""
    
    print("=" * 80)
    print("🧠 TESTING STRATEGIC BRAIN")
    print("=" * 80)
    
    brain = get_strategic_brain()
    
    # Проверка инициализации
    print(f"\n✅ Strategic Brain initialized")
    print(f"   API Key: {brain.api_key[:20]}...")
    print(f"   Base URL: {brain.base_url}")
    print(f"   Model: {brain.model}")
    print(f"   Current Regime: {brain.current_regime}")
    
    # Тестовые данные - симулируем бычий рынок
    print("\n" + "=" * 80)
    print("📊 TEST 1: BULL MARKET (BTC +5%, ETH +4%)")
    print("=" * 80)
    
    bull_candles = [
        {'symbol': 'BTCUSDT', 'open': 90000, 'close': 94500, 'high': 95000, 'low': 89500, 'volume': 1000000},
        {'symbol': 'BTCUSDT', 'open': 94500, 'close': 96000, 'high': 96500, 'low': 94000, 'volume': 1100000},
        {'symbol': 'ETHUSDT', 'open': 3000, 'close': 3120, 'high': 3150, 'low': 2980, 'volume': 500000},
        {'symbol': 'ETHUSDT', 'open': 3120, 'close': 3200, 'high': 3220, 'low': 3100, 'volume': 520000},
    ]
    
    bull_news = "Bitcoin surges past $95k as institutional adoption accelerates. Positive sentiment across crypto markets."
    
    regime = await brain.get_market_regime(bull_candles, bull_news)
    print(f"\n✅ Detected Regime: {regime}")
    
    # Проверка фильтрации
    print("\n🔍 Testing Signal Filtering:")
    print(f"   BUY signal allowed: {brain.should_allow_signal('BUY', regime)}")
    print(f"   SELL signal allowed: {brain.should_allow_signal('SELL', regime)}")
    
    # Тестовые данные - симулируем медвежий рынок
    print("\n" + "=" * 80)
    print("📊 TEST 2: BEAR MARKET (BTC -6%, ETH -5%)")
    print("=" * 80)
    
    bear_candles = [
        {'symbol': 'BTCUSDT', 'open': 95000, 'close': 89300, 'high': 95500, 'low': 88000, 'volume': 1200000},
        {'symbol': 'BTCUSDT', 'open': 89300, 'close': 87000, 'high': 90000, 'low': 86500, 'volume': 1300000},
        {'symbol': 'ETHUSDT', 'open': 3200, 'close': 3040, 'high': 3220, 'low': 3000, 'volume': 600000},
        {'symbol': 'ETHUSDT', 'open': 3040, 'close': 2950, 'high': 3060, 'low': 2920, 'volume': 620000},
    ]
    
    bear_news = "Crypto markets plunge as regulatory concerns mount. Fear dominates sentiment."
    
    # Сбросим кэш для нового теста
    brain.last_update = None
    
    regime = await brain.get_market_regime(bear_candles, bear_news)
    print(f"\n✅ Detected Regime: {regime}")
    
    # Проверка фильтрации
    print("\n🔍 Testing Signal Filtering:")
    print(f"   BUY signal allowed: {brain.should_allow_signal('BUY', regime)}")
    print(f"   SELL signal allowed: {brain.should_allow_signal('SELL', regime)}")
    
    # Тестовые данные - симулируем боковик
    print("\n" + "=" * 80)
    print("📊 TEST 3: SIDEWAYS MARKET (BTC ±1%, ETH ±0.5%)")
    print("=" * 80)
    
    sideways_candles = [
        {'symbol': 'BTCUSDT', 'open': 92000, 'close': 92500, 'high': 93000, 'low': 91500, 'volume': 800000},
        {'symbol': 'BTCUSDT', 'open': 92500, 'close': 92200, 'high': 93200, 'low': 91800, 'volume': 820000},
        {'symbol': 'ETHUSDT', 'open': 3100, 'close': 3110, 'high': 3130, 'low': 3080, 'volume': 400000},
        {'symbol': 'ETHUSDT', 'open': 3110, 'close': 3105, 'high': 3125, 'low': 3090, 'volume': 410000},
    ]
    
    sideways_news = "Crypto markets consolidate as traders await direction. Neutral sentiment prevails."
    
    # Сбросим кэш для нового теста
    brain.last_update = None
    
    regime = await brain.get_market_regime(sideways_candles, sideways_news)
    print(f"\n✅ Detected Regime: {regime}")
    
    # Проверка фильтрации
    print("\n🔍 Testing Signal Filtering:")
    print(f"   BUY signal allowed: {brain.should_allow_signal('BUY', regime)}")
    print(f"   SELL signal allowed: {brain.should_allow_signal('SELL', regime)}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_strategic_brain())
