"""
Очистка "фантомных" открытых позиций в БД
На SPOT рынке нет открытых позиций - все сделки мгновенные
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import async_session
from database.models import Trade, TradeStatus
from sqlalchemy import select
from core.bybit_api import get_bybit_api


async def main():
    api = get_bybit_api()
    
    print("=== ОЧИСТКА ФАНТОМНЫХ ПОЗИЦИЙ ===\n")
    
    # Получаем все "открытые" позиции из БД
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = result.scalars().all()
    
    if not open_trades:
        print("✅ Нет открытых позиций в БД")
        return
    
    print(f"Найдено {len(open_trades)} открытых позиций в БД\n")
    
    # Получаем реальный баланс
    balances = await api.get_wallet_balance()
    
    closed_count = 0
    
    for trade in open_trades:
        base_coin = trade.symbol.replace('USDT', '').replace('USDC', '')
        
        # Проверяем, есть ли монеты на балансе
        has_coins = base_coin in balances and balances[base_coin]['total'] >= trade.quantity * 0.5
        
        if has_coins:
            print(f"⚠️  {trade.symbol}: монеты ЕСТЬ на балансе ({balances[base_coin]['total']:.8f} {base_coin})")
            print(f"   Это реальный холдинг, оставляем открытым")
        else:
            print(f"🔴 {trade.symbol}: монеты НЕТ на балансе")
            print(f"   Закрываем в БД...")
            
            # Получаем текущую цену
            ticker = await api.get_ticker(trade.symbol)
            if ticker:
                price_field = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
                current_price = float(price_field) if price_field else trade.entry_price
            else:
                current_price = trade.entry_price
            
            # Закрываем в БД
            from datetime import datetime
            
            async with async_session() as session:
                trade.status = TradeStatus.CLOSED
                trade.exit_price = current_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = (current_price - trade.entry_price) * trade.quantity
                trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
                
                if trade.extra_data is None:
                    trade.extra_data = {}
                trade.extra_data['close_reason'] = 'Cleanup: coins not found on balance'
                
                session.add(trade)
                await session.commit()
            
            print(f"   ✅ Закрыто: PnL ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%)")
            closed_count += 1
        
        print()
    
    print("="*60)
    print(f"Закрыто фантомных позиций: {closed_count}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
