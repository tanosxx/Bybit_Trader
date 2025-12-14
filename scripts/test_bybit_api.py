"""
Тест Bybit API
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.bybit_api import get_bybit_api


async def main():
    """Тест API"""
    api = get_bybit_api()
    
    print("🔧 Testing Bybit API...")
    print("="*80)
    
    # 1. Тест получения свечей
    print("\n📊 Testing get_klines (BTCUSDT)...")
    candles = await api.get_klines("BTCUSDT", "1", limit=10)
    
    if candles:
        print(f"✅ Got {len(candles)} candles")
        print(f"   Latest: ${candles[0]['close']:.2f}")
    else:
        print("❌ Failed to get candles")
    
    # 2. Тест получения тикера
    print("\n💰 Testing get_ticker (BTCUSDT)...")
    ticker = await api.get_ticker("BTCUSDT")
    
    if ticker:
        print(f"✅ Ticker data:")
        print(f"   Price: ${ticker['last_price']:.2f}")
        print(f"   Volume 24h: ${ticker['volume_24h']:.2f}")
        print(f"   Change 24h: {ticker['price_change_24h']:+.2f}%")
    else:
        print("❌ Failed to get ticker")
    
    # 3. Тест получения баланса
    print("\n💵 Testing get_wallet_balance...")
    balance = await api.get_wallet_balance()
    
    if balance:
        print(f"✅ Wallet balance:")
        for coin, data in balance.items():
            if data['total'] > 0:
                print(f"   {coin}: ${data['total']:.2f} (available: ${data['available']:.2f})")
    else:
        print("❌ Failed to get balance")
    
    print("\n" + "="*80)
    print("✅ API test completed!")


if __name__ == "__main__":
    asyncio.run(main())
