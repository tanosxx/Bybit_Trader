"""
Менеджер SPOT позиций
Отслеживает купленные монеты и автоматически продает при SL/TP
"""
from typing import Dict, List
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from sqlalchemy import select
from core.bybit_api import get_bybit_api


class SpotPositionManager:
    """Управление SPOT позициями"""
    
    def __init__(self):
        self.bybit_api = get_bybit_api()
    
    async def check_and_close_positions(self, telegram_notifier=None):
        """
        Проверить холдинги (монеты на балансе) и продать при достижении SL/TP
        """
        # Получаем реальный баланс с биржи
        balances = await self.bybit_api.get_wallet_balance()
        
        if not balances:
            return
        
        # Получаем открытые позиции из БД
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.OPEN)
            )
            open_trades = result.scalars().all()
        
        if not open_trades:
            return
        
        print(f"\n🔍 Checking {len(open_trades)} holdings...")
        
        # Проверяем каждую позицию
        for trade in open_trades:
            # Определяем базовую монету (BTC из BTCUSDT)
            base_coin = trade.symbol.replace('USDT', '').replace('USDC', '')
            
            # Проверяем, есть ли монеты на балансе
            if base_coin not in balances or balances[base_coin]['total'] < trade.quantity * 0.5:
                # Монет нет или их слишком мало - закрываем позицию в БД
                print(f"⚠️  {trade.symbol}: монеты не найдены на балансе, закрываем в БД")
                
                # Получаем текущую цену
                ticker = await self.bybit_api.get_ticker(trade.symbol)
                if ticker:
                    price = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
                    if price:
                        current_price = float(price)
                        await self._close_position_in_db(trade, current_price, "Coins not found in balance (already sold or error)")
                continue
            
            # Получаем текущую цену
            ticker = await self.bybit_api.get_ticker(trade.symbol)
            if not ticker:
                continue
            
            price = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
            if not price:
                continue
            
            current_price = float(price)
            
            # Проверяем Stop Loss
            if trade.side == TradeSide.BUY and current_price <= trade.stop_loss:
                print(f"🛑 Stop Loss triggered for {trade.symbol}")
                await self._close_spot_position(trade, current_price, "Stop Loss triggered", telegram_notifier)
            
            # Проверяем Take Profit
            elif trade.side == TradeSide.BUY and current_price >= trade.take_profit:
                print(f"🎯 Take Profit reached for {trade.symbol}")
                await self._close_spot_position(trade, current_price, "Take Profit reached", telegram_notifier)
            
            else:
                # Показываем текущий статус
                pnl = (current_price - trade.entry_price) * trade.quantity
                pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
                print(f"   {trade.symbol}: ${current_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
    
    async def _close_spot_position(self, trade: Trade, exit_price: float, reason: str, telegram_notifier=None):
        """
        Закрыть SPOT позицию (продать монеты)
        """
        try:
            from core.real_trader import get_real_trader
            trader = get_real_trader()
            
            # Закрываем позицию через RealTrader
            result = await trader.close_trade(trade, exit_price, reason)
            
            if result.get("success") and telegram_notifier:
                await telegram_notifier.notify_position_closed(result)
            
            return result
        
        except Exception as e:
            print(f"❌ Error closing position: {e}")
            return {"success": False, "error": str(e)}
    
    async def _close_position_in_db(self, trade: Trade, exit_price: float, reason: str):
        """
        Закрыть позицию только в БД (без продажи на бирже)
        """
        try:
            from datetime import datetime
            
            async with async_session() as session:
                trade.status = TradeStatus.CLOSED
                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = (exit_price - trade.entry_price) * trade.quantity
                trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.quantity)) * 100
                trade.exit_reason = reason
                
                session.add(trade)
                await session.commit()
                
                print(f"✅ Position closed in DB: {trade.symbol} PnL: ${trade.pnl:+.2f}")
        
        except Exception as e:
            print(f"❌ Error closing position in DB: {e}")



# Singleton
_spot_manager = None

def get_spot_position_manager():
    """Получить singleton instance"""
    global _spot_manager
    if _spot_manager is None:
        _spot_manager = SpotPositionManager()
    return _spot_manager
