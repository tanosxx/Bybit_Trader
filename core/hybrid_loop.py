"""
Hybrid Trading Loop - Параллельная торговля SPOT + FUTURES
Единый сигнал от AI Brain -> Исполнение на обоих рынках
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from database.db import init_db, async_session
from database.models import SystemLog, LogLevel
from core.bybit_api import get_bybit_api
from core.technical_analyzer import get_technical_analyzer
from core.ai_brain_local import get_local_brain
from core.telegram_notifier import get_telegram_notifier
from core.ta_lib import get_dynamic_risk_manager, get_portfolio_risk_manager
from core.multi_agent import get_meta_agent

from core.executors.base_executor import TradeSignal, MarketType
from core.executors.spot_executor import get_spot_executor
from core.executors.futures_executor import get_futures_executor
from core.futures_brain import get_futures_brain, FuturesAction
from core.safety_guardian import get_safety_guardian

from config import settings, is_spot_enabled, is_futures_enabled, get_spot_pairs, get_futures_pairs


class HybridTradingLoop:
    """
    Гибридный торговый цикл
    
    Архитектура:
    1. Получаем единый сигнал от LocalBrain (News + ML + TA)
    2. Параллельно исполняем на SPOT и FUTURES
    3. Раздельная статистика и риск-менеджмент
    """
    
    def __init__(self):
        self.api = get_bybit_api()
        self.technical_analyzer = get_technical_analyzer()
        self.ai_brain = get_local_brain()
        self.telegram = get_telegram_notifier()
        self.risk_manager = get_dynamic_risk_manager()
        self.portfolio_manager = get_portfolio_risk_manager()
        self.meta_agent = get_meta_agent()
        
        # Executors
        self.spot_executor = get_spot_executor() if is_spot_enabled() else None
        self.futures_executor = get_futures_executor() if is_futures_enabled() else None
        self.futures_brain = get_futures_brain() if is_futures_enabled() else None
        
        # Safety Guardian - автоматический аудит позиций
        self.safety_guardian = get_safety_guardian() if is_futures_enabled() else None
        
        self.running = False
        self.cycle_count = 0
        
        print(f"\n🚀 HYBRID TRADING LOOP initialized:")
        print(f"   Mode: {settings.trading_mode}")
        print(f"   SPOT: {'✅ Enabled' if self.spot_executor else '❌ Disabled'}")
        print(f"   FUTURES: {'✅ Enabled' if self.futures_executor else '❌ Disabled'}")
        if self.futures_executor:
            print(f"   Futures Virtual Balance: ${settings.futures_virtual_balance}")
            print(f"   Futures Leverage: {settings.futures_leverage}x")
    
    async def log(self, level: LogLevel, message: str, extra_data: Dict = None):
        """Логирование в БД"""
        async with async_session() as session:
            log = SystemLog(
                level=level,
                component="HybridLoop",
                message=message,
                extra_data=extra_data
            )
            session.add(log)
            await session.commit()
    
    async def analyze_market(self, symbol: str) -> Optional[Dict]:
        """
        Анализ рынка: TA + AI + ML
        Возвращает единый сигнал для обоих рынков
        """
        print(f"\n📊 Analyzing {symbol}...")
        
        # Получаем свечи
        candles = await self.api.get_klines(symbol, "1", limit=200)
        
        if not candles or len(candles) < 50:
            print(f"❌ Not enough data for {symbol}")
            return None
        
        # Технический анализ
        technical = self.technical_analyzer.analyze_market(candles)
        
        if "error" in technical:
            return None
        
        print(f"   Price: ${technical['price']:.2f}")
        print(f"   RSI: {technical['rsi']:.1f}")
        print(f"   MACD: {technical['macd']['trend']}")
        print(f"   Trend: {technical['trend']}")
        
        # AI Brain анализ
        market_data = {
            "symbol": symbol,
            "price": technical['price'],
            "rsi": technical['rsi'],
            "macd": technical['macd'],
            "bollinger_bands": technical['bollinger_bands'],
            "trend": technical['trend'],
            "volume_trend": technical['volume_trend'],
            "technical_signal": technical['signal'],
            "klines": candles
        }
        
        ai_analysis = await self.ai_brain.decide_trade(market_data)
        
        if not ai_analysis:
            return None
        
        print(f"   🧠 AI Decision: {ai_analysis['decision']}")
        print(f"   🎯 Confidence: {ai_analysis['confidence']:.0%}")
        print(f"   ⚠️  Risk: {ai_analysis['risk_score']}/10")
        
        return {
            "symbol": symbol,
            "price": technical['price'],
            "technical": technical,
            "ai": ai_analysis,
            "candles": candles
        }
    
    async def execute_hybrid(self, analysis: Dict):
        """
        Исполнить сигнал на обоих рынках параллельно
        """
        symbol = analysis['symbol']
        price = analysis['price']
        ai = analysis['ai']
        technical = analysis['technical']
        
        decision = ai['decision']
        confidence = ai['confidence']
        risk_score = ai['risk_score']
        reasoning = ai['reasoning']
        
        # Multi-Agent проверка (даже если AI сказал SKIP)
        market_data = {
            'symbol': symbol,
            'price': price,
            'rsi': technical['rsi'],
            'macd': technical['macd'],
            'technical_signal': technical['signal'],
            'trend': technical['trend']
        }
        
        # Для Multi-Agent используем AI решение или создаём фейковое если SKIP
        ai_for_multi = ai if decision != 'SKIP' else {
            'decision': technical['signal'],  # Используем технический сигнал
            'confidence': 0.5,
            'risk_score': 5,
            'reasoning': 'Technical signal fallback'
        }
        
        multi_decision = self.meta_agent.decide(market_data, ai_for_multi)
        
        print(f"\n   🤖 MULTI-AGENT: {multi_decision['decision']} (consensus: {'✅' if multi_decision['consensus'] else '❌'})")
        
        # ========== SPOT EXECUTION (консервативная) ==========
        if self.spot_executor and symbol in get_spot_pairs():
            # SPOT требует: AI не SKIP + консенсус Multi-Agent
            if decision != 'SKIP' and multi_decision['decision'] != 'SKIP' and multi_decision['consensus']:
                spot_signal = TradeSignal(
                    action=multi_decision['decision'],
                    confidence=multi_decision['confidence'],
                    risk_score=risk_score,
                    reasoning=reasoning,
                    symbol=symbol,
                    price=price
                )
                if spot_signal.is_buy:  # SPOT только LONG
                    print(f"\n   📈 [SPOT] Executing {spot_signal.action}...")
                    await self._execute_spot(spot_signal)
        
        # ========== FUTURES EXECUTION (Smart Brain) ==========
        # Фьючерсы используют FuturesBrain с Smart Scaling и Weighted Voting
        if self.futures_executor and self.futures_brain and symbol in get_futures_pairs():
            # Получаем news sentiment
            news_sentiment = 'NEUTRAL'
            if hasattr(ai, 'get') and ai.get('news_sentiment'):
                news_sentiment = ai.get('news_sentiment', 'NEUTRAL')
            
            # FuturesBrain принимает решение
            futures_decision = self.futures_brain.decide(market_data, ai, news_sentiment)
            
            print(f"\n   🧠 FUTURES BRAIN: {futures_decision.action.value}")
            print(f"      Raw Conf: {futures_decision.raw_confidence:.0%} -> Trading Conf: {futures_decision.trading_confidence:.0f}%")
            print(f"      Score: {futures_decision.total_score}/6 (need 3+)")
            print(f"      Agents: {futures_decision.agents_voted}")
            
            if futures_decision.action != FuturesAction.SKIP:
                # Создаём сигнал с dynamic leverage
                action_str = 'BUY' if futures_decision.action == FuturesAction.LONG else 'SELL'
                futures_signal = TradeSignal(
                    action=action_str,
                    confidence=futures_decision.trading_confidence / 100,
                    risk_score=risk_score,
                    reasoning=futures_decision.reasoning,
                    symbol=symbol,
                    price=price
                )
                
                # Устанавливаем dynamic leverage
                self.futures_executor.leverage = futures_decision.leverage
                
                print(f"   📉 [FUTURES] Executing {futures_decision.action.value} with {futures_decision.leverage}x leverage...")
                await self._execute_futures(futures_signal)
    

    
    async def _execute_spot(self, signal: TradeSignal):
        """Исполнить на SPOT"""
        try:
            result = await self.spot_executor.execute_signal(signal)
            
            if result.success:
                await self.log(
                    LogLevel.BUY if signal.is_buy else LogLevel.SELL,
                    f"[SPOT] {signal.action} {signal.symbol} @ ${signal.price:.2f}",
                    {"market_type": "spot", "order_id": result.order_id}
                )
                
                # Telegram - детальное уведомление
                await self.telegram.notify_spot_opened(
                    symbol=signal.symbol,
                    side=signal.action,
                    entry_price=signal.price,
                    quantity=result.quantity,
                    cost=signal.price * result.quantity,
                    stop_loss=result.extra_data.get('stop_loss', 0),
                    take_profit=result.extra_data.get('take_profit', 0),
                    confidence=signal.confidence,
                    reasoning=signal.reasoning
                )
            
            return result
        except Exception as e:
            print(f"❌ SPOT execution error: {e}")
            return None
    
    async def _execute_futures(self, signal: TradeSignal):
        """Исполнить на FUTURES"""
        try:
            result = await self.futures_executor.execute_signal(signal)
            
            if result.success:
                side = result.extra_data.get('position_side', signal.action)
                leverage = result.extra_data.get('leverage', settings.futures_leverage)
                stop_loss = result.extra_data.get('stop_loss', 0)
                take_profit = result.extra_data.get('take_profit', 0)
                
                await self.log(
                    LogLevel.BUY if signal.is_buy else LogLevel.SELL,
                    f"[FUTURES] {side} {signal.symbol} @ ${signal.price:.2f} ({leverage}x)",
                    {"market_type": "futures", "order_id": result.order_id, "leverage": leverage}
                )
                # Telegram уведомление отправляется из FuturesExecutor
            
            return result
        except Exception as e:
            print(f"❌ FUTURES execution error: {e}")
            return None
    
    async def check_positions(self):
        """Проверить открытые позиции на обоих рынках"""
        # SPOT positions
        if self.spot_executor:
            spot_positions = await self.spot_executor.get_open_positions()
            if spot_positions:
                print(f"\n📈 SPOT Positions: {len(spot_positions)}")
        
        # FUTURES positions
        if self.futures_executor:
            futures_positions = await self.futures_executor.get_open_positions()
            if futures_positions:
                print(f"📉 FUTURES Positions: {len(futures_positions)}")
    
    async def print_stats(self):
        """Вывести статистику по обоим рынкам"""
        print("\n" + "="*60)
        print("📊 HYBRID TRADING STATS")
        print("="*60)
        
        if self.spot_executor:
            self.spot_executor.print_stats()
        
        if self.futures_executor:
            self.futures_executor.print_stats()
        
        # Futures Brain stats
        if self.futures_brain:
            self.futures_brain.print_stats()
        
        # AI Brain stats
        self.ai_brain.print_stats()
        
        # Multi-Agent stats
        self.meta_agent.print_stats()
        
        # Safety Guardian stats
        if self.safety_guardian:
            stats = self.safety_guardian.get_stats()
            print(f"\n🛡️ SAFETY GUARDIAN STATS:")
            print(f"   Checks: {stats['checks']}")
            print(f"   Violations Found: {stats['violations_found']}")
            print(f"   Positions Closed: {stats['positions_closed']}")
            print(f"   Emergency PnL: ${stats['emergency_pnl']:+.2f}")
        
        print("="*60)
    
    async def cycle(self):
        """Один цикл торговли"""
        self.cycle_count += 1
        
        print("\n" + "="*80)
        print(f"🔄 Hybrid Cycle #{self.cycle_count} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("="*80)
        
        try:
            # 🛡️ SAFETY GUARDIAN - проверка и защита позиций
            if self.safety_guardian:
                guardian_result = await self.safety_guardian.audit_and_protect()
                if guardian_result['closed']:
                    await self.telegram.notify_safety_alert(
                        closed_positions=guardian_result['closed'],
                        total_pnl=guardian_result['total_pnl']
                    )
            
            # 🎯 v5.0: РУЧНАЯ ПРОВЕРКА SL/TP для фьючерсов
            if self.futures_executor:
                closed_by_sltp = await self.futures_executor.check_and_close_sl_tp()
                if closed_by_sltp:
                    for pos in closed_by_sltp:
                        print(f"   🎯 Closed {pos['symbol']} {pos['side']}: {pos['reason']} | PnL: ${pos['pnl']:+.2f}")
            
            # Проверяем позиции
            await self.check_positions()
            
            # Определяем пары для анализа (объединяем SPOT и FUTURES)
            pairs = set(get_spot_pairs() + get_futures_pairs())
            
            # Анализируем каждую пару
            for symbol in pairs:
                analysis = await self.analyze_market(symbol)
                
                if analysis:
                    await self.execute_hybrid(analysis)
                
                await asyncio.sleep(2)
            
            # Статистика
            await self.print_stats()
            
            await self.log(LogLevel.INFO, f"Hybrid Cycle #{self.cycle_count} completed")
            
        except Exception as e:
            print(f"❌ Error in cycle: {e}")
            await self.log(LogLevel.ERROR, f"Cycle error: {e}")
    
    async def run(self):
        """Запустить гибридный бот"""
        print("\n" + "="*80)
        print("🚀 HYBRID TRADING BOT Starting...")
        print("="*80)
        
        await init_db()
        
        print(f"\n⚙️ Configuration:")
        print(f"   Trading Mode: {settings.trading_mode}")
        print(f"   SPOT Pairs: {get_spot_pairs()}")
        print(f"   FUTURES Pairs: {get_futures_pairs()}")
        print(f"   Scan Interval: {settings.scan_interval}s")
        
        if self.futures_executor:
            print(f"\n💰 FUTURES Settings:")
            print(f"   Virtual Balance: ${settings.futures_virtual_balance}")
            print(f"   Leverage: {settings.futures_leverage}x")
            print(f"   Risk per Trade: {settings.futures_risk_per_trade*100}%")
            print(f"   Margin Mode: {settings.futures_margin_mode}")
        
        self.running = True
        
        await self.telegram.notify_bot_started(
            mode=settings.trading_mode,
            spot_enabled=bool(self.spot_executor),
            futures_enabled=bool(self.futures_executor)
        )
        
        await self.log(LogLevel.INFO, "Hybrid Bot started")
        
        while self.running:
            try:
                await self.cycle()
                
                print(f"\n⏳ Waiting {settings.scan_interval}s...")
                await asyncio.sleep(settings.scan_interval)
                
            except KeyboardInterrupt:
                print("\n⚠️ Stopping bot...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                await asyncio.sleep(10)
        
        await self.log(LogLevel.INFO, "Hybrid Bot stopped")
        print("\n✅ Hybrid Bot stopped")


async def main():
    """Entry point"""
    loop = HybridTradingLoop()
    await loop.run()


if __name__ == "__main__":
    asyncio.run(main())
