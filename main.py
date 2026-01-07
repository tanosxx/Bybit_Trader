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
from core.executors.simple_executor import get_simple_executor
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
        self.executor = get_simple_executor()
        
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
        
        print("✅ Bot initialized successfully")
    
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
                
                # 3. Проверить статус позиций (закрылись ли по TP/SL)
                await self.executor.check_positions()
                
                # 4. Сканировать рынки на сигналы
                print("\n🔍 Scanning markets...")
                signals = await self.strategy.scan_markets()
                
                if signals:
                    self.signals_found += len(signals)
                    print(f"✅ Found {len(signals)} signal(s)")
                    
                    # 5. Исполнить сигналы
                    for signal in signals:
                        # Проверяем лимит позиций
                        if len(positions) >= settings.futures_max_open_positions:
                            print(f"⚠️ Max positions reached ({settings.futures_max_open_positions}), skipping signal")
                            continue
                        
                        # Рассчитываем размер позиции
                        quantity = self.strategy.calculate_position_size(
                            balance=balance,
                            price=signal['price'],
                            leverage=settings.futures_leverage
                        )
                        
                        # Размещаем ордер
                        print(f"\n📤 Executing {signal['signal']} signal...")
                        
                        result = await self.executor.open_position(
                            symbol=signal['symbol'],
                            side=signal['signal'],
                            price=signal['price'],
                            quantity=quantity,
                            reason=signal['reason']
                        )
                        
                        if result:
                            self.trades_executed += 1
                            print("✅ Position opened successfully")
                        else:
                            print("❌ Position opening failed")
                else:
                    print("⏸️  No signals found")
                
                # 6. Статистика
                print("\n📊 SESSION STATS:")
                print(f"   Cycles: {self.cycle_count}")
                print(f"   Signals Found: {self.signals_found}")
                print(f"   Trades Executed: {self.trades_executed}")
                print("=" * 80)
                
                # 7. Ждём следующего цикла
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
