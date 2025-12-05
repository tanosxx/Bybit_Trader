"""
Test Strategic Brain with live data from Bybit API
"""
import asyncio
import os
from pybit.unified_trading import HTTP

# Set environment variables
os.environ['OHMYGPT_KEY'] = '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'
os.environ['STRATEGIC_DRIVER_URL'] = 'https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg'
os.environ['STRATEGIC_MODEL'] = 'claude-3-5-sonnet-20240620'
os.environ['GOOGLE_API_KEY_2'] = 'AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c'
os.environ['GOOGLE_API_KEY_3'] = 'AIzaSyD18h8QwDeSl8U5pFMM1HtoB3VaUksXy-g'

from core.strategic_brain import get_strategic_brain

async def test_strategic_brain():
    """Test Strategic Brain with real market data"""
    print("=" * 80)
    print("🧠 STRATEGIC BRAIN LIVE TEST")
    print("=" * 80)
    
    # Initialize Bybit client (demo)
    client = HTTP(
        testnet=False,
        api_key="BKysZSt2fa5KmR2IIz",
        api_secret="cV649E7ymmp1L6xkLNlLNjDmkpvCIsQLkkHu",
        demo=True
    )
    
    # Get daily candles for BTC and ETH
    print("\n📊 Fetching daily candles...")
    daily_candles = []
    
    for symbol in ['BTCUSDT', 'ETHUSDT']:
        try:
            print(f"   Fetching {symbol}...")
            response = client.get_kline(
                category="linear",
                symbol=symbol,
                interval="D",
                limit=7
            )
            
            if response['retCode'] == 0:
                candles = response['result']['list']
                print(f"   ✅ Got {len(candles)} candles for {symbol}")
                
                for candle in candles:
                    daily_candles.append({
                        'symbol': symbol,
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
            else:
                print(f"   ❌ API Error: {response['retMsg']}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    if not daily_candles:
        print("\n❌ No daily candles available, cannot test Strategic Brain")
        return
    
    print(f"\n✅ Total candles collected: {len(daily_candles)}")
    print("\n📊 Sample data:")
    for candle in daily_candles[:3]:
        print(f"   {candle['symbol']}: ${candle['close']:.2f} (Vol: {candle['volume']:.0f})")
    
    # Initialize Strategic Brain
    print("\n🧠 Initializing Strategic Brain...")
    brain = get_strategic_brain()
    
    # Test regime detection
    print("\n🎯 Testing Market Regime Detection...")
    news_summary = "Mixed sentiment, moderate trading volume"
    
    regime = await brain.get_market_regime(
        daily_candles=daily_candles,
        news_summary=news_summary
    )
    
    print(f"\n✅ Market Regime: {regime}")
    print(f"   Last Update: {brain.last_update}")
    
    # Test signal filtering
    print("\n🔍 Testing Signal Filtering:")
    print(f"   BUY signal allowed: {brain.should_allow_signal('BUY', regime)}")
    print(f"   SELL signal allowed: {brain.should_allow_signal('SELL', regime)}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_strategic_brain())
