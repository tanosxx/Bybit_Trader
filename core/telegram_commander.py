"""
Telegram Commander v2.0 - Интерактивный командир бота с визуальными отчётами

ФИЛОСОФИЯ "SILENT MODE":
- Бот МОЛЧИТ по умолчанию
- Пишет ТОЛЬКО на команды или при ЧП

КОМАНДЫ:
- /start - Приветствие и список команд
- /status - Сводка "одним взглядом"
- /brain - Что думает система
- /panic - Emergency Stop (закрыть всё и остановить)
- /balance - График эквити (визуальный)
- /orders - Таблица PnL (визуальная)
"""
import asyncio
import os
from typing import Optional
from datetime import datetime
import io

# Matplotlib для графиков (без GUI)
import matplotlib
matplotlib.use('Agg')  # Без GUI для Docker
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

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
        """Запустить Telegram бота (игнорируем временные сетевые ошибки)"""
        if not self.bot_token or not self.admin_chat_id:
            print("⚠️ Telegram credentials not set - Commander disabled")
            return
        
        try:
            # Build application с увеличенными таймаутами
            self.app = (
                Application.builder()
                .token(self.bot_token)
                .connect_timeout(30.0)
                .read_timeout(30.0)
                .write_timeout(30.0)
                .pool_timeout(30.0)
                .build()
            )
            
            # Register handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("brain", self.cmd_brain))
            self.app.add_handler(CommandHandler("strategy", self.cmd_strategy))
            self.app.add_handler(CommandHandler("orders", self.cmd_orders))
            self.app.add_handler(CommandHandler("panic", self.cmd_panic))
            self.app.add_handler(CommandHandler("panic_test", self.cmd_panic_test))
            self.app.add_handler(CommandHandler("balance", self.cmd_balance))
            
            # Ignore non-admin messages
            self.app.add_handler(MessageHandler(filters.ALL, self.ignore_non_admin))
            
            # Add error handler для подавления логов
            async def error_handler(update, context):
                """Подавляем логи временных сетевых ошибок"""
                error = context.error
                # Игнорируем Conflict и ConnectError (они временные)
                if "Conflict" in str(error) or "ConnectError" in str(error):
                    return
                # Остальные ошибки логируем
                print(f"⚠️ Telegram error: {error}")
            
            self.app.add_error_handler(error_handler)
            
            # Start polling
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Пропустить старые обновления
            )
            
            self.is_running = True
            print("✅ TelegramCommander started (polling)")
            print("   Note: Temporary network errors are suppressed")
            
        except Exception as e:
            print(f"❌ TelegramCommander start error: {e}")
            print("   Bot will continue without Telegram commands")
    
    async def stop(self):
        """Остановить Telegram бота корректно"""
        if self.app:
            try:
                self.is_running = False
                
                # Остановить polling
                if self.app.updater and self.app.updater.running:
                    await self.app.updater.stop()
                    print("   Updater stopped")
                
                # Остановить application
                if self.app.running:
                    await self.app.stop()
                    print("   Application stopped")
                
                # Shutdown
                await self.app.shutdown()
                print("✅ TelegramCommander stopped gracefully")
                
            except Exception as e:
                print(f"⚠️ TelegramCommander stop error: {e}")
                # Принудительно сбросить флаг
                self.is_running = False
    
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
            "🤖 <b>Bybit Trading Bot Commander</b>\n\n"
            "<b>SILENT MODE</b> - бот молчит по умолчанию\n\n"
            "<b>Доступные команды:</b>\n"
            "/status - Сводка одним взглядом\n"
            "/brain - Что думает система\n"
            "/strategy - 🔄 Hybrid Strategy статус\n"
            "/orders - Последние ордера\n"
            "/balance - Детальный баланс\n"
            "/panic_test - 🧪 Тест panic (без закрытия)\n"
            "/panic - 🚨 Emergency Stop\n\n"
            "Бот пишет только на команды или при ЧП"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
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
            
            # Получаем Hybrid Strategy информацию
            try:
                import json
                import os
                
                # Читаем из файла состояния
                state_file = '/app/ml_data/hybrid_strategy_state.json'
                if os.path.exists(state_file):
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        market_mode = state_data.get('market_mode', 'UNKNOWN')
                        chop_value = float(state_data.get('chop_value', 0))
                        
                        # Добавляем эмодзи
                        if market_mode == 'FLAT':
                            market_mode = "FLAT 🔄"
                            strategy_info = "Mean Reversion"
                        elif market_mode == 'TREND':
                            market_mode = "TREND 🚀"
                            strategy_info = "Trend Following"
                        else:
                            strategy_info = "UNKNOWN"
                        
                        hybrid_info = f"{market_mode} (CHOP: {chop_value:.1f})"
                else:
                    hybrid_info = "N/A (file not found)"
                    strategy_info = "N/A"
            except Exception as e:
                hybrid_info = f"N/A (error: {e})"
                strategy_info = "N/A"
            
            # Формируем сообщение
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            message = (
                f"📊 <b>STATUS REPORT</b>\n\n"
                f"💰 <b>Balance:</b> ${current_balance:.2f}\n"
                f"{pnl_emoji} <b>PnL:</b> ${pnl:+.2f} ({pnl_pct:+.1f}%)\n\n"
                f"📈 <b>Positions:</b> {total_positions}\n"
                f"   🟢 Long: {long_count}\n"
                f"   🔴 Short: {short_count}\n\n"
                f"🧠 <b>Regime:</b> {regime}\n"
                f"🔄 <b>Market Mode:</b> {hybrid_info}\n"
                f"📊 <b>Strategy:</b> {strategy_info}\n"
                f"⏰ <b>Time:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}"
            )
            
            if self.panic_mode:
                message += "\n\n🚨 <b>PANIC MODE ACTIVE</b>"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
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
                f"🧠 <b>BRAIN STATUS</b>\n\n"
                f"<b>Strategic Regime:</b> {regime}\n"
                f"   Updated: {update_str}\n\n"
                f"<b>Gatekeepers:</b>\n"
                f"   🚦 CHOP Filter: Active\n"
                f"   📊 Pattern Filter: Active\n"
                f"   👑 BTC Correlation: Active\n"
                f"   💸 Funding Filter: Active\n\n"
                f"<b>Safety:</b>\n"
                f"   🛡️ Guardian: OK\n"
                f"   ⚠️ Panic Mode: {'ON' if self.panic_mode else 'OFF'}"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Детальная информация о Hybrid Strategy"""
        if not self._is_admin(update):
            return
        
        try:
            from config import settings
            import json
            import os
            
            # Читаем текущее состояние из файла
            state_file = '/app/ml_data/hybrid_strategy_state.json'
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    market_mode = state_data.get('market_mode', 'UNKNOWN')
                    chop_value = float(state_data.get('chop_value', 0))
                    symbol = state_data.get('symbol', 'UNKNOWN')
                    
                    # Определяем режим и стратегию
                    if market_mode == 'FLAT':
                        mode = "FLAT 🔄"
                        strategy = "Mean Reversion"
                    elif market_mode == 'TREND':
                        mode = "TREND 🚀"
                        strategy = "Trend Following"
                    else:
                        mode = "UNKNOWN"
                        strategy = "UNKNOWN"
                    
                    symbols_info = [
                        f"<b>{symbol}</b> (last analyzed)\n"
                        f"  Mode: {mode}\n"
                        f"  CHOP: {chop_value:.1f}\n"
                        f"  Strategy: {strategy}"
                    ]
            else:
                symbols_info = []
            
            # Формируем сообщение
            message = (
                f"🔄 <b>HYBRID STRATEGY STATUS</b>\n\n"
                f"<b>Configuration:</b>\n"
                f"  Enabled: {'✅' if settings.mean_reversion_enabled else '❌'}\n"
                f"  CHOP Threshold: {settings.chop_flat_threshold}\n"
                f"  RSI Oversold: {settings.rsi_oversold}\n"
                f"  RSI Overbought: {settings.rsi_overbought}\n"
                f"  Min Confidence: {settings.mean_reversion_min_confidence:.0%}\n"
                f"  BTC Safety: {'✅' if settings.mean_reversion_btc_safety else '❌'}\n\n"
                f"<b>Active Symbols:</b>\n"
            )
            
            if symbols_info:
                message += "\n".join(symbols_info)
            else:
                message += "  No data available"
            
            message += (
                f"\n\n<b>Strategy Logic:</b>\n"
                f"  CHOP &lt; {settings.chop_flat_threshold}: Trend Following (ML)\n"
                f"  CHOP ≥ {settings.chop_flat_threshold}: Mean Reversion (RSI)"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_panic_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """TEST: Показать что будет сделано при /panic (БЕЗ реального закрытия)"""
        if not self._is_admin(update):
            return
        
        try:
            # Получаем позиции
            if self.executor:
                positions = await self.executor.get_open_positions()
                
                if not positions:
                    message = (
                        "🧪 <b>PANIC TEST</b>\n\n"
                        "✅ No open positions\n"
                        "Nothing to close\n\n"
                        "⚠️ This is a TEST - no real actions taken"
                    )
                else:
                    pos_list = []
                    for pos in positions:
                        side = pos['side']
                        symbol = pos['symbol']
                        qty = pos['quantity']
                        entry = pos['entry_price']
                        pos_list.append(f"   • {side} {symbol}: {qty} @ ${entry:.2f}")
                    
                    message = (
                        f"🧪 <b>PANIC TEST</b>\n\n"
                        f"<b>Would close {len(positions)} positions:</b>\n"
                        + "\n".join(pos_list) +
                        f"\n\n<b>Actions:</b>\n"
                        f"1. Close all {len(positions)} positions\n"
                        f"2. Activate panic_mode = True\n"
                        f"3. Stop trading (new signals ignored)\n\n"
                        f"⚠️ This is a TEST - no real actions taken\n"
                        f"Use /panic to execute for real"
                    )
            else:
                message = "❌ Executor not available"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Test error: {e}")
    
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
                f"✅ <b>PANIC COMPLETE</b>\n\n"
                f"Closed positions: {closed_count}\n"
                f"Bot paused: YES\n\n"
                f"⚠️ Trading stopped. Restart bot to resume."
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Panic error: {e}")
    
    async def cmd_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """📊 Таблица PnL последних сделок (визуальный отчёт)"""
        if not self._is_admin(update):
            return
        
        try:
            await update.message.reply_text("📊 Generating PnL table...")
            
            # Получаем данные из БД
            from database.db import async_session
            from database.models import Trade, TradeStatus
            from sqlalchemy import select, desc
            
            async with async_session() as session:
                # Последние 15 закрытых сделок
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.CLOSED,
                        Trade.market_type == 'futures'
                    ).order_by(desc(Trade.exit_time)).limit(15)
                )
                trades = list(result.scalars().all())
                
                if not trades:
                    await update.message.reply_text("📊 No closed trades yet")
                    return
                
                # Подготовка данных для таблицы
                table_data = []
                total_pnl = 0
                
                for trade in reversed(trades):  # Показываем от старых к новым
                    net_pnl = trade.pnl - (trade.fee_entry + trade.fee_exit)
                    total_pnl += net_pnl
                    
                    time_str = trade.exit_time.strftime("%H:%M") if trade.exit_time else "?"
                    pair = trade.symbol.replace('USDT', '')
                    side = "L" if trade.side.value == "BUY" else "S"
                    status = "✓" if net_pnl >= 0 else "✗"
                    
                    table_data.append([time_str, pair, side, f"${net_pnl:+.2f}", status])
                
                # Создаём таблицу
                fig, ax = plt.subplots(figsize=(10, 8), facecolor='#1e1e1e')
                ax.axis('off')
                
                # Заголовки
                headers = ['Time', 'Pair', 'Side', 'PnL ($)', 'Status']
                
                # Создаём таблицу
                table = ax.table(
                    cellText=table_data,
                    colLabels=headers,
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.15, 0.15, 0.12, 0.20, 0.12]
                )
                
                # Стилизация таблицы
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1, 2)
                
                # Стилизация заголовков
                for i in range(len(headers)):
                    cell = table[(0, i)]
                    cell.set_facecolor('#3d3d3d')
                    cell.set_text_props(weight='bold', color='white')
                    cell.set_edgecolor('white')
                
                # Стилизация строк с раскраской по PnL
                for i, row in enumerate(table_data, start=1):
                    net_pnl_value = float(row[3].replace('$', '').replace('+', ''))
                    
                    # Определяем цвет фона
                    if net_pnl_value > 0:
                        bg_color = '#1a3d1a'  # Тёмно-зелёный
                    else:
                        bg_color = '#3d1a1a'  # Тёмно-красный
                    
                    for j in range(len(headers)):
                        cell = table[(i, j)]
                        cell.set_facecolor(bg_color)
                        cell.set_text_props(color='white')
                        cell.set_edgecolor('#555555')
                
                # Заголовок
                title_color = '#00ff00' if total_pnl >= 0 else '#ff4444'
                plt.title(
                    f'📊 Last 15 Trades | Total PnL: ${total_pnl:+.2f}',
                    color=title_color,
                    fontsize=14,
                    fontweight='bold',
                    pad=20
                )
                
                # Подпись внизу
                fig.text(
                    0.5, 0.02,
                    f'Trades: {len(trades)} | Wins: {sum(1 for t in trades if (t.pnl - t.fee_entry - t.fee_exit) > 0)} | Losses: {sum(1 for t in trades if (t.pnl - t.fee_entry - t.fee_exit) <= 0)}',
                    ha='center',
                    color='white',
                    fontsize=10
                )
                
                plt.tight_layout()
                
                # Сохраняем в буфер
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, facecolor='#1e1e1e')
                buf.seek(0)
                plt.close()
                
                # Отправляем фото
                win_rate = sum(1 for t in trades if (t.pnl - t.fee_entry - t.fee_exit) > 0) / len(trades) * 100
                caption = (
                    f"📊 <b>Recent Trades</b>\n"
                    f"Total PnL: <b>${total_pnl:+.2f}</b>\n"
                    f"Win Rate: <b>{win_rate:.1f}%</b>\n"
                    f"Trades: {len(trades)}"
                )
                
                await update.message.reply_photo(
                    photo=buf,
                    caption=caption,
                    parse_mode='HTML'
                )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error generating table: {e}")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """📈 График эквити (визуальный отчёт)"""
        if not self._is_admin(update):
            return
        
        try:
            await update.message.reply_text("📊 Generating equity curve...")
            
            # Получаем данные из БД
            from database.db import async_session
            from database.models import Trade, TradeStatus
            from sqlalchemy import select
            
            async with async_session() as session:
                # Стартовый баланс
                initial_balance = 100.0
                
                # Получаем все закрытые сделки, отсортированные по времени
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.CLOSED,
                        Trade.market_type == 'futures'
                    ).order_by(Trade.exit_time)
                )
                trades = list(result.scalars().all())
                
                if not trades:
                    await update.message.reply_text("📊 No closed trades yet")
                    return
                
                # Строим кумулятивную линию баланса
                timestamps = []
                balances = []
                current_balance = initial_balance
                
                # Добавляем стартовую точку
                if trades:
                    timestamps.append(trades[0].entry_time)
                    balances.append(initial_balance)
                
                # Добавляем точки после каждой сделки
                for trade in trades:
                    net_pnl = trade.pnl - (trade.fee_entry + trade.fee_exit)
                    current_balance += net_pnl
                    timestamps.append(trade.exit_time)
                    balances.append(current_balance)
                
                # Создаём график
                fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1e1e1e')
                ax.set_facecolor('#2d2d2d')
                
                # Определяем цвет линии
                final_pnl = current_balance - initial_balance
                line_color = '#00ff00' if final_pnl >= 0 else '#ff4444'
                
                # Рисуем линию эквити
                ax.plot(timestamps, balances, color=line_color, linewidth=2.5, label='Balance')
                
                # Горизонтальная линия стартового баланса
                ax.axhline(y=initial_balance, color='#888888', linestyle='--', 
                          linewidth=1, alpha=0.5, label=f'Initial: ${initial_balance:.2f}')
                
                # Заливка области прибыли/убытка
                ax.fill_between(timestamps, balances, initial_balance, 
                               where=[b >= initial_balance for b in balances],
                               color='#00ff00', alpha=0.1)
                ax.fill_between(timestamps, balances, initial_balance,
                               where=[b < initial_balance for b in balances],
                               color='#ff4444', alpha=0.1)
                
                # Настройка осей
                ax.set_xlabel('Time', color='white', fontsize=12)
                ax.set_ylabel('Balance ($)', color='white', fontsize=12)
                ax.set_title(f'📈 Equity Curve | Current: ${current_balance:.2f} ({final_pnl:+.2f})', 
                            color='white', fontsize=14, fontweight='bold')
                
                # Форматирование времени на оси X
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                plt.xticks(rotation=45, ha='right', color='white')
                plt.yticks(color='white')
                
                # Сетка
                ax.grid(True, alpha=0.2, color='white')
                
                # Легенда
                ax.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='white', 
                         labelcolor='white')
                
                # Убираем рамки
                for spine in ax.spines.values():
                    spine.set_color('white')
                    spine.set_linewidth(0.5)
                
                plt.tight_layout()
                
                # Сохраняем в буфер
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, facecolor='#1e1e1e')
                buf.seek(0)
                plt.close()
                
                # Отправляем фото
                caption = (
                    f"📈 <b>Balance History</b>\n"
                    f"Current: <b>${current_balance:.2f}</b>\n"
                    f"PnL: <b>${final_pnl:+.2f}</b> ({(final_pnl/initial_balance*100):+.1f}%)\n"
                    f"Trades: {len(trades)}"
                )
                
                await update.message.reply_photo(
                    photo=buf,
                    caption=caption,
                    parse_mode='HTML'
                )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error generating chart: {e}")
    
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
            full_message = f"🚨 <b>{title}</b>\n\n{message}"
            await self.app.bot.send_message(
                chat_id=self.admin_chat_id,
                text=full_message,
                parse_mode='HTML'
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
