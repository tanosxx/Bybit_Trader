import asyncio
from core.executors.futures_executor import FuturesExecutor

async def check():
    executor = FuturesExecutor()
    positions = await executor.get_open_positions()
    
    print(f'\n📊 ОТКРЫТЫЕ ПОЗИЦИИ: {len(positions)}')
    
    total_unrealized = 0
    active_positions = []
    
    for p in positions:
        size = float(p.get('size', 0))
        if size > 0:  # Только активные
            symbol = p.get('symbol', 'UNKNOWN')
            side = p.get('side', 'UNKNOWN')
            entry = float(p.get('avgPrice', 0))
            pnl = float(p.get('unrealisedPnl', 0))
            leverage = p.get('leverage', 'N/A')
            
            total_unrealized += pnl
            active_positions.append({
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry': entry,
                'pnl': pnl,
                'leverage': leverage
            })
    
    print(f'\n🔥 АКТИВНЫЕ ПОЗИЦИИ: {len(active_positions)}')
    print(f'💸 Total Unrealized PnL: ${total_unrealized:.2f}')
    
    # Топ убыточных
    active_positions.sort(key=lambda x: x['pnl'])
    print(f'\n❌ ТОП-10 УБЫТОЧНЫХ:')
    for p in active_positions[:10]:
        print(f"  {p['side']} {p['symbol']}: {p['size']} @ ${p['entry']:.2f} | PnL: ${p['pnl']:.2f} ({p['leverage']}x)")
    
    # Топ прибыльных
    print(f'\n✅ ТОП-5 ПРИБЫЛЬНЫХ:')
    for p in active_positions[-5:]:
        print(f"  {p['side']} {p['symbol']}: {p['size']} @ ${p['entry']:.2f} | PnL: ${p['pnl']:.2f} ({p['leverage']}x)")

asyncio.run(check())
