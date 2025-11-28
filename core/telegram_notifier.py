"""
Telegram уведомления для Bybit Trading Bot v2.0
Чёткие и информативные оповещения
"""
import asyncio
from typing import Optional, Dict
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from config import settings


class TelegramNotifier:
    """Отправка уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.bot = None
        
        if self.bot_token and self.chat_id:
            self.bot = Bot(token=self.bot_token)
            self.enabled = True
        else:
            self.enabled = False
    
    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Отправить сообщение"""
        if not self.enabled:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except TelegramError as e:
            print(f"❌ Telegram error: {e}")
    
    # ========== FUTURES NOTIFICATIONS ==========
    
    async def notify_futures_opened(
        self,
        symbol: str,
        side: str,  # LONG / SHORT
        entry_price: float,
        quantity: float,
        leverage: int,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        reasoning: str,
        position_value: float = None
    ):
        """
        Уведомление об открытии FUTURES позиции
        """
        emoji = "🟢" if side == "LONG" else "🔴"
        direction = "�  LONG (покупка)" if side == "LONG" else "📉 SHORT (продажа)"
        
        # Рассчитываем стоимость если не передана
        if position_value is None:
            position_value = entry_price * quantity
        
        # Рассчитываем потенциал
        if side == "LONG":
            sl_pct = ((stop_loss - entry_price) / entry_price) * 100
            tp_pct = ((take_profit - entry_price) / entry_price) * 100
        else:
            sl_pct = ((entry_price - stop_loss) / entry_price) * 100
            tp_pct = ((entry_price - take_profit) / entry_price) * 100
        
        message = f"""
{emoji} <b>FUTURES ОТКРЫТА</b>

💱 <b>{symbol}</b>
{direction}

� <b>>Детали сделки:</b>
├ Цена входа: <b>${entry_price:,.2f}</b>
├ Количество: <b>{quantity}</b>
├ Плечо: <b>{leverage}x</b>
└ Стоимость: <b>${position_value:,.2f}</b>

�️ <b>Зыащита:</b>
├ Stop Loss: <b>${stop_loss:,.2f}</b> ({sl_pct:+.1f}%)
└ Take Profit: <b>${take_profit:,.2f}</b> ({tp_pct:+.1f}%)

🎯 Уверенность: <b>{confidence:.0%}</b>
� Пригчина: {reasoning[:150]}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    async def notify_futures_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        leverage: int,
        pnl: float,
        pnl_pct: float,
        reason: str,
        duration: str = None
    ):
        """
        Уведомление о закрытии FUTURES позиции
        """
        emoji = "✅" if pnl > 0 else "❌"
        result = "ПРИБЫЛЬ" if pnl > 0 else "УБЫТОК"
        
        message = f"""
{emoji} <b>FUTURES ЗАКРЫТА</b>

� <b>{symbol}</b> ({side})

💰 <b>Результат:</b>
├ Вход: <b>${entry_price:,.2f}</b>
├ Выход: <b>${exit_price:,.2f}</b>
├ Плечо: <b>{leverage}x</b>
└ <b>{result}: ${pnl:+.2f}</b> ({pnl_pct:+.1f}%)

📝 Причина: {reason}
{f"⏱ Время в позиции: {duration}" if duration else ""}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    # ========== SPOT NOTIFICATIONS ==========
    
    async def notify_spot_opened(
        self,
        symbol: str,
        side: str,  # BUY / SELL
        entry_price: float,
        quantity: float,
        cost: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        reasoning: str
    ):
        """
        Уведомление об открытии SPOT позиции
        """
        emoji = "🟢" if side == "BUY" else "🔴"
        
        message = f"""
{emoji} <b>SPOT ОТКРЫТА</b>

💱 <b>{symbol}</b>
📊 Действие: <b>{side}</b>

💰 <b>Детали:</b>
├ Цена: <b>${entry_price:,.2f}</b>
├ Количество: <b>{quantity}</b>
└ Стоимость: <b>${cost:,.2f}</b>

🛡️ <b>Защита:</b>
├ Stop Loss: <b>${stop_loss:,.2f}</b>
└ Take Profit: <b>${take_profit:,.2f}</b>

🎯 Уверенность: <b>{confidence:.0%}</b>
💡 Причина: {reasoning[:150]}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    async def notify_spot_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl: float,
        pnl_pct: float,
        reason: str
    ):
        """
        Уведомление о закрытии SPOT позиции
        """
        emoji = "✅" if pnl > 0 else "❌"
        result = "ПРИБЫЛЬ" if pnl > 0 else "УБЫТОК"
        
        message = f"""
{emoji} <b>SPOT ЗАКРЫТА</b>

💱 <b>{symbol}</b>

💰 <b>Результат:</b>
├ Вход: <b>${entry_price:,.2f}</b>
├ Выход: <b>${exit_price:,.2f}</b>
└ <b>{result}: ${pnl:+.2f}</b> ({pnl_pct:+.1f}%)

📝 Причина: {reason}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    # ========== SAFETY ALERTS ==========
    
    async def notify_safety_alert(
        self,
        closed_positions: list,
        total_pnl: float
    ):
        """
        Уведомление от SafetyGuardian
        """
        positions_info = "\n".join([
            f"├ {p['symbol']} {p['side']}: <b>${p['pnl']:+.2f}</b> ({', '.join(p['reasons'])})"
            for p in closed_positions
        ])
        
        message = f"""
🚨 <b>SAFETY GUARDIAN</b>

⚠️ Закрыты опасные позиции:
{positions_info}

💰 Итого PnL: <b>${total_pnl:+.2f}</b>

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    # ========== STATUS NOTIFICATIONS ==========
    
    async def notify_bot_started(self, mode: str, spot_enabled: bool, futures_enabled: bool):
        """Уведомление о запуске бота"""
        message = f"""
🚀 <b>BYBIT BOT ЗАПУЩЕН</b>

⚙️ <b>Режим:</b> {mode}
├ SPOT: {'✅' if spot_enabled else '❌'}
└ FUTURES: {'✅' if futures_enabled else '❌'}

💰 <b>Настройки FUTURES:</b>
├ Баланс: <b>${settings.futures_virtual_balance}</b>
├ Плечо: <b>{settings.futures_leverage}x</b>
└ Риск: <b>{settings.futures_risk_per_trade*100}%</b>

📊 Пары: {', '.join(settings.futures_pairs)}

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    async def notify_daily_summary(
        self,
        futures_balance: float,
        futures_pnl: float,
        futures_trades: int,
        futures_winrate: float,
        spot_balance: float = 0,
        spot_pnl: float = 0,
        spot_trades: int = 0,
        open_positions: int = 0
    ):
        """Ежедневная сводка"""
        message = f"""
📊 <b>ЕЖЕДНЕВНАЯ СВОДКА</b>

💰 <b>FUTURES:</b>
├ Баланс: <b>${futures_balance:,.2f}</b>
├ PnL: <b>${futures_pnl:+.2f}</b>
├ Сделок: <b>{futures_trades}</b>
└ Win Rate: <b>{futures_winrate:.1f}%</b>

💰 <b>SPOT:</b>
├ Баланс: <b>${spot_balance:,.2f}</b>
├ PnL: <b>${spot_pnl:+.2f}</b>
└ Сделок: <b>{spot_trades}</b>

📈 Открытых позиций: <b>{open_positions}</b>

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    async def notify_risk_warning(self, warning: str, details: str = ""):
        """Предупреждение о рисках"""
        message = f"""
⚠️ <b>ПРЕДУПРЕЖДЕНИЕ</b>

{warning}
{details}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        await self.send_message(message)
    
    # ========== LEGACY METHODS (для совместимости) ==========
    
    async def notify_position_opened(self, trade_data: dict):
        """Legacy метод"""
        await self.send_message(
            f"🟢 Позиция открыта: {trade_data.get('symbol', 'N/A')}"
        )
    
    async def notify_position_closed(self, trade_data: dict):
        """Legacy метод"""
        pnl = trade_data.get('pnl', 0)
        emoji = "✅" if pnl > 0 else "❌"
        await self.send_message(
            f"{emoji} Позиция закрыта: {trade_data.get('symbol', 'N/A')} | PnL: ${pnl:+.2f}"
        )


# Singleton
_telegram_notifier = None

def get_telegram_notifier() -> TelegramNotifier:
    """Получить singleton instance"""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier
