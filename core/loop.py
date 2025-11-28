"""
Главный цикл Bybit Trading Bot
"""
import asyncio
from datetime import datetime
from typing import Dict, List
from database.db import init_db, async_session
from database.models import SystemLog, LogLevel, TradeSide
from core.bybit_api import get_bybit_api
from core.technical_analyzer import get_technical_analyzer
from core.ai_brain_local import get_local_brain  # Local Brain (полностью автономный)
from core.real_trader import get_real_trader  # РЕАЛЬНЫЙ ТРЕЙДЕР! 🚀
from core.data_collector import get_data_collector
from core.ml_predictor import get_ml_predictor  # LSTM модель
from core.telegram_notifier import get_telegram_notifier
from core.spot_position_manager import get_spot_position_manager  # SPOT менеджер
from config import settings, STRATEGY_CONFIGS


class TradingLoop:
    """Главный цикл торговли"""
    
    def __init__(self):
        self.bybit_api = get_bybit_api()
        self.technical_analyzer = get_technical_analyzer()
        self.ai_brain = get_local_brain()  # Используем Local Brain (автономный)
        self.trader = get_real_trader()  # РЕАЛЬНЫЙ ТРЕЙДЕР! 🚀
        self.data_collector = get_data_collector()
        self.ml_predictor = get_ml_predictor()  # LSTM модель
        self.telegram = get_telegram_notifier()
        self.spot_manager = get_spot_position_manager()  # SPOT менеджер
        
        self.running = False
        self.cycle_count = 0
    
    async def log(self, level: LogLevel, message: str, extra_data: Dict = None):
        """Логирование в БД"""
        async with async_session() as session:
            log = SystemLog(
                level=level,
                component="TradingLoop",
                message=message,
                extra_data=extra_data
            )
            session.add(log)
            await session.commit()
    
    async def analyze_market(self, symbol: str) -> Dict:
        """
        Анализ рынка: технический анализ + AI + ML прогноз
        
        Returns:
            {
                "symbol": "BTCUSDT",
                "technical": {...},
                "ai": {...},
                "ml_prediction": {...},
                "final_decision": "BUY/SELL/SKIP"
            }
        """
        print(f"\n📊 Analyzing {symbol}...")
        
        # 1. Получаем свечи (последние 200 минут)
        candles = await self.bybit_api.get_klines(symbol, "1", limit=200)
        
        if not candles or len(candles) < 50:
            print(f"❌ Not enough data for {symbol}")
            return {"error": "Not enough data"}
        
        # 1.1. Сохраняем свечи в БД для обучения
        await self.data_collector.save_candles(symbol, "1", candles)
        
        # 2. Технический анализ
        technical = self.technical_analyzer.analyze_market(candles)
        
        if "error" in technical:
            print(f"❌ Technical analysis failed: {technical['error']}")
            return technical
        
        print(f"   Price: ${technical['price']:.2f}")
        print(f"   RSI: {technical['rsi']:.1f}")
        print(f"   MACD: {technical['macd']['trend']}")
        print(f"   BB: {technical['bollinger_bands']['position']}")
        print(f"   Trend: {technical['trend']}")
        print(f"   Technical Signal: {technical['signal']}")
        
        # 3. Smart AI анализ (ML Gatekeeper)
        market_data = {
            "symbol": symbol,
            "price": technical['price'],
            "rsi": technical['rsi'],
            "macd": technical['macd'],
            "bollinger_bands": technical['bollinger_bands'],
            "trend": technical['trend'],
            "volume_trend": technical['volume_trend'],
            "technical_signal": technical['signal'],
            "klines": candles  # Добавляем свечи для ML модели
        }
        
        ai_analysis = await self.ai_brain.decide_trade(market_data)
        
        if not ai_analysis:
            print(f"❌ Smart AI analysis failed")
            return {"error": "Smart AI analysis failed"}
        
        print(f"   🧠 Decision: {ai_analysis['decision']}")
        print(f"   📊 Source: {ai_analysis['source']}")
        print(f"   🎯 Confidence: {ai_analysis['confidence']:.0%}")
        print(f"   ⚠️  Risk: {ai_analysis['risk_score']}/10")
        print(f"   💡 Reasoning: {ai_analysis['reasoning']}")
        
        # Финальное решение уже принято Smart AI Brain
        final_decision = ai_analysis['decision']
        
        # ML prediction из ai_analysis (если есть)
        ml_prediction = ai_analysis.get('ml_prediction', None)
        
        return {
            "symbol": symbol,
            "technical": technical,
            "ai": ai_analysis,
            "ml_prediction": ml_prediction,
            "final_decision": final_decision
        }
    
    async def execute_trade(self, analysis: Dict):
        """
        Выполнить сделку на основе анализа
        """
        symbol = analysis['symbol']
        decision = analysis['final_decision']
        
        if decision == "SKIP":
            return
        
        # PANIC_SELL - закрываем все позиции немедленно!
        if decision == "PANIC_SELL":
            print(f"🚨 PANIC SELL triggered! Closing all positions...")
            await self.telegram.send_message(
                f"🚨 PANIC SELL!\n"
                f"Причина: {analysis['ai']['reasoning']}\n"
                f"Закрываем все позиции!"
            )
            await self.spot_manager.close_all_positions(self.telegram)
            return
        
        # SPOT торговля - нет лимита на позиции
        # Проверяем риск
        ai_risk = analysis['ai']['risk_score']
        ai_confidence = analysis['ai']['confidence']
        
        # Получаем текущую стратегию (более агрессивная)
        strategy = STRATEGY_CONFIGS['aggressive']
        
        if ai_risk > strategy['max_risk']:
            print(f"⚠️ Риск слишком высокий: {ai_risk} > {strategy['max_risk']}")
            return
        
        if ai_confidence < strategy['min_confidence']:
            print(f"⚠️ Уверенность слишком низкая: {ai_confidence:.0%} < {strategy['min_confidence']:.0%}")
            return
        
        # Рассчитываем размер позиции
        balance = await self.trader.get_balance()
        position_size_usd = balance * (strategy['position_size_pct'] / 100)
        
        # Применяем multiplier из Smart AI (Safety Mode = 0.5)
        position_multiplier = analysis['ai'].get('position_size_multiplier', 1.0)
        position_size_usd *= position_multiplier
        
        if position_multiplier < 1.0:
            print(f"⚠️ Safety Mode: Position size reduced to {position_multiplier:.0%}")
        
        # Получаем текущую цену
        ticker = await self.bybit_api.get_ticker(symbol)
        if not ticker:
            print(f"❌ Failed to get ticker for {symbol}")
            return
        
        current_price = ticker['last_price']
        quantity = position_size_usd / current_price
        
        # Округляем количество (для BTC - 4 знака, для ETH - 3 знака)
        if symbol == "BTCUSDT":
            quantity = round(quantity, 4)
        else:
            quantity = round(quantity, 3)
        
        # Открываем сделку
        side = TradeSide.BUY if decision == "BUY" else TradeSide.SELL
        
        trade = await self.trader.open_trade(
            symbol=symbol,
            side=side,
            entry_price=current_price,
            quantity=quantity,
            ai_risk_score=ai_risk,
            ai_reasoning=analysis['ai']['reasoning'],
            extra_data={
                "strategy": "balanced",
                "technical_signal": analysis['technical']['signal'],
                "rsi": analysis['technical']['rsi'],
                "macd_trend": analysis['technical']['macd']['trend'],
                "bb_position": analysis['technical']['bollinger_bands']['position'],
                "ml_prediction": analysis.get('ml_prediction')
            }
        )
        
        if trade:
            await self.log(
                LogLevel.BUY if side == TradeSide.BUY else LogLevel.SELL,
                f"Opened {side.value} {symbol} @ ${current_price:.2f}",
                {"trade_id": trade.id, "analysis": analysis}
            )
            
            # Telegram уведомление
            await self.telegram.notify_position_opened({
                "symbol": symbol,
                "side": side.value,
                "entry_price": current_price,
                "quantity": quantity,
                "cost": current_price * quantity,
                "take_profit": trade.take_profit,
                "stop_loss": trade.stop_loss,
                "ai_risk": ai_risk,
                "ai_reasoning": analysis['ai']['reasoning']
            })
    
    async def check_positions(self):
        """Проверить открытые позиции (Stop Loss / Take Profit) для SPOT"""
        # Используем SPOT менеджер для проверки и закрытия позиций
        await self.spot_manager.check_and_close_positions(self.telegram)
    
    async def cycle(self):
        """Один цикл торговли"""
        self.cycle_count += 1
        
        print("\n" + "="*80)
        print(f"🔄 Trading Cycle #{self.cycle_count} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("="*80)
        
        try:
            # 1. Проверяем открытые позиции
            await self.check_positions()
            
            # 2. Показываем статистику
            balance = await self.trader.get_balance()
            open_trades = await self.trader.get_open_trades()
            stats = await self.trader.get_statistics()
            
            print(f"\n💰 Balance: ${balance:.2f}")
            print(f"📊 Open Positions: {len(open_trades)}/{settings.max_open_positions}")
            print(f"📈 Total Trades: {stats['total_trades']} (Wins: {stats['wins']}, Losses: {stats['losses']})")
            if stats['total_trades'] > 0:
                print(f"🎯 Winrate: {stats['winrate']:.1f}%")
                print(f"💵 Total PnL: ${stats['total_pnl']:+.2f}")
            
            # 3. Анализируем рынки
            for symbol in settings.trading_pairs:
                analysis = await self.analyze_market(symbol)
                
                if "error" not in analysis:
                    await self.execute_trade(analysis)
                
                # Задержка между анализами
                await asyncio.sleep(2)
            
            # 4. Статистика AI Brain
            print("\n" + "="*80)
            self.ai_brain.print_stats()
            print("="*80)
            
            await self.log(LogLevel.INFO, f"Cycle #{self.cycle_count} completed")
            
        except Exception as e:
            print(f"❌ Error in cycle: {e}")
            await self.log(LogLevel.ERROR, f"Cycle error: {e}")
    
    async def run(self):
        """Запустить бота"""
        print("\n" + "="*80)
        print("🚀 Bybit Trading Bot Starting...")
        print("="*80)
        
        # Инициализация БД
        await init_db()
        
        # Показываем режим работы
        mode = "🎮 DEMO MODE (Testnet)" if settings.bybit_testnet else "💰 LIVE MODE (Mainnet)"
        print(f"\n🔧 Режим: {mode}")
        
        # Показываем конфигурацию
        print(f"\n⚙️ Конфигурация:")
        print(f"   Торговые пары: {', '.join(settings.trading_pairs)}")
        print(f"   Интервал сканирования: {settings.scan_interval} сек")
        print(f"   Макс. открытых позиций: {settings.max_open_positions}")
        print(f"   Stop Loss: {settings.stop_loss_pct}%")
        print(f"   Take Profit: {settings.take_profit_pct}%")
        print(f"   Начальный баланс: ${settings.initial_balance}")
        
        # Инициализация ML модели
        print(f"\n🤖 Загрузка LSTM модели...")
        ml_loaded = await self.ml_predictor.load_model()
        if ml_loaded:
            print(f"✅ LSTM модель загружена успешно!")
            print(f"   Model: {self.ml_predictor.model_path}")
            print(f"   Scalers: {self.ml_predictor.scaler_x_path}")
        else:
            print(f"⚠️  LSTM модель не загружена, используется fallback")
        
        # Проверяем баланс
        balance = await self.trader.get_balance()
        print(f"\n💰 Текущий баланс: ${balance:.2f}")
        
        self.running = True
        
        print(f"\n✅ Bot started! Running every {settings.scan_interval} seconds...")
        print("="*80)
        
        await self.log(LogLevel.INFO, "Bot started")
        
        # Telegram уведомление о запуске
        await self.telegram.notify_bot_started()
        
        # Главный цикл
        while self.running:
            try:
                await self.cycle()
                
                # Ждем до следующего цикла
                print(f"\n⏳ Waiting {settings.scan_interval} seconds until next cycle...")
                await asyncio.sleep(settings.scan_interval)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Stopping bot...")
                self.running = False
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                await self.log(LogLevel.ERROR, f"Unexpected error: {e}")
                await asyncio.sleep(10)
        
        await self.log(LogLevel.INFO, "Bot stopped")
        print("\n✅ Bot stopped")


async def main():
    """Точка входа"""
    loop = TradingLoop()
    await loop.run()


if __name__ == "__main__":
    asyncio.run(main())
