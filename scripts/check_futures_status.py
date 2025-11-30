"""
Проверка статуса фьючерсной торговли
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from config import settings

async def main():
    api = get_bybit_api()
    
    print("\n" + "="*80)
    print("📊 FUTURES STATUS CHECK")
    print("="*80 + "\n")
    
    # 1. Конфигурация
    print("⚙️  Конфигурация:")
    print(f"   Trading Mode: {settings.trading_mode}")
    print(f"   Futures Enabled: {settings.futures_enabled}")
    print(f"   Virtual Balance: ${settings.futures_virtual_balance}")
    print(f"   Leverage: {settings.futures_leverage}x")
    print(f"   Margin Mode: {settings.futures_margin_mode}")
    print(f"   Risk per Trade: {settings.futures_risk_per_trade*100}%")
    print(f"   Futures Pairs: {', '.join(settings.futures_pairs)}")
    
    # 2. Проверка API
    print(f"\n🔌 API Connection:")
    print(f"   Base URL: {api.base_url}")
    
    # 3. Проверка баланса
    print(f"\n💰 Wallet Balance:")
    balances = await api.get_wallet_balance()
    if balances:
        for coin, data in balances.items():
            if data['total'] > 0:
                print(f"   {coin}: ${data['total']:.2f} (available: ${data['available']:.2f})")
    else:
        print("   ❌ Не удалось получить баланс")
    
    # 4. Проверка открытых позиций
    print(f"\n📈 Open Futures Positions:")
    for symbol in settings.futures_pairs:
        positions = await api.get_positions(symbol)
        if positions:
            for pos in positions:
                print(f"   {pos['symbol']} {pos['side']}: {pos['size']} @ ${pos['entry_price']:.2f}")
                print(f"      PnL: ${pos['unrealized_pnl']:+.2f} | Leverage: {pos['leverage']}x")
        else:
            print(f"   {symbol}: No open positions")
    
    # 5. Проверка цен
    print(f"\n💹 Current Prices:")
    for symbol in settings.futures_pairs[:3]:  # Первые 3 пары
        ticker = await api.get_ticker(symbol)
        if ticker:
            print(f"   {symbol}: ${ticker['last_price']:,.2f}")
    
    print("\n" + "="*80)
    print("✅ Status check complete!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
