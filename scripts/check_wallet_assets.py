"""
Проверка реальных активов в кошельке
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api


async def main():
    api = get_bybit_api()
    
    print("=== РЕАЛЬНЫЕ АКТИВЫ В КОШЕЛЬКЕ ===\n")
    
    # Получаем баланс всех активов
    balances = await api.get_wallet_balance()
    
    if not balances:
        print("❌ Не удалось получить баланс")
        return
    
    total_usdt = 0
    
    for coin, data in balances.items():
        if data['total'] > 0:
            print(f"{coin}:")
            print(f"   Total: {data['total']:.8f}")
            print(f"   Available: {data.get('available', 0):.8f}")
            if 'locked' in data:
                print(f"   Locked: {data['locked']:.8f}")
            
            # Конвертируем в USDT
            if coin == "USDT":
                usdt_value = data['total']
            else:
                # Получаем текущую цену
                ticker = await api.get_ticker(f"{coin}USDT")
                if ticker:
                    current_price = ticker['last_price']
                    usdt_value = data['total'] * current_price
                    print(f"   Current Price: ${current_price:.2f}")
                    print(f"   USDT Value: ${usdt_value:.2f}")
                else:
                    usdt_value = 0
            
            total_usdt += usdt_value
            print()
    
    print("="*60)
    print(f"TOTAL BALANCE (USDT equivalent): ${total_usdt:.2f}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
