"""Детальная проверка состояния торговли"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select, desc

async def main():
    api = get_bybit_api()
    
    print("=" * 60)
    print("1. ОТКРЫТЫЕ ОРДЕРА НА БИРЖЕ (API)")
    print("=" * 60)
    
    for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']:
        orders = await api.get_open_orders(symbol)
        if orders and len(orders) > 0:
            print(f"\n{symbol}: {len(orders)} открытых ордеров")
            for order in orders:
                print(f"  Order ID: {order.get('orderId')}")
                print(f"  Side: {order.get('side')}, Price: {order.get('price')}, Qty: {order.get('qty')}")
                print(f"  Status: {order.get('orderStatus')}")
        else:
            print(f"{symbol}: нет открытых ордеров")
    
    print("\n" + "=" * 60)
    print("2. ИСТОРИЯ ОРДЕРОВ НА БИРЖЕ (последние 10)")
    print("=" * 60)
    
    for symbol in ['ETHUSDT', 'SOLUSDT']:
        history = await api.get_trade_history(symbol, limit=5)
        if history and len(history) > 0:
            print(f"\n{symbol}: {len(history)} записей в истории")
            for trade in history[:3]:
                print(f"  {trade.get('side')} @ ${trade.get('execPrice')} x{trade.get('execQty')} - {trade.get('execTime')}")
        else:
            print(f"{symbol}: нет истории")
    
    print("\n" + "=" * 60)
    print("3. ОТКРЫТЫЕ ПОЗИЦИИ В БД")
    print("=" * 60)
    
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN).order_by(desc(Trade.entry_time))
        )
        open_trades = result.scalars().all()
        
        if len(open_trades) > 0:
            print(f"\nНайдено {len(open_trades)} открытых позиций в БД:")
            for trade in open_trades:
                print(f"  ID {trade.id}: {trade.symbol} {trade.side.value} @ ${trade.entry_price:.2f}")
                print(f"    Quantity: {trade.quantity}, Entry: {trade.entry_time}")
                print(f"    Bybit Order ID: {trade.extra_data.get('bybit_order_id') if trade.extra_data else 'N/A'}")
        else:
            print("✅ Нет открытых позиций в БД")
    
    print("\n" + "=" * 60)
    print("4. ЗАКРЫТЫЕ СДЕЛКИ В БД (последние 10)")
    print("=" * 60)
    
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED).order_by(desc(Trade.exit_time)).limit(10)
        )
        closed_trades = result.scalars().all()
        
        if len(closed_trades) > 0:
            print(f"\nНайдено {len(closed_trades)} закрытых сделок:")
            for trade in closed_trades:
                pnl_emoji = "🟢" if trade.pnl > 0 else "🔴"
                print(f"  {pnl_emoji} ID {trade.id}: {trade.symbol} {trade.side.value}")
                print(f"    Entry: ${trade.entry_price:.2f} -> Exit: ${trade.exit_price:.2f}")
                print(f"    PnL: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)")
                print(f"    Reason: {trade.exit_reason}")
                print(f"    Exit time: {trade.exit_time}")
        else:
            print("Нет закрытых сделок")
    
    print("\n" + "=" * 60)
    print("5. ЛОГИКА БОТА")
    print("=" * 60)
    print("Бот работает так:")
    print("1. Открывает SPOT ордер на бирже (Market order)")
    print("2. Сохраняет позицию в БД со статусом OPEN")
    print("3. Проверяет Stop Loss / Take Profit каждый цикл")
    print("4. Когда цена достигает SL/TP - закрывает позицию:")
    print("   - Открывает обратный ордер на бирже")
    print("   - Обновляет статус в БД на CLOSED")
    print("\nЕсли открытых ордеров нет на бирже, но есть в БД:")
    print("  -> Возможно бот уже закрыл их, но не обновил БД")
    print("  -> Или ордера были закрыты вручную на бирже")

if __name__ == "__main__":
    asyncio.run(main())
