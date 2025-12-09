"""
Проверка реальных сделок на Bybit Demo
Сверяет данные из БД с реальными позициями и историей на бирже
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from datetime import datetime
from sqlalchemy import create_engine, text
from core.bybit_api import get_bybit_api
from config import settings

# Database
engine = create_engine(settings.database_url)

def get_db_stats():
    """Получить статистику из БД"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                ROUND(SUM(CASE WHEN status = 'CLOSED' THEN pnl ELSE 0 END)::numeric, 2) as total_pnl,
                ROUND(SUM(CASE WHEN status = 'CLOSED' THEN fee_entry + fee_exit ELSE 0 END)::numeric, 2) as total_fees
            FROM trades 
            WHERE market_type = 'futures'
        """))
        return dict(result.fetchone()._mapping)

def get_db_open_positions():
    """Получить открытые позиции из БД"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, side, entry_price, quantity, entry_time
            FROM trades 
            WHERE status = 'OPEN' AND market_type = 'futures'
            ORDER BY entry_time DESC
        """))
        return [dict(row._mapping) for row in result.fetchall()]

def get_db_recent_closed():
    """Получить последние закрытые сделки из БД"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, side, entry_price, quantity, pnl, entry_time, exit_time
            FROM trades 
            WHERE status = 'CLOSED' AND market_type = 'futures'
            ORDER BY exit_time DESC
            LIMIT 20
        """))
        return [dict(row._mapping) for row in result.fetchall()]

async def get_bybit_positions():
    """Получить реальные позиции с Bybit"""
    try:
        api = get_bybit_api()
        positions = await api.get_positions()
        return positions
    except Exception as e:
        print(f"❌ Ошибка получения позиций: {e}")
        import traceback
        traceback.print_exc()
        return []

async def get_bybit_wallet():
    """Получить реальный баланс с Bybit"""
    try:
        api = get_bybit_api()
        balances = await api.get_wallet_balance()
        if balances and "USDT" in balances:
            usdt = balances["USDT"]
            return {
                "total": usdt["total"],
                "available": usdt["available"],
                "used": usdt["total"] - usdt["available"]
            }
        return None
    except Exception as e:
        print(f"❌ Ошибка получения баланса: {e}")
        import traceback
        traceback.print_exc()
        return None

async def get_bybit_closed_pnl():
    """Получить закрытый PnL с Bybit"""
    try:
        api = get_bybit_api()
        # Получаем историю закрытых позиций
        pnl_records = await api.get_closed_pnl_history(limit=100)
        
        if pnl_records:
            total_pnl = 0
            trades = []
            for record in pnl_records:
                pnl = float(record.get("closedPnl", 0))
                total_pnl += pnl
                trades.append({
                    "symbol": record.get("symbol"),
                    "side": record.get("side"),
                    "qty": float(record.get("qty", 0)),
                    "pnl": pnl,
                    "close_time": datetime.fromtimestamp(int(record.get("updatedTime", 0)) / 1000)
                })
            return {
                "total_pnl": round(total_pnl, 2),
                "count": len(trades),
                "trades": trades[:10]  # Последние 10
            }
        return None
    except Exception as e:
        print(f"❌ Ошибка получения закрытого PnL: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    print("=" * 80)
    print("🔍 ПРОВЕРКА РЕАЛЬНЫХ СДЕЛОК НА BYBIT DEMO")
    print("=" * 80)
    
    # 1. Статистика из БД
    print("\n📊 ДАННЫЕ ИЗ БАЗЫ ДАННЫХ:")
    db_stats = get_db_stats()
    print(f"   Всего сделок: {db_stats['total_trades']}")
    print(f"   Открытых: {db_stats['open_trades']}")
    print(f"   Закрытых: {db_stats['closed_trades']}")
    print(f"   Total PnL: ${db_stats['total_pnl']}")
    print(f"   Total Fees: ${db_stats['total_fees']}")
    print(f"   Net Profit: ${db_stats['total_pnl'] - db_stats['total_fees']}")
    
    # 2. Открытые позиции в БД
    print("\n📂 ОТКРЫТЫЕ ПОЗИЦИИ В БД:")
    db_open = get_db_open_positions()
    if db_open:
        for pos in db_open:
            print(f"   {pos['symbol']} {pos['side']} | Qty: {pos['quantity']} | Entry: ${pos['entry_price']} | Time: {pos['entry_time']}")
    else:
        print("   ✅ Нет открытых позиций")
    
    # 3. Реальные позиции на Bybit
    print("\n🌐 РЕАЛЬНЫЕ ПОЗИЦИИ НА BYBIT:")
    bybit_positions = await get_bybit_positions()
    if bybit_positions:
        for pos in bybit_positions:
            print(f"   {pos['symbol']} {pos['side']} | Size: {pos['size']} | Entry: ${pos['entry_price']} | Unrealized PnL: ${pos['unrealized_pnl']}")
    else:
        print("   ✅ Нет открытых позиций")
    
    # 4. Сверка открытых позиций
    print("\n🔄 СВЕРКА ОТКРЫТЫХ ПОЗИЦИЙ:")
    if len(db_open) == len(bybit_positions):
        print(f"   ✅ Количество совпадает: {len(db_open)} позиций")
        
        # Проверяем каждую позицию
        db_symbols = {pos['symbol']: pos for pos in db_open}
        bybit_symbols = {pos['symbol']: pos for pos in bybit_positions}
        
        for symbol in db_symbols:
            if symbol in bybit_symbols:
                db_pos = db_symbols[symbol]
                bybit_pos = bybit_symbols[symbol]
                
                qty_match = abs(db_pos['quantity'] - bybit_pos['size']) < 0.01
                side_match = db_pos['side'] == bybit_pos['side']
                
                if qty_match and side_match:
                    print(f"   ✅ {symbol}: Полное совпадение")
                else:
                    print(f"   ⚠️ {symbol}: Расхождение!")
                    print(f"      БД: {db_pos['side']} {db_pos['quantity']}")
                    print(f"      Bybit: {bybit_pos['side']} {bybit_pos['size']}")
            else:
                print(f"   ❌ {symbol}: Есть в БД, но НЕТ на Bybit (фантомная позиция!)")
        
        for symbol in bybit_symbols:
            if symbol not in db_symbols:
                print(f"   ⚠️ {symbol}: Есть на Bybit, но НЕТ в БД")
    else:
        print(f"   ❌ Расхождение количества: БД={len(db_open)}, Bybit={len(bybit_positions)}")
    
    # 5. Реальный баланс на Bybit
    print("\n💰 РЕАЛЬНЫЙ БАЛАНС НА BYBIT:")
    wallet = await get_bybit_wallet()
    if wallet:
        print(f"   Total Equity: ${wallet['total']:.2f}")
        print(f"   Available: ${wallet['available']:.2f}")
        print(f"   Used in Positions: ${wallet['used']:.2f}")
        
        # Сравнение с БД
        db_balance = 100.0 + db_stats['total_pnl'] - db_stats['total_fees']
        diff = wallet['total'] - db_balance
        print(f"\n   📊 Сравнение с БД:")
        print(f"      БД Balance: ${db_balance:.2f}")
        print(f"      Bybit Balance: ${wallet['total']:.2f}")
        print(f"      Разница: ${diff:.2f}")
        
        if abs(diff) < 1.0:
            print(f"      ✅ Балансы совпадают (разница < $1)")
        else:
            print(f"      ⚠️ Есть расхождение в балансах")
    
    # 6. История закрытых сделок на Bybit
    print("\n📜 ИСТОРИЯ ЗАКРЫТЫХ СДЕЛОК НА BYBIT (последние 10):")
    closed_pnl = await get_bybit_closed_pnl()
    if closed_pnl:
        print(f"   Всего закрытых сделок: {closed_pnl['count']}")
        print(f"   Total Closed PnL: ${closed_pnl['total_pnl']}")
        print(f"\n   Последние сделки:")
        for trade in closed_pnl['trades']:
            print(f"   {trade['symbol']} {trade['side']} | Qty: {trade['qty']} | PnL: ${trade['pnl']:.2f} | {trade['close_time']}")
    
    # 7. Последние закрытые сделки из БД
    print("\n📂 ПОСЛЕДНИЕ ЗАКРЫТЫЕ СДЕЛКИ В БД (последние 10):")
    db_closed = get_db_recent_closed()
    for trade in db_closed[:10]:
        print(f"   {trade['symbol']} {trade['side']} | Qty: {trade['quantity']} | PnL: ${trade['pnl']:.2f} | Exit: {trade['exit_time']}")
    
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
