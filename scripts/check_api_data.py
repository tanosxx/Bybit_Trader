"""Проверка данных с API Bybit"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from database.db import async_session
from database.models import Trade, WalletHistory, TradeStatus
from sqlalchemy import select, desc, func

async def main():
    api = get_bybit_api()
    
    print("=== 1. БАЛАНС ВСЕХ ВАЛЮТ (API) ===")
    balances = await api.get_wallet_balance()
    if balances:
        for coin, data in balances.items():
            if data['total'] > 0:
                print(f"{coin}: {data['total']:.8f} (available: {data['available']:.8f})")
    
    print("\n=== 2. ОТКРЫТЫЕ ОРДЕРА (API) ===")
    open_orders = await api.get_open_orders("BTCUSDT")
    print(f"BTCUSDT: {len(open_orders) if open_orders else 0} ордеров")
    
    open_orders = await api.get_open_orders("ETHUSDT")
    print(f"ETHUSDT: {len(open_orders) if open_orders else 0} ордеров")
    
    print("\n=== 3. ИСТОРИЯ ОРДЕРОВ (API, последние 10) ===")
    order_history = await api.get_order_history("BTCUSDT", limit=5)
    if order_history:
        for order in order_history[:5]:
            print(f"  {order.get('symbol')} {order.get('side')} @ {order.get('avgPrice')} - {order.get('orderStatus')}")
    
    print("\n=== 4. ОТКРЫТЫЕ СДЕЛКИ (БД) ===")
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = result.scalars().all()
        print(f"Открытых сделок в БД: {len(open_trades)}")
        for trade in open_trades:
            print(f"  {trade.symbol} {trade.side.value} @ ${trade.entry_price:.2f} x{trade.quantity}")
    
    print("\n=== 5. ЗАКРЫТЫЕ СДЕЛКИ (БД) ===")
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED).order_by(desc(Trade.exit_time)).limit(5)
        )
        closed_trades = result.scalars().all()
        print(f"Закрытых сделок в БД: {len(closed_trades)}")
        for trade in closed_trades:
            pnl_emoji = "🟢" if trade.pnl > 0 else "🔴"
            print(f"  {pnl_emoji} {trade.symbol} {trade.side.value} PnL: ${trade.pnl:.2f}")
    
    print("\n=== 6. ИСТОРИЯ БАЛАНСА (БД) ===")
    async with async_session() as session:
        result = await session.execute(
            select(WalletHistory).order_by(desc(WalletHistory.time)).limit(5)
        )
        wallet_history = result.scalars().all()
        print(f"Записей истории баланса: {len(wallet_history)}")
        for wallet in wallet_history:
            print(f"  {wallet.time.strftime('%Y-%m-%d %H:%M')} - ${wallet.balance_usdt:.2f} ({wallet.change_reason})")

if __name__ == "__main__":
    asyncio.run(main())
