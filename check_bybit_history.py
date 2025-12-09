"""
Проверка истории сделок напрямую с Bybit API
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from datetime import datetime

async def main():
    print("=" * 80)
    print("🌐 ПРОВЕРКА ИСТОРИИ СДЕЛОК НА BYBIT")
    print("=" * 80)
    
    api = get_bybit_api()
    
    # 1. Баланс
    print("\n💰 ТЕКУЩИЙ БАЛАНС:")
    balances = await api.get_wallet_balance()
    if balances:
        for coin, data in balances.items():
            if data['total'] > 0:
                print(f"   {coin}: ${data['total']:.2f} (Available: ${data['available']:.2f})")
    
    # 2. Открытые позиции
    print("\n📂 ОТКРЫТЫЕ ПОЗИЦИИ:")
    positions = await api.get_positions()
    if positions:
        for pos in positions:
            print(f"   {pos['symbol']} {pos['side']} | Size: {pos['size']} | Entry: ${pos['entry_price']:.2f} | PnL: ${pos['unrealized_pnl']:.2f}")
    else:
        print("   Нет открытых позиций")
    
    # 3. История закрытых позиций (Futures)
    print("\n📜 ИСТОРИЯ ЗАКРЫТЫХ ПОЗИЦИЙ (FUTURES):")
    print("   Получаем данные с Bybit API...")
    
    try:
        pnl_history = await api.get_closed_pnl_history(limit=100)
        
        if pnl_history:
            print(f"   Найдено записей: {len(pnl_history)}")
            
            total_pnl = 0
            for i, record in enumerate(pnl_history[:20], 1):  # Первые 20
                pnl = float(record.get("closedPnl", 0))
                total_pnl += pnl
                qty = float(record.get("qty", 0))
                symbol = record.get("symbol", "")
                side = record.get("side", "")
                updated_time = int(record.get("updatedTime", 0)) / 1000
                close_time = datetime.fromtimestamp(updated_time) if updated_time > 0 else "N/A"
                
                print(f"   {i}. {symbol} {side} | Qty: {qty} | PnL: ${pnl:.2f} | Time: {close_time}")
            
            print(f"\n   Total PnL (первые 20): ${total_pnl:.2f}")
            
            # Считаем общий PnL
            total_all = sum(float(r.get("closedPnl", 0)) for r in pnl_history)
            print(f"   Total PnL (все {len(pnl_history)}): ${total_all:.2f}")
        else:
            print("   ❌ Нет данных о закрытых позициях")
            print("   Возможно, это Demo аккаунт без истории futures")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. История исполненных ордеров (Spot)
    print("\n📜 ИСТОРИЯ ИСПОЛНЕННЫХ ОРДЕРОВ (SPOT):")
    try:
        trades = await api.get_trade_history(limit=20)
        
        if trades:
            print(f"   Найдено записей: {len(trades)}")
            
            for i, trade in enumerate(trades[:10], 1):  # Первые 10
                symbol = trade.get("symbol", "")
                side = trade.get("side", "")
                qty = float(trade.get("execQty", 0))
                price = float(trade.get("execPrice", 0))
                fee = float(trade.get("execFee", 0))
                exec_time = int(trade.get("execTime", 0)) / 1000
                time_str = datetime.fromtimestamp(exec_time) if exec_time > 0 else "N/A"
                
                print(f"   {i}. {symbol} {side} | Qty: {qty} | Price: ${price:.2f} | Fee: ${fee:.4f} | Time: {time_str}")
        else:
            print("   Нет данных об исполненных ордерах")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 80)
    
    print("\n💡 ВЫВОДЫ:")
    print("   1. Если баланс $135k - это НЕ наш стартовый $100")
    print("   2. Возможно, это Demo аккаунт с предзагруженным балансом")
    print("   3. Или это другой аккаунт (проверь API ключи)")
    print("   4. Наши сделки в БД могут быть виртуальными (не отправлялись на биржу)")

if __name__ == "__main__":
    asyncio.run(main())
