"""
EMERGENCY: Закрыть ВСЕ открытые позиции на Bybit
"""
import asyncio
from core.bybit_api import get_bybit_api

async def close_all():
    api = get_bybit_api()
    
    print("\n🚨 EMERGENCY: Закрываю все позиции...")
    
    # Получаем все позиции
    positions = await api.get_positions()
    
    closed_count = 0
    
    for p in positions:
        symbol = p.get('symbol')
        side = p.get('side')
        size = float(p.get('size', 0))
        
        if size > 0:
            print(f"\n📉 Закрываю {side} {symbol} (size: {size})")
            
            try:
                # Определяем сторону закрытия (противоположную)
                close_side = 'Sell' if side == 'Buy' else 'Buy'
                
                # Закрываем позицию
                result = await api.place_order(
                    category='linear',
                    symbol=symbol,
                    side=close_side,
                    order_type='Market',
                    qty=str(size),
                    reduce_only=True
                )
                
                if result:
                    print(f"✅ Закрыто: {symbol}")
                    closed_count += 1
                else:
                    print(f"❌ Ошибка закрытия: {symbol}")
                    
            except Exception as e:
                print(f"❌ Исключение при закрытии {symbol}: {e}")
    
    print(f"\n✅ Закрыто позиций: {closed_count}")
    
    # Проверяем что осталось
    positions_after = await api.get_positions()
    active_after = sum(1 for p in positions_after if float(p.get('size', 0)) > 0)
    
    print(f"📊 Активных позиций после закрытия: {active_after}")

asyncio.run(close_all())
