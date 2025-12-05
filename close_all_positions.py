"""
Emergency: Close all open positions on Bybit
"""
import asyncio
from core.bybit_api import get_bybit_api

async def close_all():
    api = get_bybit_api()
    
    print("🔍 Getting open positions...")
    positions = await api.get_positions()
    
    if not positions:
        print("✅ No open positions")
        return
    
    print(f"📊 Found {len(positions)} positions:")
    for pos in positions:
        size = float(pos.get('size', 0))
        if size > 0:
            symbol = pos['symbol']
            side = pos['side']
            print(f"   - {symbol} {side} {size}")
    
    confirm = input("\n⚠️  Close ALL positions? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Cancelled")
        return
    
    print("\n🔄 Closing positions...")
    for pos in positions:
        size = float(pos.get('size', 0))
        if size > 0:
            symbol = pos['symbol']
            side = pos['side']  # 'Buy' or 'Sell'
            
            # Закрываем позицию (противоположный ордер)
            close_side = 'Sell' if side == 'Buy' else 'Buy'
            
            try:
                print(f"   Closing {symbol} {side} {size}...")
                result = await api.place_order(
                    symbol=symbol,
                    side=close_side,
                    order_type='Market',
                    qty=size,
                    reduce_only=True  # Важно! Только закрытие позиции
                )
                print(f"   ✅ {symbol} closed: {result.get('orderId')}")
            except Exception as e:
                print(f"   ❌ Error closing {symbol}: {e}")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(close_all())
