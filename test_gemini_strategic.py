"""
Простой тест Strategic Brain с Gemini fallback
"""
import asyncio
import os

# Set environment variables
os.environ['OHMYGPT_KEY'] = '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'
os.environ['STRATEGIC_DRIVER_URL'] = 'https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg'
os.environ['STRATEGIC_MODEL'] = 'claude-3-5-sonnet-20240620'
os.environ['GOOGLE_API_KEY_2'] = 'AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c'
os.environ['GOOGLE_API_KEY_3'] = 'AIzaSyD18h8QwDeSl8U5pFMM1HtoB3VaUksXy-g'

from core.strategic_brain import get_strategic_brain

async def test():
    print("=" * 80)
    print("🧠 STRATEGIC BRAIN TEST - Gemini Fallback")
    print("=" * 80)
    
    brain = get_strategic_brain()
    
    # Тестовые данные - симулируем рост
    daily_candles = [
        {'symbol': 'BTCUSDT', 'open': 90000, 'close': 91000, 'high': 91500, 'low': 89500, 'volume': 1000000},
        {'symbol': 'BTCUSDT', 'open': 91000, 'close': 92000, 'high': 92500, 'low': 90500, 'volume': 1100000},
        {'symbol': 'BTCUSDT', 'open': 92000, 'close': 93000, 'high': 93500, 'low': 91500, 'volume': 1200000},
        {'symbol': 'ETHUSDT', 'open': 3100, 'close': 3150, 'high': 3180, 'low': 3080, 'volume': 500000},
        {'symbol': 'ETHUSDT', 'open': 3150, 'close': 3180, 'high': 3200, 'low': 3130, 'volume': 520000},
        {'symbol': 'ETHUSDT', 'open': 3180, 'close': 3200, 'high': 3220, 'low': 3160, 'volume': 540000},
    ]
    
    news_summary = "Positive sentiment, Bitcoin breaking resistance levels"
    
    print("\n📊 Test Data:")
    print(f"   Candles: {len(daily_candles)}")
    print(f"   News: {news_summary}")
    
    print("\n🎯 Calling Strategic Brain...")
    regime = await brain.get_market_regime(daily_candles, news_summary)
    
    print(f"\n✅ Result: {regime}")
    print(f"   Last Update: {brain.last_update}")
    
    # Test signal filtering
    print("\n🔍 Signal Filtering:")
    print(f"   BUY allowed: {brain.should_allow_signal('BUY', regime)}")
    print(f"   SELL allowed: {brain.should_allow_signal('SELL', regime)}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test())
