"""
Получение истории транзакций с Bybit
Находим начальное пополнение и рассчитываем реальный начальный баланс
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api
from datetime import datetime


async def get_all_transactions():
    """Получить ВСЕ транзакции через пагинацию с cursor"""
    api = get_bybit_api()
    
    all_transactions = []
    cursor = None
    page = 1
    max_pages = 20  # Максимум 20 страниц (2000 транзакций)
    
    try:
        print("📄 Загружаю транзакции...\n")
        
        while page <= max_pages:
            endpoint = "/v5/account/transaction-log"
            params = {
                "accountType": "UNIFIED",
                "limit": 100
            }
            
            if cursor:
                params['cursor'] = cursor
            
            result = await api._request("GET", endpoint, params)
            
            if not result or 'result' not in result:
                print(f"⚠️  Нет ответа от API на странице {page}")
                break
            
            transactions = result['result'].get('list', [])
            if not transactions:
                print(f"⚪ Страница {page}: нет транзакций")
                break
            
            all_transactions.extend(transactions)
            print(f"✅ Страница {page}: получено {len(transactions)} транзакций (всего: {len(all_transactions)})")
            
            # Проверяем cursor для следующей страницы
            next_cursor = result['result'].get('nextPageCursor')
            if not next_cursor or next_cursor == cursor:
                print(f"⚪ Достигнут конец истории")
                break
            
            cursor = next_cursor
            page += 1
            await asyncio.sleep(0.2)
        
        print(f"\n✅ Всего загружено транзакций: {len(all_transactions)}\n")
        return all_transactions
    
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
        import traceback
        traceback.print_exc()
        return all_transactions


async def calculate_initial_balance():
    """Рассчитать начальный баланс из истории транзакций"""
    api = get_bybit_api()
    
    print("=== ПОЛУЧЕНИЕ ИСТОРИИ ТРАНЗАКЦИЙ ===\n")
    
    transactions = await get_all_transactions()
    
    if not transactions:
        print("❌ Не удалось получить транзакции\n")
        return None
    
    # Сортируем по времени (самые старые первые)
    transactions.sort(key=lambda x: x.get('transactionTime', 0))
    
    print("=== ПЕРВЫЕ 20 ТРАНЗАКЦИЙ (САМЫЕ СТАРЫЕ) ===\n")
    
    initial_deposits = {}
    
    for i, tx in enumerate(transactions[:20], 1):
        tx_type = tx.get('type', 'N/A')
        coin = tx.get('coin', 'N/A')
        change = float(tx.get('change', 0))
        amount = float(tx.get('amount', 0))
        timestamp = tx.get('transactionTime', 0)
        
        # Конвертируем timestamp в дату
        if timestamp:
            try:
                timestamp_int = int(timestamp)
                dt = datetime.fromtimestamp(timestamp_int / 1000)
                date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = str(timestamp)
        else:
            date_str = 'N/A'
        
        print(f"{i}. {date_str}")
        print(f"   Type: {tx_type}")
        print(f"   Coin: {coin}")
        print(f"   Change: {change:+.8f}")
        print(f"   Amount: {amount:.8f}")
        
        # Если это пополнение (Transfer с положительным change)
        if tx_type == 'TRANSFER' and change > 0:
            print(f"   💰 ПОПОЛНЕНИЕ (TRANSFER)!")
            if coin not in initial_deposits:
                initial_deposits[coin] = 0
            initial_deposits[coin] += change
        elif change > 0 and tx_type not in ['TRADE', 'FEE']:
            print(f"   💰 ПОПОЛНЕНИЕ ({tx_type})!")
            if coin not in initial_deposits:
                initial_deposits[coin] = 0
            initial_deposits[coin] += change
        
        print()
    
    if initial_deposits:
        print("="*60)
        print("💰 НАЙДЕННЫЕ ПОПОЛНЕНИЯ (НАЧАЛЬНЫЙ БАЛАНС):")
        print("="*60)
        
        total_usdt_value = 0
        
        for coin, amount in initial_deposits.items():
            print(f"\n{coin}: {amount:.8f}")
            
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
            total_usdt_value += usdt_value
        
        print("\n" + "="*60)
        print(f"🎯 НАЧАЛЬНЫЙ БАЛАНС (USDT): ${total_usdt_value:.2f}")
        print("="*60)
        
        return {
            'initial_deposits': initial_deposits,
            'initial_balance_usdt': total_usdt_value
        }
    
    else:
        print("⚠️  Пополнения не найдены в первых 20 транзакциях")
        print("   Показываю больше...\n")
        
        # Альтернатива: смотрим текущий баланс и вычитаем PnL
        balances = await api.get_wallet_balance()
        
        if balances:
            print("=== ТЕКУЩИЙ БАЛАНС ===\n")
            
            total_usdt = 0
            deposits = {}
            
            for coin, data in balances.items():
                current = float(data['total'])
                
                if current > 0:
                    # Конвертируем в USDT
                    if coin == 'USDT':
                        usdt_value = current
                        price = 1.0
                    elif coin == 'USDC':
                        usdt_value = current * 0.9999
                        price = 0.9999
                    else:
                        try:
                            ticker = await api.get_ticker(f"{coin}USDT")
                            if ticker:
                                price_field = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
                                price = float(price_field) if price_field else 0
                                usdt_value = current * price
                            else:
                                price = 0
                                usdt_value = 0
                        except:
                            price = 0
                            usdt_value = 0
                    
                    total_usdt += usdt_value
                    deposits[coin] = {'amount': current, 'price': price, 'usdt_value': usdt_value}
                    
                    print(f"{coin}:")
                    print(f"   Amount: {current:.8f}")
                    if price > 0:
                        print(f"   Price: ${price:.2f}")
                    print(f"   USDT Value: ${usdt_value:.2f}")
                    print()
            
            print("="*60)
            print(f"TOTAL CURRENT BALANCE: ${total_usdt:.2f}")
            print("="*60)
            
            # Получаем PnL из БД
            from database.db import async_session
            from database.models import Trade, TradeStatus
            from sqlalchemy import select, func
            
            async with async_session() as session:
                result = await session.execute(
                    select(func.sum(Trade.pnl)).where(Trade.status == TradeStatus.CLOSED)
                )
                total_pnl = result.scalar() or 0
            
            print(f"\nTotal PnL from closed trades: ${total_pnl:+.2f}")
            
            # Начальный баланс = Текущий - PnL
            # НО это не точно, так как не учитывает комиссии и slippage
            estimated_initial = total_usdt - total_pnl
            
            print(f"\n💡 ESTIMATED Initial Balance: ${estimated_initial:.2f}")
            print(f"   (Current ${total_usdt:.2f} - PnL ${total_pnl:+.2f})")
            
            return {
                'current_balance': total_usdt,
                'total_pnl': total_pnl,
                'estimated_initial': estimated_initial,
                'deposits': deposits
            }
    



if __name__ == "__main__":
    asyncio.run(calculate_initial_balance())
