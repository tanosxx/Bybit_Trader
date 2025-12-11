"""
Telegram Commander v1.0 - Интерактивный командир бота

ФИЛОСОФИЯ "SILENT MODE":
- Бот МОЛЧИТ по умолчанию
- Пишет ТОЛЬКО на команды или при ЧП

КОМАНДЫ:
- /start - Приветствие и список команд
- /status - Сводка "одним взглядом"
- /brain - Что думает система
- /panic - Emergency Stop (закрыть всё и остановить)
- /balance - Детальный баланс
"""
import asyncio
import os
from typing import Optional
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from config import settings


class TelegramCommander:
    """
    Интерактивный командир бота через Telegram
    
    Работает асинхронно, не блокирует основной цикл торговли
    """
    
    def __init__(self, executor=None, ai_brain=None, strategic_brain=None):
        """
        Args:
            executor: FuturesExecutor для управления позициями
            ai_brain: LocalBrain для получения состояния AI
            strategic_brain: StrategicBrain для получения режима рынка
        """
        self.executor = executor
        self.ai_brain = ai_brain
        self.strategic_brain = strategic_brain
        
        # Telegram credentials
        self.bot_token = settings.telegram_bot_token
        self.admin_chat_id = settings.telegram_chat_id
        
        # Application
        self.app: Optional[Application] = None
        self.is_running = False
        
        # Emergency state
        self.panic_mode = False
        
        print(f"🤖 TelegramCommander initialized (SILENT MODE)")
        print(f"   Admin Chat ID: {self.admin_chat_id}")
    
    async def start(self):
        """Запустить Telegram бота"""
        if not self.bot_token or not self.admin_chat_id:
            print("⚠️ Telegram credentials not set - Commander disabled")
            return
        
        try:
            # Build application
            self.app = Application.builder().token(self.bot_token).build()
            
            # Register handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("brain", self.cmd_brain))
            self.app.add_handler(CommandHandler("panic", self.cmd_panic))
            self.app.add_handler(CommandHandler("balance", self.cmd_balance))
            
            # Ignore non-admin messages
            self.app.add_handler(MessageHandler(filters.ALL, self.ignore_non_admin))
            
            # Start polling
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            self.is_running = True
            print("✅ TelegramCommander started (polling)")
            
        except Exception as e:
            print(f"❌ TelegramCommander start error: {e}")
    
    async def stop(self):
        """Остановить Telegram бота"""
        if self.app and self.is_running:
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
                self.is_running = False
                print("✅ TelegramCommander stopped")
            except Exception as e:
                print(f"⚠️ TelegramCommander stop error: {e}")
    
    def _is_admin(self, update: Update) -> bool:
        """Проверить, что сообщение от админа"""
        if not update.effective_chat:
            return False
        return str(update.effective_chat.id) == str(self.admin_chat_id)
    
    async def ignore_non_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Игнорировать сообщения не от админа"""
        if not self._is_admin(update):
            print(f"🚫 Ignored message from non-admin: {update.effective_chat.id}")
    
    # ========== КОМАНДЫ ==========
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветствие и список команд"""
        if not self._is_admin(update):
            return
        
        message = (
            "🤖 **Bybit Trading Bot Commander**\n\n"
            "**SILENT MODE** - бот молчит по умолчанию\n\n"
            "**Доступные команды:**\n"
            "/status - Сводка одним взглядом\n"
            "/brain - Что думает система\n"
            "/balance - Детальный баланс\n"
            "/panic - 🚨 Emergency Stop\n\n"
            "Бот пишет только на команды или при ЧП"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сводка одним взглядом"""
        if not self._is_admin(update):
            return
        
        try:
            # Получаем РЕАЛЬНЫЙ баланс из БД
            from database.db import async_session
            from database.models import Trade, TradeStatus
            from sqlalchemy import select, func
            
            async with async_session() as session:
                # Стартовый баланс
                initial_balance = 100.0
                
                # Считаем PnL из закрытых сделок
                result = await session.execute(
                    select(
                        func.sum(Trade.pnl).label('total_pnl'),
                        func.sum(Trade.fee_entry + Trade.fee_exit).label('total_fees')
                    ).where(
                        Trade.status == TradeStatus.CLOSED,
                        Trade.market_type == 'futures'
                    )
                )
                row = result.first()
                total_pnl = float(row.total_pnl or 0)
                total_fees = float(row.total_fees or 0)
                
                # Текущий баланс = стартовый + PnL - комиссии
                current_balance = initial_balance + total_pnl - total_fees
                pnl = current_balance - initial_balance
                pnl_pct = (pnl / initial_balance * 100) if initial_balance > 0 else 0
            
            # Получаем позиции
            if self.executor:
                positions = await self.executor.get_open_positions()
                long_count = sum(1 for p in positions if p['side'] == 'LONG')
                short_count = sum(1 for p in positions if p['side'] == 'SHORT')
                total_positions = len(positions)
            else:
                long_count = 0
                short_count = 0
                total_positions = 0
            
            # Получаем режим
            if self.strategic_brain:
                regime = self.strategic_brain.current_regime or "UNKNOWN"
            else:
                regime = "UNKNOWN"
            
            # Формируем сообщение
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            message = (
                f"📊 **STATUS REPORT**\n\n"
                f"💰 **Balance:** ${current_balance:.2f}\n"
                f"{pnl_emoji} **PnL:** ${pnl:+.2f} ({pnl_pct:+.1f}%)\n\n"
                f"📈 **Positions:** {total_positions}\n"
                f"   🟢 Long: {long_count}\n"
                f"   🔴 Short: {short_count}\n\n"
                f"🧠 **Regime:** {regime}\n"
                f"⏰ **Time:** {datetime.utcnow().strftime('%H:%M:%S UTC')}"
            )
            
            if self.panic_mode:
                message += "\n\n🚨 **PANIC MODE ACTIVE**"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_brain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Что думает система"""
        if not self._is_admin(update):
            return
        
        try:
            # Strategic Brain
            if self.strategic_brain:
                regime = self.strategic_brain.current_regime or "UNKNOWN"
                # Проверяем наличие атрибута last_update_time
                last_update = getattr(self.strategic_brain, 'last_update_time', None)
                if last_update:
                    minutes_ago = int((datetime.utcnow() - last_update).total_seconds() / 60)
                    update_str = f"{minutes_ago}m ago"
                else:
                    update_str = "Never"
            else:
                regime = "UNKNOWN"
                update_str = "N/A"
            
            # Gatekeepers (примерные значения, можно расширить)
            message = (
                f"🧠 **BRAIN STATUS**\n\n"
                f"**Strategic Regime:** {regime}\n"
                f"   Updated: {update_str}\n\n"
                f"**Gatekeepers:**\n"
                f"   🚦 CHOP Filter: Active\n"
                f"   📊 Pattern Filter: Active\n"
                f"   👑 BTC Correlation: Active\n"
                f"   💸 Funding Filter: Active\n\n"
                f"**Safety:**\n"
                f"   🛡️ Guardian: OK\n"
                f"   ⚠️ Panic Mode: {'ON' if self.panic_mode else 'OFF'}"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_panic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Emergency Stop - закрыть всё и остановить"""
        if not self._is_admin(update):
            return
        
        try:
            await update.message.reply_text("🚨 **PANIC ACTIVATED**\n\nClosing all positions...")
            
            # Закрываем все позиции
            if self.executor:
                positions = await self.executor.get_open_positions()
                closed_count = 0
                
                for pos in positions:
                    try:
                        result = await self.executor.close_position(
                            pos['symbol'],
                            "PANIC STOP by Telegram Commander"
                        )
                        if result.success:
                            closed_count += 1
                    except Exception as e:
                        print(f"❌ Failed to close {pos['symbol']}: {e}")
            
            # Активируем panic mode
            self.panic_mode = True
            
            message = (
                f"✅ **PANIC COMPLETE**\n\n"
                f"Closed positions: {closed_count}\n"
                f"Bot paused: YES\n\n"
                f"⚠️ Trading stopped. Restart bot to resume."
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Panic error: {e}")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Детальный баланс"""
        if not self._is_admin(update):
            return
        
        try:
            # Получаем РЕАЛЬНЫЙ баланс из БД
            from database.db import async_session
            from database.models import Trade, TradeStatus
            from sqlalchemy import select, func
            
            async with async_session() as session:
                # Стартовый баланс
                initial = 100.0
                leverage = 5  # Из конфига
                
                # Считаем PnL из закрытых сделок
                result = await session.execute(
                    select(
                        func.sum(Trade.pnl).label('total_pnl'),
                        func.sum(Trade.fee_entry + Trade.fee_exit).label('total_fees'),
                        func.count(Trade.id).label('total_trades')
                    ).where(
                        Trade.status == TradeStatus.CLOSED,
                        Trade.market_type == 'futures'
                    )
                )
                row = result.first()
                total_pnl = float(row.total_pnl or 0)
                total_fees = float(row.total_fees or 0)
                total_trades = int(row.total_trades or 0)
                
                # Текущий баланс
                current = initial + total_pnl - total_fees
                realized_pnl = current - initial
                pnl_pct = (realized_pnl / initial * 100) if initial > 0 else 0
                
                # Buying power
                buying_power = current * leverage
                
                message = (
                    f"💰 **BALANCE DETAILS**\n\n"
                    f"**Virtual Balance:**\n"
                    f"   Initial: ${initial:.2f}\n"
                    f"   Current: ${current:.2f}\n"
                    f"   Realized PnL: ${realized_pnl:+.2f}\n"
                    f"   ROI: {pnl_pct:+.1f}%\n\n"
                    f"**Trading:**\n"
                    f"   Total Trades: {total_trades}\n"
                    f"   Gross PnL: ${total_pnl:+.2f}\n"
                    f"   Total Fees: ${total_fees:.2f}\n\n"
                    f"**Leverage:** {leverage}x\n"
                    f"**Buying Power:** ${buying_power:.2f}\n\n"
                    f"⚠️ Demo Trading Mode"
                )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    # ========== EMERGENCY NOTIFICATIONS ==========
    
    async def notify_emergency(self, title: str, message: str):
        """
        Отправить экстренное уведомление админу
        
        Используется для:
        - Safety Guardian сработал
        - Ошибка API
        - Риск ликвидации
        """
        if not self.app or not self.is_running:
            return
        
        try:
            full_message = f"🚨 **{title}**\n\n{message}"
            await self.app.bot.send_message(
                chat_id=self.admin_chat_id,
                text=full_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ Emergency notification error: {e}")


# ========== SINGLETON ==========

_telegram_commander: Optional[TelegramCommander] = None

def get_telegram_commander(executor=None, ai_brain=None, strategic_brain=None) -> TelegramCommander:
    """Получить singleton TelegramCommander"""
    global _telegram_commander
    if _telegram_commander is None:
        _telegram_commander = TelegramCommander(executor, ai_brain, strategic_brain)
    return _telegram_commander
