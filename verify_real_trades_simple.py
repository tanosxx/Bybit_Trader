"""
Простая проверка реальных сделок на Bybit Demo
Сверяет данные из БД с реальными позициями на бирже
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Trade
from sqlalchemy import select, func

async def main():
    print("=" * 80)
    print("🔍 ПРОВЕРКА РЕАЛЬНЫХ СДЕЛОК НА BYBIT DEMO")
    print("=" * 80)
    
    # 1. Статистика из БД
    print("\n📊 ДАННЫЕ ИЗ БАЗЫ ДАННЫХ:")
    async with async_session() as session:
        # Всего сделок
        result = await session.execute(
            select(func.count(Trade.id)).where(Trade.market_type == 'futures')
        )
        total_trades = result.scalar()
        
        # Открытые
        result = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.market_type == 'futures',
                Trade.status == 'OPEN'
            )
        )
        open_trades = result.scalar()
        
        # Закрытые
        result = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.market_type == 'futures',
                Trade.status == 'CLOSED'
            )
        )
        closed_trades = result.scalar()
        
        # Total PnL
        result = await session.execute(
            select(func.sum(Trade.pnl)).where(
                Trade.market_type == 'futures',
                Trade.status == 'CLOSED'
            )
        )
        total_pnl = result.scalar() or 0
        
        # Total Fees
        result = await session.execute(
            select(func.sum(Trade.fee_entry + Trade.fee_exit)).where(
                Trade.market_type == 'futures',
                Trade.status == 'CLOSED'
            )
        )
        total_fees = result.scalar() or 0
        
        print(f"   Всего сделок: {total_trades}")
        print(f"   Открытых: {open_trades}")
        print(f"   Закрытых: {closed_trades}")
        print(f"   Total PnL: ${total_pnl:.2f}")
        print(f"   Total Fees: ${total_fees:.2f}")
        print(f"   Net Profit: ${total_pnl - total_fees:.2f}")
        
        # 2. Открытые позиции в БД
        print("\n📂 ОТКРЫТЫЕ ПОЗИЦИИ В БД:")
        result = await session.execute(
            select(Trade).where(
                Trade.market_type == 'futures',
                Trade.status == 'OPEN'
            ).order_by(Trade.entry_time.desc())
        )
        db_open = result.scalars().all()
        
        if db_open:
            for pos in db_open:
                print(f"   {pos.symbol} {pos.side} | Qty: {pos.quantity} | Entry: ${pos.entry_price} | Time: {pos.entry_time}")
        else:
            print("   ✅ Нет открытых позиций")
        
        # 3. Реальные позиции на Bybit
        print("\n🌐 РЕАЛЬНЫЕ ПОЗИЦИИ НА BYBIT:")
        api = get_bybit_api()
        bybit_positions = await api.get_positions()
        
        if bybit_positions:
            for pos in bybit_positions:
                print(f"   {pos['symbol']} {pos['side']} | Size: {pos['size']} | Entry: ${pos['entry_price']:.2f} | Unrealized PnL: ${pos['unrealized_pnl']:.2f}")
        else:
            print("   ✅ Нет открытых позиций")
        
        # 4. Сверка открытых позиций
        print("\n🔄 СВЕРКА ОТКРЫТЫХ ПОЗИЦИЙ:")
        if len(db_open) == len(bybit_positions):
            print(f"   ✅ Количество совпадает: {len(db_open)} позиций")
            
            if len(db_open) == 0:
                print("   ✅ Обе системы показывают 0 открытых позиций - идеально!")
            else:
                # Проверяем каждую позицию
                db_symbols = {pos.symbol: pos for pos in db_open}
                bybit_symbols = {pos['symbol']: pos for pos in bybit_positions}
                
                for symbol in db_symbols:
                    if symbol in bybit_symbols:
                        db_pos = db_symbols[symbol]
                        bybit_pos = bybit_symbols[symbol]
                        
                        qty_match = abs(db_pos.quantity - bybit_pos['size']) < 0.01
                        side_match = db_pos.side == bybit_pos['side']
                        
                        if qty_match and side_match:
                            print(f"   ✅ {symbol}: Полное совпадение")
                        else:
                            print(f"   ⚠️ {symbol}: Расхождение!")
                            print(f"      БД: {db_pos.side} {db_pos.quantity}")
                            print(f"      Bybit: {bybit_pos['side']} {bybit_pos['size']}")
                    else:
                        print(f"   ❌ {symbol}: Есть в БД, но НЕТ на Bybit (фантомная позиция!)")
                
                for symbol in bybit_symbols:
                    if symbol not in db_symbols:
                        print(f"   ⚠️ {symbol}: Есть на Bybit, но НЕТ в БД")
        else:
            print(f"   ❌ Расхождение количества: БД={len(db_open)}, Bybit={len(bybit_positions)}")
            if len(db_open) > 0:
                print(f"   ⚠️ В БД есть {len(db_open)} открытых позиций, но на Bybit их {len(bybit_positions)}")
                print(f"   ⚠️ Возможно фантомные позиции!")
        
        # 5. Реальный баланс на Bybit
        print("\n💰 РЕАЛЬНЫЙ БАЛАНС НА BYBIT:")
        balances = await api.get_wallet_balance()
        
        if balances and "USDT" in balances:
            wallet = balances["USDT"]
            print(f"   Total Equity: ${wallet['total']:.2f}")
            print(f"   Available: ${wallet['available']:.2f}")
            print(f"   Used in Positions: ${wallet['total'] - wallet['available']:.2f}")
            
            # Сравнение с БД
            db_balance = 100.0 + total_pnl - total_fees
            diff = wallet['total'] - db_balance
            print(f"\n   📊 Сравнение с БД:")
            print(f"      БД Balance: ${db_balance:.2f}")
            print(f"      Bybit Balance: ${wallet['total']:.2f}")
            print(f"      Разница: ${diff:.2f}")
            
            if abs(diff) < 1.0:
                print(f"      ✅ Балансы совпадают (разница < $1)")
            elif abs(diff) < 5.0:
                print(f"      ⚠️ Небольшое расхождение (< $5) - возможно комиссии или открытые позиции")
            else:
                print(f"      ❌ Значительное расхождение! Нужна проверка")
        
        # 6. Последние закрытые сделки из БД
        print("\n📂 ПОСЛЕДНИЕ ЗАКРЫТЫЕ СДЕЛКИ В БД (последние 10):")
        result = await session.execute(
            select(Trade).where(
                Trade.market_type == 'futures',
                Trade.status == 'CLOSED'
            ).order_by(Trade.exit_time.desc()).limit(10)
        )
        db_closed = result.scalars().all()
        
        for trade in db_closed:
            print(f"   {trade.symbol} {trade.side} | Qty: {trade.quantity} | PnL: ${trade.pnl:.2f} | Exit: {trade.exit_time}")
    
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 80)
    
    # Итоговый вердикт
    print("\n🎯 ИТОГОВЫЙ ВЕРДИКТ:")
    if len(db_open) == len(bybit_positions) == 0:
        print("   ✅ Нет открытых позиций - система чистая")
    elif len(db_open) == len(bybit_positions):
        print("   ✅ Количество позиций совпадает")
    else:
        print("   ⚠️ Есть расхождения в позициях - требуется внимание")
    
    if balances and "USDT" in balances:
        wallet = balances["USDT"]
        db_balance = 100.0 + total_pnl - total_fees
        diff = abs(wallet['total'] - db_balance)
        if diff < 1.0:
            print("   ✅ Балансы полностью совпадают")
        elif diff < 5.0:
            print("   ✅ Балансы почти совпадают (разница < $5)")
        else:
            print("   ⚠️ Балансы расходятся значительно")
    
    print("\n   💡 Все сделки в БД являются РЕАЛЬНЫМИ, если:")
    print("      1. Количество открытых позиций совпадает (БД = Bybit)")
    print("      2. Баланс совпадает с точностью до комиссий")
    print("      3. Нет фантомных позиций (есть в БД, но нет на Bybit)")

if __name__ == "__main__":
    asyncio.run(main())
