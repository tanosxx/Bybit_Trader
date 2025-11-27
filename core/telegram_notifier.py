"""
Telegram уведомления для Bybit Trading Bot
"""
import asyncio
from typing import Optional
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
    
    async def notify_position_opened(self, trade_data: dict):
        """Уведомление об открытии позиции"""
        message = f"""
🟢 <b>ПОЗИЦИЯ ОТКРЫТА</b>

💱 Пара: <b>{trade_data['symbol']}</b>
📊 Сторона: <b>{trade_data['side']}</b>
💰 Цена входа: <b>${trade_data['entry_price']:.2f}</b>
📦 Количество: <b>{trade_data['quantity']}</b>
💵 Стоимость: <b>${trade_data['cost']:.2f}</b>

🎯 Take Profit: <b>${trade_data['take_profit']:.2f}</b> (+{settings.take_profit_pct}%)
🛑 Stop Loss: <b>${trade_data['stop_loss']:.2f}</b> (-{settings.stop_loss_pct}%)

🤖 AI Risk: <b>{trade_data['ai_risk']}/10</b>
💡 Reasoning: {trade_data['ai_reasoning'][:200]}
"""
        await self.send_message(message)
    
    async def notify_position_closed(self, trade_data: dict):
        """Уведомление о закрытии позиции"""
        emoji = "🟢" if trade_data['pnl'] > 0 else "🔴"
        
        message = f"""
{emoji} <b>ПОЗИЦИЯ ЗАКРЫТА</b>

💱 Пара: <b>{trade_data['symbol']}</b>
📊 Сторона: <b>{trade_data['side']}</b>
💰 Цена входа: <b>${trade_data['entry_price']:.2f}</b>
💰 Цена выхода: <b>${trade_data['exit_price']:.2f}</b>

💵 PnL: <b>${trade_data['pnl']:+.2f}</b> ({trade_data['pnl_pct']:+.2f}%)
📝 Причина: <b>{trade_data['reason']}</b>

⏱ Время в позиции: {trade_data['duration']}
"""
        await self.send_message(message)
    
    async def notify_daily_summary(self, stats: dict):
        """Ежедневная сводка"""
        message = f"""
📊 <b>ЕЖЕДНЕВНАЯ СВОДКА</b>

💰 Баланс: <b>${stats['balance']:.2f}</b>
📈 Изменение: <b>${stats['balance_change']:+.2f}</b> ({stats['balance_change_pct']:+.1f}%)

📊 Сделок сегодня: <b>{stats['trades_today']}</b>
🟢 Выигрышей: <b>{stats['wins']}</b>
🔴 Проигрышей: <b>{stats['losses']}</b>
🎯 Винрейт: <b>{stats['winrate']:.1f}%</b>

💵 Прибыль сегодня: <b>${stats['pnl_today']:+.2f}</b>
💵 Всего прибыль: <b>${stats['total_pnl']:+.2f}</b>

📊 Открытых позиций: <b>{stats['open_positions']}</b>
"""
        await self.send_message(message)
    
    async def notify_risk_warning(self, warning: str):
        """Предупреждение о рисках"""
        message = f"""
⚠️ <b>ПРЕДУПРЕЖДЕНИЕ О РИСКАХ</b>

{warning}
"""
        await self.send_message(message)
    
    async def notify_bot_started(self):
        """Уведомление о запуске бота"""
        message = f"""
🚀 <b>BYBIT TRADING BOT STARTED</b>

✅ Бот успешно запущен
💰 Начальный баланс: <b>${settings.initial_balance:.2f}</b>
📊 Пары: <b>{', '.join(settings.trading_pairs)}</b>
⏱ Интервал: <b>{settings.scan_interval} сек</b>

🎯 Stop Loss: <b>{settings.stop_loss_pct}%</b>
🎯 Take Profit: <b>{settings.take_profit_pct}%</b>
📊 Max позиций: <b>{settings.max_open_positions}</b>
"""
        await self.send_message(message)
    
    async def notify_ml_prediction(self, symbol: str, prediction: dict):
        """Уведомление о ML предсказании"""
        emoji = "📈" if prediction['direction'] == "UP" else "📉" if prediction['direction'] == "DOWN" else "➡️"
        
        message = f"""
{emoji} <b>ML ПРОГНОЗ</b>

💱 Пара: <b>{symbol}</b>
💰 Текущая цена: <b>${prediction['current_price']:.2f}</b>

🔮 Направление: <b>{prediction['direction']}</b>
🎯 Уверенность: <b>{prediction['confidence']:.0%}</b>

📊 Прогноз через 5 мин: <b>${prediction['predicted_price_5m']:.2f}</b> ({prediction['change_5m_pct']:+.2f}%)
📊 Прогноз через 15 мин: <b>${prediction['predicted_price_15m']:.2f}</b> ({prediction['change_15m_pct']:+.2f}%)
"""
        await self.send_message(message)


# Singleton
_telegram_notifier = None

def get_telegram_notifier() -> TelegramNotifier:
    """Получить singleton instance"""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier
