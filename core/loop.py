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
from core.ta_lib import (  # DYNAMIC RISK MANAGEMENT 🎯
    get_dynamic_risk_manager, 
    get_portfolio_risk_manager,
    RiskLevel
)
from core.multi_agent import get_meta_agent  # MULTI-AGENT SYSTEM 🤖
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
        
        # DYNAMIC RISK MANAGEMENT 🎯
        self.risk_manager = get_dynamic_risk_manager()
        self.portfolio_manager = get_portfolio_risk_manager()
        
        # MULTI-AGENT SYSTEM 🤖
        self.meta_agent = get_meta_agent()
        self.use_multi_agent = True  # Включить/выключить Multi-Agent
        
        self.running = False
        self.cycle_count = 0
        self.daily_pnl = 0.0  # Отслеживаем дневной PnL
    
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
        Выполнить сделку на основе анализа с DYNAMIC RISK MANAGEMENT
        """
        symbol = analysis['symbol']
        decision = analysis['final_decision']
        klines = analysis.get('technical', {}).get('klines') or []
        
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
        
        # Получаем баланс и открытые позиции
        balance = await self.trader.get_balance()
        open_trades = await self.trader.get_open_trades()
        stats = await self.trader.get_statistics()
        
        # ========== MARKET REGIME CHECK 📊 ==========
        candles = await self.bybit_api.get_klines(symbol, "5", limit=100)  # 5-минутки для режима
        if candles:
            regime_check = self.risk_manager.get_trading_recommendation(candles)
            print(f"\n   📊 MARKET REGIME: {regime_check['regime'].value}")
            print(f"      Recommendation: {regime_check['recommendation'].value}")
            print(f"      Reason: {regime_check['reason']}")
            
            if not regime_check['can_trade']:
                print(f"   ⏭️ Skipping trade: {regime_check['reason']}")
                return
            
            # Сохраняем множитель размера позиции
            regime_size_multiplier = regime_check['size_multiplier']
        else:
            regime_size_multiplier = 1.0
        
        # ========== TREND FILTER (OPTIMIZED) 📈 ==========
        if settings.require_trend_confirmation:
            trend = analysis['technical'].get('trend', 'sideways')
            
            # Не торгуем против тренда
            if decision == "BUY" and trend in ['downtrend', 'strong_downtrend']:
                print(f"   ⏭️ Skipping BUY: against downtrend")
                return
            if decision == "SELL" and trend in ['uptrend', 'strong_uptrend']:
                print(f"   ⏭️ Skipping SELL: against uptrend")
                return
            
            # Уменьшаем размер в боковике
            if trend == 'sideways':
                regime_size_multiplier *= 0.7
                print(f"   ⚠️ Sideways market: position size reduced to 70%")
        
        # ========== MULTI-AGENT DECISION 🤖 ==========
        if self.use_multi_agent:
            market_data = {
                'symbol': symbol,
                'price': analysis['technical']['price'],
                'rsi': analysis['technical']['rsi'],
                'macd': analysis['technical']['macd'],
                'technical_signal': analysis['technical']['signal'],
                'trend': analysis['technical']['trend']
            }
            
            multi_decision = self.meta_agent.decide(market_data, analysis['ai'])
            
            print(f"\n   🤖 MULTI-AGENT DECISION:")
            if multi_decision['selected_agent']:
                print(f"      Selected: {multi_decision['selected_agent'].value}")
            print(f"      Decision: {multi_decision['decision']}")
            print(f"      Consensus: {'✅' if multi_decision['consensus'] else '❌'}")
            print(f"      Confidence: {multi_decision['confidence']:.0%}")
            
            # Используем решение Multi-Agent
            if multi_decision['decision'] == 'SKIP':
                print(f"   ⏭️ Multi-Agent: SKIP")
                return
            
            # Переопределяем параметры из Multi-Agent
            ai_risk = multi_decision['risk_score']
            ai_confidence = multi_decision['confidence']
            position_size_from_agent = multi_decision['position_size_pct']
        else:
            # Старая логика без Multi-Agent
            ai_risk = analysis['ai']['risk_score']
            ai_confidence = analysis['ai']['confidence']
            position_size_from_agent = None
        
        # OPTIMIZED: используем balanced стратегию для стабильности
        strategy = STRATEGY_CONFIGS['balanced']
        
        if ai_risk > strategy['max_risk']:
            print(f"⚠️ Риск слишком высокий: {ai_risk} > {strategy['max_risk']}")
            return
        
        if ai_confidence < strategy['min_confidence']:
            print(f"⚠️ Уверенность слишком низкая: {ai_confidence:.0%} < {strategy['min_confidence']:.0%}")
            return
        
        # Получаем текущую цену
        ticker = await self.bybit_api.get_ticker(symbol)
        if not ticker:
            print(f"❌ Failed to get ticker for {symbol}")
            return
        
        current_price = ticker['last_price']
        side_str = "BUY" if decision == "BUY" else "SELL"
        
        # ========== DYNAMIC RISK MANAGEMENT 🎯 ==========
        
        # Получаем свечи для ATR расчёта
        candles = await self.bybit_api.get_klines(symbol, "1", limit=200)
        
        # Определяем уровень риска по AI score
        if ai_risk <= 3:
            risk_level = RiskLevel.LOW
        elif ai_risk <= 5:
            risk_level = RiskLevel.MEDIUM
        elif ai_risk <= 7:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.VERY_HIGH
        
        # Рассчитываем полные параметры риска
        win_rate = stats['winrate'] / 100 if stats['total_trades'] > 10 else 0.55
        risk_params = self.risk_manager.calculate_full_risk_params(
            balance=balance,
            entry_price=current_price,
            side=side_str,
            klines=candles,
            risk_level=risk_level,
            win_rate=win_rate
        )
        
        print(f"\n   🎯 DYNAMIC RISK PARAMS:")
        print(f"      ATR: ${risk_params.atr_value:.2f}")
        print(f"      SL: ${risk_params.stop_loss_price:.2f} | TP: ${risk_params.take_profit_price:.2f}")
        print(f"      R:R = 1:{risk_params.risk_reward_ratio:.1f}")
        print(f"      Position: ${risk_params.position_size_usd:.2f} ({risk_params.position_size_qty:.6f})")
        print(f"      Risk: ${risk_params.risk_amount_usd:.2f} ({risk_params.risk_percent:.1f}%)")
        
        # Проверяем портфельный риск
        open_positions_data = [
            {
                'symbol': t.symbol,
                'side': t.side.value,
                'size_usd': t.entry_price * t.quantity,
                'risk_amount': abs(t.entry_price - t.stop_loss) * t.quantity if t.stop_loss else 0
            }
            for t in open_trades
        ]
        
        portfolio_check = self.portfolio_manager.full_risk_check(
            balance=balance,
            daily_pnl=self.daily_pnl,
            open_positions=open_positions_data,
            new_symbol=symbol,
            new_position_risk=risk_params.risk_amount_usd
        )
        
        if not portfolio_check['can_trade']:
            print(f"   ❌ PORTFOLIO RISK CHECK FAILED:")
            for reason in portfolio_check['reasons']:
                print(f"      {reason}")
            return
        
        print(f"   ✅ Portfolio Risk OK: {portfolio_check['portfolio_check']['new_portfolio_risk_pct']:.1f}%")
        
        # Применяем AI multiplier, Multi-Agent size и Market Regime multiplier
        position_multiplier = analysis['ai'].get('position_size_multiplier', 1.0)
        total_multiplier = position_multiplier * regime_size_multiplier
        
        if self.use_multi_agent and position_size_from_agent:
            # Multi-Agent определяет размер позиции
            final_position_usd = balance * position_size_from_agent * total_multiplier
            print(f"   🤖 Multi-Agent position size: {position_size_from_agent*100:.0f}%")
        else:
            final_position_usd = risk_params.position_size_usd * total_multiplier
        
        if total_multiplier < 1.0:
            print(f"   ⚠️ Size adjusted: {total_multiplier:.0%} (AI: {position_multiplier:.0%}, Regime: {regime_size_multiplier:.0%})")
        
        # Рассчитываем количество
        quantity = final_position_usd / current_price
        
        # Округляем количество согласно требованиям Bybit
        quantity = self.trader.round_quantity(symbol, quantity)
        
        # Открываем сделку с ДИНАМИЧЕСКИМИ SL/TP
        side = TradeSide.BUY if decision == "BUY" else TradeSide.SELL
        
        trade = await self.trader.open_trade(
            symbol=symbol,
            side=side,
            entry_price=current_price,
            quantity=quantity,
            ai_risk_score=ai_risk,
            ai_reasoning=analysis['ai']['reasoning'],
            stop_loss_override=risk_params.stop_loss_price,  # DYNAMIC SL
            take_profit_override=risk_params.take_profit_price,  # DYNAMIC TP
            extra_data={
                "strategy": "dynamic_risk",
                "technical_signal": analysis['technical']['signal'],
                "rsi": analysis['technical']['rsi'],
                "macd_trend": analysis['technical']['macd']['trend'],
                "bb_position": analysis['technical']['bollinger_bands']['position'],
                "ml_prediction": analysis.get('ml_prediction'),
                "atr": risk_params.atr_value,
                "risk_reward": risk_params.risk_reward_ratio,
                "risk_level": risk_level.value,
                "trailing_stop_distance": risk_params.trailing_stop_distance
            }
        )
        
        if trade:
            await self.log(
                LogLevel.BUY if side == TradeSide.BUY else LogLevel.SELL,
                f"Opened {side.value} {symbol} @ ${current_price:.2f} (ATR SL/TP)",
                {"trade_id": trade.id, "risk_params": {
                    "sl": risk_params.stop_loss_price,
                    "tp": risk_params.take_profit_price,
                    "rr": risk_params.risk_reward_ratio,
                    "atr": risk_params.atr_value
                }}
            )
            
            # Telegram уведомление
            await self.telegram.notify_position_opened({
                "symbol": symbol,
                "side": side.value,
                "entry_price": current_price,
                "quantity": quantity,
                "cost": current_price * quantity,
                "take_profit": risk_params.take_profit_price,
                "stop_loss": risk_params.stop_loss_price,
                "ai_risk": ai_risk,
                "ai_reasoning": f"{analysis['ai']['reasoning']} | R:R={risk_params.risk_reward_ratio:.1f}"
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
            
            # 5. Статистика Multi-Agent
            if self.use_multi_agent:
                self.meta_agent.print_stats()
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
