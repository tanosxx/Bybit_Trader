"""
Bybit Trading Bot v2.0 - Simple Profit Edition

Философия: Простота = Прибыль
Без ML, без агентов, без сложности.

Стратегия: RSI Grid (Mean Reversion)
- Покупаем на перепроданности
- Продаём на перекупленности
- Фиксированные TP/SL
"""
import asyncio
from datetime import datetime
from typing import Optional

from core.strategies.simple_scalper import get_simple_scalper
from core.executors.futures_executor import FuturesExecutor
from core.telegram_commander_v2 import get_telegram_commander
from config_v2 import settings


class SimpleTradingBot:
    """
    Простой торговый бот
    
    Компоненты:
    - SimpleScalper: Стратегия RSI Grid
    - SimpleExecutor: Исполнение ордеров
    - TelegramCommander: Управление через Telegram (опционально)
    """
    
    def __init__(self):
        """Инициализация бота"""
        print("=" * 80)
        print("🚀 BYBIT TRADING BOT v2.0 - SIMPLE PROFIT EDITION")
        print("=" * 80)
        print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Mode: {'TESTNET' if settings.bybit_testnet else 'MAINNET'}")
        print(f"   Strategy: RSI Grid (Mean Reversion)")
        print("=" * 80)
        
        # Инициализация компонентов
        self.strategy = get_simple_scalper()
        self.executor = FuturesExecutor()
        
        # Telegram Commander (опционально)
        try:
            self.commander = get_telegram_commander(executor=self.executor)
        except Exception as e:
            print(f"⚠️ Telegram Commander disabled: {e}")
            self.commander = None
        
        # Статистика
        self.cycle_count = 0
        self.signals_found = 0
        self.trades_executed = 0
        self.last_sync_time = datetime.now()
        
        print("✅ Bot initialized successfully")
    
    async def sync_positions(self):
        """
        Heartbeat Sync - Синхронизация позиций с биржей
        
        Логика:
        1. Получаем реальные позиции с биржи
        2. Получаем позиции из БД
        3. Сравниваем и синхронизируем:
           - Если на бирже НЕТ, а в БД ЕСТЬ → Закрываем в БД (TP/SL сработал)
           - Если на бирже ЕСТЬ, а в БД НЕТ → Игнорируем (открыто вручную)
        """
        try:
            print("🔄 Syncing positions with exchange...")
            
            # 1. Получаем позиции с биржи (async!)
            exchange_positions_list = await self.executor.api.get_positions(category="linear")
            
            # Преобразуем в dict для удобства
            exchange_positions = {}
            for pos in exchange_positions_list:
                if pos["size"] > 0:
                    exchange_positions[pos["symbol"]] = pos
            
            # 2. Получаем позиции из БД
            db_positions = await self.executor.get_open_positions()
            db_symbols = {pos["symbol"] for pos in db_positions}
            
            # 3. Находим "фантомные" позиции (есть в БД, но нет на бирже)
            phantom_symbols = db_symbols - set(exchange_positions.keys())
            
            if phantom_symbols:
                print(f"👻 Found {len(phantom_symbols)} phantom position(s): {', '.join(phantom_symbols)}")
                
                # Закрываем фантомные позиции в БД
                for symbol in phantom_symbols:
                    # Находим позицию в БД
                    pos = next((p for p in db_positions if p["symbol"] == symbol), None)
                    if pos:
                        print(f"   Closing phantom position: {symbol}")
                        await self.executor.close_position_in_db(
                            symbol=symbol,
                            exit_price=pos["entry_price"],  # Используем entry price как exit
                            reason="Closed on exchange (TP/SL triggered)"
                        )
            else:
                print("✅ All positions synced")
            
            # 4. ЗАКРЫВАЕМ позиции открытые вручную (есть на бирже, но нет в БД)
            manual_symbols = set(exchange_positions.keys()) - db_symbols
            if manual_symbols:
                print(f"🚨 Found {len(manual_symbols)} UNAUTHORIZED position(s): {', '.join(manual_symbols)}")
                print("   🔴 CLOSING IMMEDIATELY (not managed by bot)...")
                
                # Закрываем каждую неуправляемую позицию
                for symbol in manual_symbols:
                    try:
                        pos = exchange_positions[symbol]
                        side = pos["side"]  # "Buy" или "Sell"
                        size = pos["size"]
                        
                        # Определяем противоположную сторону для закрытия
                        close_side = "Sell" if side == "Buy" else "Buy"
                        
                        print(f"   🔴 Closing {symbol} {side} {size}...")
                        
                        result = await self.executor.api.place_futures_order(
                            symbol=symbol,
                            side=close_side,
                            order_type="Market",
                            qty=size,
                            reduce_only=True
                        )
                        
                        if result:
                            print(f"   ✅ {symbol} closed successfully")
                        else:
                            print(f"   ❌ Failed to close {symbol}")
                    except Exception as e:
                        print(f"   ❌ Error closing {symbol}: {e}")
            
        except Exception as e:
            print(f"❌ Sync error: {e}")
    
    async def run(self):
        """Основной цикл бота"""
        print("\n🔄 Starting main trading loop...")
        print(f"   Scan interval: {settings.scan_interval_seconds}s")
        print(f"   Symbols: {', '.join(settings.futures_pairs)}")
        print()
        
        # Загружаем баланс из БД
        await self.executor.load_balance_from_db()
        
        # Запускаем Telegram Commander в фоне
        if self.commander:
            commander_task = asyncio.create_task(self.commander.start())
            print("✅ Telegram Commander started in background")
        
        try:
            while True:
                self.cycle_count += 1
                
                print("=" * 80)
                print(f"🔄 CYCLE #{self.cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print("=" * 80)
                
                # 1. Получить текущий баланс
                balance = await self.executor.get_balance()
                print(f"💰 Balance: ${balance:.2f}")
                
                # 2. Проверить открытые позиции
                positions = await self.executor.get_open_positions()
                print(f"📊 Open Positions: {len(positions)}")
                
                if positions:
                    for pos in positions:
                        print(f"   {pos['symbol']}: {pos['side']} @ {pos['entry_price']:.2f}")
                
                # 3. Синхронизация с биржей (каждые 30 секунд)
                if (datetime.now() - self.last_sync_time).total_seconds() >= settings.sync_positions_interval:
                    await self.sync_positions()
                    self.last_sync_time = datetime.now()
                
                # 4. Проверить статус позиций (закрылись ли по TP/SL)
                print("🔍 Checking TP/SL...")
                closed_positions = await self.executor.check_and_close_sl_tp()
                if closed_positions:
                    for pos in closed_positions:
                        print(f"   ✅ Closed {pos['symbol']} {pos['side']}: {pos['reason']} (PnL: ${pos.get('pnl', 0):+.2f})")
                else:
                    print("   ⏸️  No positions hit TP/SL")
                
                # 5. Сканировать рынки на сигналы
                print("\n🔍 Scanning markets...")
                signals = await self.strategy.scan_markets()
                
                if signals:
                    self.signals_found += len(signals)
                    print(f"✅ Found {len(signals)} signal(s)")
                    
                    # 6. Исполнить сигналы
                    for signal in signals:
                        # Проверяем лимит позиций
                        if len(positions) >= settings.futures_max_open_positions:
                            print(f"⚠️ Max positions reached ({settings.futures_max_open_positions}), skipping signal")
                            continue
                        
                        # Создаём TradeSignal объект для FuturesExecutor
                        from core.executors.base_executor import TradeSignal
                        
                        # Преобразуем LONG/SHORT в BUY/SELL
                        action = "BUY" if signal['signal'] in ['BUY', 'LONG'] else "SELL"
                        
                        trade_signal = TradeSignal(
                            symbol=signal['symbol'],
                            action=action,  # BUY или SELL
                            price=signal['price'],
                            confidence=0.75,  # RSI + EMA + ADX имеет высокую уверенность
                            risk_score=3,  # Средний риск
                            reasoning=signal['reason']
                        )
                        
                        # Размещаем ордер через execute_signal
                        print(f"\n📤 Executing {signal['signal']} signal for {signal['symbol']}...")
                        
                        result = await self.executor.execute_signal(trade_signal)
                        
                        if result.success:
                            self.trades_executed += 1
                            print("✅ Position opened successfully")
                        else:
                            print(f"❌ Position opening failed: {result.error}")
                else:
                    print("⏸️  No signals found")
                
                # 7. Статистика
                print("\n📊 SESSION STATS:")
                print(f"   Cycles: {self.cycle_count}")
                print(f"   Signals Found: {self.signals_found}")
                print(f"   Trades Executed: {self.trades_executed}")
                print("=" * 80)
                
                # 8. Ждём следующего цикла
                print(f"\n⏳ Waiting {settings.scan_interval_seconds}s...\n")
                await asyncio.sleep(settings.scan_interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"\n\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Останавливаем Telegram Commander
            if self.commander:
                try:
                    await self.commander.stop()
                except Exception as e:
                    print(f"⚠️ Commander stop error: {e}")


async def main():
    """Entry point"""
    bot = SimpleTradingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
