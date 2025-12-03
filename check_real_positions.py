import asyncio
from core.bybit_api import get_bybit_api

async def check():
    api = get_bybit_api()
    
    # Получаем позиции с биржи
    positions = await api.get_positions()
    
    print(f'\n📊 ПОЗИЦИИ НА BYBIT: {len(positions)}')
    
    total_unrealized = 0
    
    for p in positions:
        symbol = p.get('symbol', 'UNKNOWN')
        side = p.get('side', 'UNKNOWN')
        size = float(p.get('size', 0))
        entry = float(p.get('avgPrice', 0))
        mark_price = float(p.get('markPrice', 0))
        unrealized_pnl = float(p.get('unrealisedPnl', 0))
        leverage = p.get('leverage', 'N/A')
        
        if size > 0:
            total_unrealized += unrealized_pnl
            print(f'\n{side} {symbol}:')
            print(f'  Size: {size}')
            print(f'  Entry: ${entry:.2f}')
            print(f'  Mark: ${mark_price:.2f}')
            print(f'  Unrealized PnL: ${unrealized_pnl:.2f}')
            print(f'  Leverage: {leverage}x')
    
    print(f'\n💸 TOTAL UNREALIZED PNL: ${total_unrealized:.2f}')
    
    # Получаем баланс
    wallet = await api.get_wallet_balance()
    if wallet:
        usdt = wallet.get('USDT', {})
        total = float(usdt.get('total', 0))
        available = float(usdt.get('available', 0))
        print(f'\n💰 USDT BALANCE:')
        print(f'  Total: ${total:.2f}')
        print(f'  Available: ${available:.2f}')

asyncio.run(check())
