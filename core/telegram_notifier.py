"""
Telegram Reporter v2.0 - Rich Formatting для Futures Trading
Красивые, компактные и информативные уведомления

ТОЛЬКО FUTURES! SPOT уведомления отключены.
"""
import asyncio
from typing import Optional, Dict
from datetime import datetime, timezone
from config import settings


class TelegramReporter:
    """
    Rich Telegram уведомления для Futures Trading
    
    Типы сообщений:
    - OPEN: Открытие позиции (LONG/SHORT)
    - CLOSE: Закрытие (TP/SL/Trailing)
    - INFO: Funding skip, Safety alerts
    """
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.bot = None
        self.enabled = False
        
        if self.bot_token and self.chat_id:
            try:
                from telegram import Bot
                self.bot = Bot(token=self.bot_token)
                self.enabled = True
                print(f"📱 TelegramReporter v2.0: ENABLED")
            except Exception as e:
                print(f"📱 TelegramReporter: DISABLED ({e})")
        else:
            print(f"📱 TelegramReporter: DISABLED (no credentials)")
    
    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Отправить сообщение с обработкой ошибок
        
        Returns: True если успешно
        """
        if not self.enabled or not self.bot:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            return True
        except Exception as e:
            # НЕ падаем! Просто логируем
            print(f"📱 Telegram error (ignored): {e}")
            return False
    
    # ========== FUTURES ONLY ==========
    
    def _check_futures_only(self, market_type: str) -> bool:
        """Фильтр: только FUTURES"""
        if market_type and market_type.lower() == 'spot':
            return False  # SPOT отключен
        return True

    
    # ========== ТИП А: ОТКРЫТИЕ ПОЗИЦИИ ==========
    
    async def notify_open(
        self,
        symbol: str,
        side: str,  # LONG / SHORT
        entry_price: float,
        size_usd: float,
        leverage: int,
        stop_loss: float,
        take_profit: float,
        reason: str = "",
        market_type: str = "futures"
    ):
        """
        🚀 OPEN LONG / 🐻 OPEN SHORT
        
        ОТКЛЮЧЕНО - используйте /orders для просмотра
        """
        # SILENT MODE - не отправляем автоматические уведомления
        return
    
    # ========== ТИП Б: ЗАКРЫТИЕ ПОЗИЦИИ ==========
    
    async def notify_close(
        self,
        symbol: str,
        side: str,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        duration_minutes: int = 0,
        reason: str = "",
        market_type: str = "futures",
        gross_pnl: float = None,
        net_pnl: float = None,
        fees: float = None
    ):
        """
        💰 TAKE PROFIT / 🩸 STOP LOSS
        
        ОТКЛЮЧЕНО - используйте /orders для просмотра
        """
        # SILENT MODE - не отправляем автоматические уведомления
        return
    
    # ========== ТИП В: TRAILING STOP ==========
    
    async def notify_trailing_hit(
        self,
        symbol: str,
        side: str,
        secured_pct: float,
        pnl: float,
        market_type: str = "futures"
    ):
        """
        ⚡ Trailing Stop Hit
        """
        if not self._check_futures_only(market_type):
            return
        
        message = f"""⚡ <b>TRAILING STOP HIT</b>

<b>#{symbol}</b> ({side})
🔒 Secured Profit: <b>+{secured_pct:.1f}%</b> (${pnl:+.2f})"""
        
        await self.send_message(message)
    
    # ========== ТИП Г: FUNDING SKIP ==========
    
    async def notify_funding_skip(
        self,
        symbol: str,
        side: str,
        funding_rate: float,
        minutes_until: int
    ):
        """
        ⚠️ High Funding Skip
        """
        message = f"""⚠️ <b>HIGH FUNDING SKIP</b>

<b>#{symbol}</b> ({side})
💸 Rate: <b>{funding_rate:.4f}%</b>
⏰ Payment in: {minutes_until} min

<i>Trade blocked to avoid fee</i>"""
        
        await self.send_message(message)

    
    # ========== SAFETY ALERTS ==========
    
    async def notify_safety_close(
        self,
        symbol: str,
        side: str,
        pnl: float,
        reasons: list
    ):
        """
        🚨 Safety Guardian закрыл позицию
        """
        reasons_str = ", ".join(reasons) if reasons else "Risk limit"
        
        message = f"""🚨 <b>SAFETY CLOSE</b>

<b>#{symbol}</b> ({side})
💸 PnL: ${pnl:+.2f}
⚠️ Reason: {reasons_str}"""
        
        await self.send_message(message)
    
    # ========== STATUS ==========
    
    async def notify_bot_started(
        self,
        mode: str = "FUTURES",
        spot_enabled: bool = False,
        futures_enabled: bool = True,
        spot_pairs: list = None,
        futures_pairs: list = None
    ):
        """🤖 Bot Started"""
        # Используем переданные пары или из настроек
        f_pairs = futures_pairs or settings.futures_pairs
        pairs = ", ".join(f_pairs[:3])
        if len(f_pairs) > 3:
            pairs += f" +{len(f_pairs) - 3}"
        
        mode_emoji = "🔀" if mode == "HYBRID" else ("📈" if mode == "FUTURES" else "💱")
        
        message = f"""🤖 <b>BOT STARTED</b>

{mode_emoji} Mode: <b>{mode}</b>
💰 Balance: <b>${settings.futures_virtual_balance}</b>
⚡ Leverage: <b>{settings.futures_leverage}x</b> Isolated
📊 Pairs: {pairs}
📈 Trailing: {'ON' if settings.trailing_stop_enabled else 'OFF'}
💸 Funding Filter: {'ON' if settings.funding_rate_filter_enabled else 'OFF'}"""
        
        await self.send_message(message)
    
    async def notify_daily_summary(
        self,
        balance: float,
        pnl_today: float,
        trades_today: int,
        winrate: float,
        open_positions: int
    ):
        """📊 Daily Summary"""
        pnl_emoji = "📈" if pnl_today >= 0 else "📉"
        
        message = f"""📊 <b>DAILY SUMMARY</b>

💰 Balance: <b>${balance:,.2f}</b>
{pnl_emoji} Today PnL: <b>${pnl_today:+.2f}</b>
🎯 Trades: <b>{trades_today}</b> (WR: {winrate:.0f}%)
📈 Open: <b>{open_positions}</b> positions"""
        
        await self.send_message(message)
    
    async def notify_strategic_compliance(
        self,
        regime: str,
        positions_closed: int
    ):
        """🚨 Strategic Compliance - Forced Position Closure"""
        regime_emoji = {
            'UNCERTAIN': '⚠️',
            'BEAR_CRASH': '🐻',
            'BULL_RUSH': '🚀',
            'SIDEWAYS': '↔️'
        }.get(regime, '❓')
        
        regime_desc = {
            'UNCERTAIN': 'High volatility - Cash is King',
            'BEAR_CRASH': 'Bear market - LONG positions closed',
            'BULL_RUSH': 'Bull market - SHORT positions closed',
            'SIDEWAYS': 'Range-bound market'
        }.get(regime, 'Unknown regime')
        
        message = f"""🚨 <b>STRATEGIC COMPLIANCE</b>

{regime_emoji} Regime: <b>{regime}</b>
📝 {regime_desc}

🔒 Closed: <b>{positions_closed}</b> position(s)
💡 Reason: Non-compliant with current strategy"""
        
        await self.send_message(message)
    
    # ========== LEGACY COMPATIBILITY ==========
    
    async def notify_futures_opened(self, **kwargs):
        """Legacy -> notify_open"""
        await self.notify_open(
            symbol=kwargs.get('symbol', ''),
            side=kwargs.get('side', 'LONG'),
            entry_price=kwargs.get('entry_price', 0),
            size_usd=kwargs.get('position_value', kwargs.get('quantity', 0) * kwargs.get('entry_price', 0)),
            leverage=kwargs.get('leverage', 5),
            stop_loss=kwargs.get('stop_loss', 0),
            take_profit=kwargs.get('take_profit', 0),
            reason=kwargs.get('reasoning', ''),
            market_type='futures'
        )
    
    async def notify_futures_closed(self, **kwargs):
        """Legacy -> notify_close"""
        await self.notify_close(
            symbol=kwargs.get('symbol', ''),
            side=kwargs.get('side', 'LONG'),
            exit_price=kwargs.get('exit_price', 0),
            pnl=kwargs.get('pnl', 0),
            pnl_pct=kwargs.get('pnl_pct', 0),
            duration_minutes=0,
            reason=kwargs.get('reason', ''),
            market_type='futures'
        )
    
    async def notify_spot_opened(self, **kwargs):
        """SPOT отключен"""
        pass  # Игнорируем SPOT
    
    async def notify_spot_closed(self, **kwargs):
        """SPOT отключен"""
        pass  # Игнорируем SPOT
    
    async def notify_position_opened(self, trade_data: dict):
        """Legacy"""
        pass
    
    async def notify_position_closed(self, trade_data: dict):
        """Legacy"""
        pass
    
    async def notify_safety_alert(self, closed_positions: list, total_pnl: float):
        """Legacy"""
        for pos in closed_positions:
            await self.notify_safety_close(
                symbol=pos.get('symbol', ''),
                side=pos.get('side', ''),
                pnl=pos.get('pnl', 0),
                reasons=pos.get('reasons', [])
            )
    
    async def notify_risk_warning(self, warning: str, details: str = ""):
        """Legacy"""
        await self.send_message(f"⚠️ {warning}\n{details}")


# Singleton
_telegram_reporter = None

def get_telegram_notifier() -> TelegramReporter:
    """Получить singleton (legacy name)"""
    global _telegram_reporter
    if _telegram_reporter is None:
        _telegram_reporter = TelegramReporter()
    return _telegram_reporter

def get_telegram_reporter() -> TelegramReporter:
    """Получить singleton"""
    return get_telegram_notifier()


# Alias для совместимости
TelegramNotifier = TelegramReporter
