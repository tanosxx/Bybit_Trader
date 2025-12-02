"""
Balance Tracker - Учёт виртуального баланса с комиссиями

Отслеживает:
1. Виртуальный баланс фьючерсов ($100 стартовый)
2. Комиссии Bybit (0.055% taker)
3. Funding Rate комиссии
4. История изменений баланса
"""
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import select, func
from database.db import async_session
from database.models import Trade, TradeStatus, AppConfig
from config import settings


class BalanceTracker:
    """Трекер виртуального баланса с учётом всех комиссий"""
    
    # Комиссии Bybit
    TAKER_FEE_PCT = 0.055  # 0.055% за исполнение
    MAKER_FEE_PCT = 0.02   # 0.02% за лимитные ордера (не используем)
    
    def __init__(self):
        self.initial_balance = settings.futures_virtual_balance  # $100
        self.session_start = datetime(2025, 12, 2, 16, 0, 0)  # Время сброса
    
    async def get_current_balance(self) -> Dict:
        """
        Получить текущий виртуальный баланс
        
        Формула:
        balance = initial_balance + realized_pnl - total_fees
        
        Returns:
            {
                'initial_balance': 100.0,
                'current_balance': 105.23,
                'realized_pnl': 8.50,
                'total_fees': 3.27,
                'trading_fees': 2.10,
                'funding_fees': 1.17,
                'pnl_pct': 5.23,
                'total_trades': 15,
                'open_positions': 3
            }
        """
        async with async_session() as session:
            # Закрытые сделки с момента сброса
            closed_result = await session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.CLOSED,
                    Trade.market_type == 'futures',
                    Trade.entry_time >= self.session_start
                )
            )
            closed_trades = closed_result.scalars().all()
            
            # Открытые позиции
            open_result = await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'futures'
                )
            )
            open_positions = open_result.scalar() or 0
        
        # Рассчитываем PnL и комиссии
        realized_pnl = 0.0
        trading_fees = 0.0
        
        for trade in closed_trades:
            # PnL из БД
            realized_pnl += float(trade.pnl or 0)
            
            # Комиссии за вход и выход
            entry_fee = float(trade.fee_entry or 0)
            exit_fee = float(trade.fee_exit or 0)
            
            # Если комиссии не записаны, рассчитываем
            if entry_fee == 0:
                entry_value = trade.entry_price * trade.quantity
                entry_fee = entry_value * (self.TAKER_FEE_PCT / 100)
            
            if exit_fee == 0 and trade.exit_price:
                exit_value = trade.exit_price * trade.quantity
                exit_fee = exit_value * (self.TAKER_FEE_PCT / 100)
            
            trading_fees += (entry_fee + exit_fee)
        
        # TODO: Funding fees (пока 0, нужно логировать отдельно)
        funding_fees = 0.0
        
        total_fees = trading_fees + funding_fees
        
        # Итоговый баланс
        current_balance = self.initial_balance + realized_pnl - total_fees
        pnl_pct = ((current_balance - self.initial_balance) / self.initial_balance * 100)
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': current_balance,
            'realized_pnl': realized_pnl,
            'total_fees': total_fees,
            'trading_fees': trading_fees,
            'funding_fees': funding_fees,
            'pnl_pct': pnl_pct,
            'total_trades': len(closed_trades),
            'open_positions': open_positions,
            'session_start': self.session_start.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    async def calculate_trade_fees(self, entry_price: float, exit_price: float, 
                                   quantity: float, leverage: int = 1) -> Dict:
        """
        Рассчитать комиссии для сделки
        
        Args:
            entry_price: Цена входа
            exit_price: Цена выхода
            quantity: Количество
            leverage: Плечо (для расчёта позиции)
        
        Returns:
            {
                'entry_fee': 0.52,
                'exit_fee': 0.55,
                'total_fee': 1.07,
                'entry_value': 950.0,
                'exit_value': 1000.0
            }
        """
        # Стоимость позиции (без учёта плеча для комиссий)
        entry_value = entry_price * quantity
        exit_value = exit_price * quantity
        
        # Комиссии (taker fee)
        entry_fee = entry_value * (self.TAKER_FEE_PCT / 100)
        exit_fee = exit_value * (self.TAKER_FEE_PCT / 100)
        
        return {
            'entry_fee': entry_fee,
            'exit_fee': exit_fee,
            'total_fee': entry_fee + exit_fee,
            'entry_value': entry_value,
            'exit_value': exit_value
        }
    
    async def save_balance_snapshot(self):
        """Сохранить снимок баланса в AppConfig"""
        balance_data = await self.get_current_balance()
        
        async with async_session() as session:
            # Обновляем или создаём запись
            result = await session.execute(
                select(AppConfig).where(AppConfig.key == 'futures_virtual_balance')
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.value = str(balance_data['current_balance'])
                config.updated_at = datetime.utcnow()
            else:
                config = AppConfig(
                    key='futures_virtual_balance',
                    value=str(balance_data['current_balance'])
                )
                session.add(config)
            
            await session.commit()
    
    async def get_balance_history(self, days: int = 7) -> list:
        """
        Получить историю баланса по закрытым сделкам
        
        Returns: список точек для графика
        """
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.CLOSED,
                    Trade.market_type == 'futures',
                    Trade.entry_time >= self.session_start
                ).order_by(Trade.exit_time)
            )
            trades = result.scalars().all()
        
        history = []
        running_balance = self.initial_balance
        
        for trade in trades:
            if not trade.exit_time:
                continue
            
            # PnL
            pnl = float(trade.pnl or 0)
            
            # Комиссии
            fees = await self.calculate_trade_fees(
                trade.entry_price,
                trade.exit_price or trade.entry_price,
                trade.quantity
            )
            
            # Обновляем баланс
            running_balance += pnl - fees['total_fee']
            
            history.append({
                'time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'balance': running_balance,
                'pnl': pnl,
                'fees': fees['total_fee'],
                'symbol': trade.symbol,
                'side': trade.extra_data.get('position_side', 'LONG') if trade.extra_data else 'LONG'
            })
        
        return history


# Singleton
_balance_tracker = None

def get_balance_tracker() -> BalanceTracker:
    global _balance_tracker
    if _balance_tracker is None:
        _balance_tracker = BalanceTracker()
    return _balance_tracker
