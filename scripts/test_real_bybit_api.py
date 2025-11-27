"""
Тест реального Bybit API
"""
import asyncio
import sys
sys.path.append('/app')

from core.bybit_api import get_bybit_api


async def test_api():
    """Тест Bybit API"""
    api = get_bybit_api()
    
    print(f"\n🔧 Bybit API Test")
    print(f"Base URL: {api.base_url}")
    print(f"API Key: {api.api_key[:10]}...")
    print("="*80)
    
    # Тест 1: Получить баланс
    print("\n1️⃣ Тест: Получить баланс кошелька")
    balances = await api.get_wallet_balance()
    
    if balances:
        print("✅ Баланс получен:")
        for coin, balance in balances.items():
            if balance['total'] > 0:
                print(f"   {coin}: {balance['total']:.4f} (доступно: {balance['available']:.4f})")
    else:
        print("❌ Не удалось получить баланс")
    
    # Тест 2: Получить цену
    print("\n2️⃣ Тест: Получить текущую цену BTC")
    ticker = await api.get_ticker("BTCUSDT")
    
    if ticker:
        print(f"✅ Цена BTC: ${ticker['last_price']:.2f}")
        print(f"   Объем 24ч: {ticker['volume_24h']:.2f}")
        print(f"   Изменение 24ч: {ticker['price_change_24h']:+.2f}%")
    else:
        print("❌ Не удалось получить цену")
    
    # Тест 3: Получить открытые ордера
    print("\n3️⃣ Тест: Получить открытые ордера")
    orders = await api.get_open_orders()
    
    if orders is not None:
        print(f"✅ Открытых ордеров: {len(orders)}")
        for order in orders[:5]:
            print(f"   {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ ${order.get('price')}")
    else:
        print("❌ Не удалось получить ордера")
    
    print("\n" + "="*80)
    print("✅ Тест завершен!")


if __name__ == "__main__":
    asyncio.run(test_api())
