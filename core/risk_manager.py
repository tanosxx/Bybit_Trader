"""
Risk Manager - Жёсткий контроль рисков (Anti-Tilt Protection)
Версия: 2.0 (30.12.2025)

Функции:
1. Daily Loss Limit (Circuit Breaker) - блокировка при превышении дневного лимита
2. Loss Cooldown (Anti-Whipsaw) - пауза после убытка на конкретной паре
3. Проверка перед открытием позиции
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Trade, TradeStatus


class RiskManager:
    """
    Менеджер рисков с защитой от тильта
    """
    
    def __init__(self):
        """Инициализация Risk Manager"""
        self.daily_loss_limit_enabled = settings.daily_loss_limit_enabled
        self.max_daily_loss_percent = settings.max_daily_loss_percent
        self.loss_cooldown_enabled = settings.loss_cooldown_enabled
        self.loss_cooldown_minutes = settings.loss_cooldown_minutes
        
        # Кэш для cooldown (symbol -> datetime последнего убытка)
        self._cooldown_cache: Dict[str, datetime] = {}
        
        print(f"✅ Risk Manager initialized")
        if self.daily_loss_limit_enabled:
            print(f"   📊 Daily Loss Limit: {self.max_daily_loss_percent * 100}% of balance")
        if self.loss_cooldown_enabled:
            print(f"   ⏸️  Loss Cooldown: {self.loss_cooldown_minutes} minutes per symbol")
    
    async def check_daily_loss_limit(self, session: AsyncSession, current_balance: float) -> Tuple[bool, str]:
        """
        Проверить дневной лимит убытков (Circuit Breaker)
        
        Args:
            session: Database session
            current_balance: Текущий баланс
        
        Returns:
            (allowed: bool, reason: str)
            - allowed=True: торговля разрешена
            - allowed=False: торговля заблокирована (превышен лимит)
        """
        if not self.daily_loss_limit_enabled:
            return True, "Daily loss limit disabled"
        
        # Получаем начало текущего дня (00:00 UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Считаем PnL за сегодня (только закрытые сделки)
        result = await session.execute(
            select(
                func.sum(Trade.pnl - Trade.fee_entry - Trade.fee_exit).label('daily_net_pnl')
            ).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.exit_time >= today_start
            )
        )
        
        daily_net_pnl = result.scalar() or 0.0
        
        # Рассчитываем лимит убытков
        max_daily_loss = current_balance * self.max_daily_loss_percent
        
        # Проверка: если убыток превысил лимит
        if daily_net_pnl < -max_daily_loss:
            # Блокируем торговлю до конца дня
            next_day = today_start + timedelta(days=1)
            hours_until_reset = (next_day - datetime.utcnow()).total_seconds() / 3600
            
            reason = (
                f"⛔ DAILY LOSS LIMIT REACHED!\n"
                f"   Today's Loss: ${-daily_net_pnl:.2f} (limit: ${max_daily_loss:.2f})\n"
                f"   Trading halted until {next_day.strftime('%Y-%m-%d %H:%M')} UTC "
                f"({hours_until_reset:.1f}h remaining)"
            )
            
            return False, reason
        
        # Торговля разрешена
        remaining = max_daily_loss + daily_net_pnl
        reason = f"Daily loss check passed (${daily_net_pnl:.2f} / ${-max_daily_loss:.2f} limit, ${remaining:.2f} remaining)"
        
        return True, reason
    
    async def check_loss_cooldown(self, session: AsyncSession, symbol: str) -> Tuple[bool, str]:
        """
        Проверить cooldown после убытка на конкретной паре (Anti-Whipsaw)
        
        Args:
            session: Database session
            symbol: Торговая пара (например, SOLUSDT)
        
        Returns:
            (allowed: bool, reason: str)
            - allowed=True: торговля разрешена
            - allowed=False: пара в cooldown (нужно подождать)
        """
        if not self.loss_cooldown_enabled:
            return True, "Loss cooldown disabled"
        
        # Проверяем кэш
        if symbol in self._cooldown_cache:
            last_loss_time = self._cooldown_cache[symbol]
            cooldown_end = last_loss_time + timedelta(minutes=self.loss_cooldown_minutes)
            
            if datetime.utcnow() < cooldown_end:
                # Cooldown ещё активен
                minutes_remaining = (cooldown_end - datetime.utcnow()).total_seconds() / 60
                reason = (
                    f"⏸️  {symbol} in COOLDOWN after recent loss\n"
                    f"   Wait {minutes_remaining:.1f} minutes (until {cooldown_end.strftime('%H:%M:%S')} UTC)"
                )
                return False, reason
            else:
                # Cooldown истёк, удаляем из кэша
                del self._cooldown_cache[symbol]
        
        # Проверяем БД: была ли последняя сделка убыточной?
        result = await session.execute(
            select(Trade).where(
                Trade.symbol == symbol,
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures'
            ).order_by(Trade.exit_time.desc()).limit(1)
        )
        
        last_trade = result.scalar_one_or_none()
        
        if last_trade and last_trade.pnl < 0:
            # Последняя сделка была убыточной
            cooldown_end = last_trade.exit_time + timedelta(minutes=self.loss_cooldown_minutes)
            
            if datetime.utcnow() < cooldown_end:
                # Cooldown активен
                self._cooldown_cache[symbol] = last_trade.exit_time
                minutes_remaining = (cooldown_end - datetime.utcnow()).total_seconds() / 60
                
                reason = (
                    f"⏸️  {symbol} in COOLDOWN after loss (${last_trade.pnl:.2f})\n"
                    f"   Last loss: {last_trade.exit_time.strftime('%H:%M:%S')} UTC\n"
                    f"   Wait {minutes_remaining:.1f} minutes (until {cooldown_end.strftime('%H:%M:%S')} UTC)"
                )
                return False, reason
        
        # Cooldown не активен
        reason = f"Loss cooldown check passed for {symbol}"
        return True, reason
    
    async def can_open_position(
        self, 
        session: AsyncSession, 
        symbol: str, 
        current_balance: float
    ) -> Tuple[bool, str]:
        """
        Комплексная проверка: можно ли открыть позицию?
        
        Проверяет:
        1. Daily Loss Limit (Circuit Breaker)
        2. Loss Cooldown (Anti-Whipsaw)
        
        Args:
            session: Database session
            symbol: Торговая пара
            current_balance: Текущий баланс
        
        Returns:
            (allowed: bool, reason: str)
        """
        # Проверка 1: Daily Loss Limit
        daily_allowed, daily_reason = await self.check_daily_loss_limit(session, current_balance)
        
        if not daily_allowed:
            return False, daily_reason
        
        # Проверка 2: Loss Cooldown
        cooldown_allowed, cooldown_reason = await self.check_loss_cooldown(session, symbol)
        
        if not cooldown_allowed:
            return False, cooldown_reason
        
        # Все проверки пройдены
        return True, "All risk checks passed"
    
    def register_loss(self, symbol: str, loss_time: Optional[datetime] = None):
        """
        Зарегистрировать убыток для cooldown
        
        Args:
            symbol: Торговая пара
            loss_time: Время убытка (по умолчанию - сейчас)
        """
        if not self.loss_cooldown_enabled:
            return
        
        if loss_time is None:
            loss_time = datetime.utcnow()
        
        self._cooldown_cache[symbol] = loss_time
        print(f"   ⏸️  {symbol} cooldown registered until {(loss_time + timedelta(minutes=self.loss_cooldown_minutes)).strftime('%H:%M:%S')} UTC")


# Singleton instance
_risk_manager_instance = None


def get_risk_manager() -> RiskManager:
    """Получить singleton instance Risk Manager"""
    global _risk_manager_instance
    if _risk_manager_instance is None:
        _risk_manager_instance = RiskManager()
    return _risk_manager_instance
