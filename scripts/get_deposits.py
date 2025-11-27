"""
Получение истории депозитов/пополнений с Bybit
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api
from datetime import datetime, timedelta


async def get_deposit_history():
    """Получить историю депозитов"""
    api = get_bybit_api()
    
    print("=== ИСТОРИЯ ДЕПОЗИТОВ ===\n")
    
    try:
        # V5 API: /v5/asset/deposit/query-record
        endpoint = "/v5/asset/deposit/query-record"
        
        # Пробуем без параметров (все депозиты)
        result = await api._request("GET", endpoint, {})
        
        if result and 'result' in result:
            deposits = result['result'].get('rows', [])
            
            if deposits:
                print(f"✅ Найдено депозитов: {len(deposits)}\n")
                
                total_usdt = 0
                
                for i, dep in enumerate(deposits, 1):
                    coin = dep.get('coin', 'N/A')
                    amount = float(dep.get('amount', 0))
                    status = dep.get('status', 'N/A')
                    timestamp = dep.get('successAt', 0)
                    
                    if timestamp:
                        try:
                            dt = datetime.fromtimestamp(int(timestamp) / 1000)
                            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            date_str = str(timestamp)
                    else:
                        date_str = 'N/A'
                    
                    print(f"{i}. {date_str}")
                    print(f"   Coin: {coin}")
                    print(f"   Amount: {amount:.8f}")
                    print(f"   Status: {status}")
                    
                    # Конвертируем в USDT
                    if coin == 'USDT':
                        usdt_value = amount
                    elif coin == 'USDC':
                        usdt_value = amount * 0.9999
                    else:
                        try:
                            ticker = await api.get_ticker(f"{coin}USDT")
                            if ticker:
                                price_field = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
                                price = float(price_field) if price_field else 0
                                usdt_value = amount * price
                                print(f"   Current Price: ${price:.2f}")
                            else:
                                usdt_value = 0
                        except:
                            usdt_value = 0
                    
                    print(f"   USDT Value: ${usdt_value:.2f}")
                    total_usdt += usdt_value
                    print()
                
                print("="*60)
                print(f"💰 НАЧАЛЬНЫЙ БАЛАНС (сумма депозитов): ${total_usdt:.2f}")
                print("="*60)
                
                return total_usdt
            else:
                print("⚠️  Депозиты не найдены")
                return None
        else:
            print(f"❌ Ошибка API: {result}")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(get_deposit_history())
