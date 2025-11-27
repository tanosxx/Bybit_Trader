"""Проверка реальных данных с API"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.real_trader import RealTrader

async def main():
    trader = RealTrader()
    
    print("=== БАЛАНС ===")
    balance = await trader.get_balance()
    print(balance)
    
    print("\n=== ОТКРЫТЫЕ ПОЗИЦИИ ===")
    positions = await trader.get_open_positions()
    print(positions)
    
    print("\n=== ИСТОРИЯ ОРДЕРОВ (последние 10) ===")
    # Получим историю через API
    try:
        from pybit.unified_trading import HTTP
        from config import settings
        
        session = HTTP(
            testnet=settings.BYBIT_TESTNET,
            api_key=settings.BYBIT_API_KEY,
            api_secret=settings.BYBIT_API_SECRET
        )
        
        orders = session.get_order_history(
            category="spot",
            limit=10
        )
        print(orders)
    except Exception as e:
        print(f"Ошибка получения истории: {e}")

if __name__ == "__main__":
    asyncio.run(main())
