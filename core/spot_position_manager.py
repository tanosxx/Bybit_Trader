"""
Менеджер SPOT позиций
Отслеживает купленные монеты и автоматически продает при SL/TP
+ TRAILING STOP LOSS
"""
from typing import Dict, List
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from sqlalchemy import select
from core.bybit_api import get_bybit_api
from core.ta_lib import get_dynamic_risk_manager


class SpotPositionManager:
    """Управление SPOT позициями с Trailing Stop"""
    
    def __init__(self):
        self.bybit_api = get_bybit_api()
        self.risk_manager = get_dynamic_risk_manager()
        
        # Кэш trailing stops (trade_id -> current_trailing_sl)
        self._trailing_stops: Dict[int, float] = {}
    
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
            
            # Используем trailing SL если есть, иначе обычный
            effective_sl = self._trailing_stops.get(trade.id, trade.stop_loss)
            
            # Проверяем Stop Loss (с учётом trailing)
            if trade.side == TradeSide.BUY and current_price <= effective_sl:
                is_trailing = trade.id in self._trailing_stops and self._trailing_stops[trade.id] > trade.stop_loss
                reason = "Trailing Stop triggered" if is_trailing else "Stop Loss triggered"
                print(f"🛑 {reason} for {trade.symbol} @ ${effective_sl:.2f}")
                await self._close_spot_position(trade, current_price, reason, telegram_notifier)
                # Очищаем trailing stop из кэша
                if trade.id in self._trailing_stops:
                    del self._trailing_stops[trade.id]
            
            # Проверяем Take Profit
            elif trade.side == TradeSide.BUY and current_price >= trade.take_profit:
                print(f"🎯 Take Profit reached for {trade.symbol}")
                await self._close_spot_position(trade, current_price, "Take Profit reached", telegram_notifier)
                if trade.id in self._trailing_stops:
                    del self._trailing_stops[trade.id]
            
            else:
                # Показываем текущий статус
                pnl = (current_price - trade.entry_price) * trade.quantity
                pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
                
                # ========== TRAILING STOP LOGIC ==========
                # Получаем trailing distance из extra_data или используем дефолт
                trailing_distance = None
                if trade.extra_data and 'trailing_stop_distance' in trade.extra_data:
                    trailing_distance = trade.extra_data['trailing_stop_distance']
                
                # Текущий trailing SL (из кэша или начальный)
                current_trailing_sl = self._trailing_stops.get(trade.id, trade.stop_loss)
                
                # Проверяем нужно ли обновить trailing stop
                if pnl > 0 and trailing_distance:  # Только в прибыли
                    trailing_result = self.risk_manager.calculate_trailing_stop(
                        entry_price=trade.entry_price,
                        current_price=current_price,
                        side=trade.side.value,
                        initial_stop_loss=current_trailing_sl,
                        trailing_percent=None,  # Используем ATR-based
                        klines=None  # Используем trailing_distance напрямую
                    )
                    
                    # Ручной расчёт если есть trailing_distance
                    if trade.side == TradeSide.BUY:
                        potential_new_sl = current_price - trailing_distance
                        if potential_new_sl > current_trailing_sl:
                            self._trailing_stops[trade.id] = potential_new_sl
                            profit_locked = potential_new_sl - trade.entry_price
                            print(f"   📈 {trade.symbol}: TRAILING SL updated to ${potential_new_sl:.2f} (locked: ${profit_locked:+.2f})")
                
                print(f"   {trade.symbol}: ${current_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | SL: ${current_trailing_sl:.2f}")
    
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
    
    async def close_all_positions(self, telegram_notifier=None):
        """
        PANIC SELL - закрыть ВСЕ открытые позиции немедленно!
        Используется при EXTREME_FEAR новостном фоне
        """
        print(f"\n🚨 PANIC SELL - Closing ALL positions!")
        
        # Получаем все открытые позиции
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.OPEN)
            )
            open_trades = result.scalars().all()
        
        if not open_trades:
            print(f"   No open positions to close")
            return
        
        closed_count = 0
        total_pnl = 0.0
        
        for trade in open_trades:
            # Получаем текущую цену
            ticker = await self.bybit_api.get_ticker(trade.symbol)
            if not ticker:
                continue
            
            price = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
            if not price:
                continue
            
            current_price = float(price)
            
            # Закрываем позицию
            result = await self._close_spot_position(
                trade, 
                current_price, 
                "PANIC SELL - Extreme Fear detected",
                telegram_notifier
            )
            
            if result.get("success"):
                closed_count += 1
                total_pnl += result.get("pnl", 0)
        
        print(f"🚨 PANIC SELL complete: {closed_count} positions closed, Total PnL: ${total_pnl:+.2f}")



# Singleton
_spot_manager = None

def get_spot_position_manager():
    """Получить singleton instance"""
    global _spot_manager
    if _spot_manager is None:
        _spot_manager = SpotPositionManager()
    return _spot_manager
