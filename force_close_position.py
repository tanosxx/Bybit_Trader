"""
Force close a single position by symbol (no confirmation)
"""
import asyncio
import sys
from core.bybit_api import get_bybit_api

async def close_position(symbol: str):
    api = get_bybit_api()
    
    print(f"🔍 Getting position for {symbol}...")
    positions = await api.get_positions()
    
    target_pos = None
    for pos in positions:
        if pos['symbol'] == symbol:
            size = float(pos.get('size', 0))
            if size > 0:
                target_pos = pos
                break
    
    if not target_pos:
        print(f"❌ No open position found for {symbol}")
        return
    
    side = target_pos['side']
    size = float(target_pos['size'])
    entry_price = float(target_pos.get('avgPrice', 0))
    
    print(f"\n📊 Position found:")
    print(f"   Symbol: {symbol}")
    print(f"   Side: {side}")
    print(f"   Size: {size}")
    print(f"   Entry Price: ${entry_price:.2f}")
    
    # Закрываем позицию (противоположный ордер)
    close_side = 'Sell' if side == 'Buy' else 'Buy'
    
    try:
        print(f"\n🔄 Closing {symbol} {side} {size}...")
        result = await api.place_order(
            symbol=symbol,
            side=close_side,
            order_type='Market',
            qty=size,
            reduce_only=True  # Важно! Только закрытие позиции
        )
        print(f"✅ {symbol} closed successfully!")
        print(f"   Order ID: {result.get('orderId')}")
    except Exception as e:
        print(f"❌ Error closing {symbol}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python force_close_position.py SYMBOL")
        print("Example: python force_close_position.py BNBUSDT")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    asyncio.run(close_position(symbol))
