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
from core.ai_logger import get_ai_logger
from core.risk_manager import get_risk_manager  # ANTI-TILT PROTECTION

from config import settings, is_spot_enabled, is_futures_enabled, get_spot_pairs, get_futures_pairs
from core.strategy_scaler import get_strategy_scaler


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
        self.ai_brain = get_local_brain(api_client=self.api)  # Передаём API для Gatekeeper
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
        
        # Risk Manager - Anti-Tilt Protection (Circuit Breaker + Loss Cooldown)
        self.risk_manager = get_risk_manager() if is_futures_enabled() else None
        
        # Strategy Scaler - динамическое масштабирование стратегии
        self.strategy_scaler = get_strategy_scaler()
        
        self.running = False
        self.cycle_count = 0
        self.last_strategy_update = None  # Время последнего обновления стратегии
        
        print(f"\n🚀 HYBRID TRADING LOOP initialized:")
        print(f"   Mode: {settings.trading_mode}")
        print(f"   SPOT: {'✅ Enabled' if self.spot_executor else '❌ Disabled'}")
        print(f"   FUTURES: {'✅ Enabled' if self.futures_executor else '❌ Disabled'}")
        if self.futures_executor:
            print(f"   Futures Virtual Balance: ${settings.futures_virtual_balance}")
            print(f"   Futures Leverage: {settings.futures_leverage}x")
        if self.risk_manager:
            print(f"   Risk Manager: ✅ Enabled (Anti-Tilt Protection)")
        print(f"   Strategy Scaler: ✅ Enabled (Tier-based auto-scaling)")
    
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
        
        # Получаем BTC свечи для корреляционного фильтра (если торгуем не BTC)
        btc_klines = []
        if symbol != 'BTCUSDT':
            try:
                btc_klines = await self.api.get_klines('BTCUSDT', '15', limit=10)
            except Exception as e:
                print(f"   ⚠️ Failed to get BTC klines: {e}")
        
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
            "klines": candles,
            "btc_klines": btc_klines  # Для BTC Correlation Filter
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
        OPTIMIZED v2.0: Фильтры по тренду и времени
        """
        symbol = analysis['symbol']
        price = analysis['price']
        ai = analysis['ai']
        technical = analysis['technical']
        
        decision = ai['decision']
        confidence = ai['confidence']
        risk_score = ai['risk_score']
        reasoning = ai['reasoning']
        
        # ========== TREND FILTER (DISABLED for active trading) 📈 ==========
        # Фильтр отключен - торгуем и против тренда для большей активности
        # trend = technical.get('trend', 'sideways')
        # if decision == "BUY" and trend in ['downtrend', 'strong_downtrend']:
        #     print(f"   ⏭️ Skipping BUY: against downtrend")
        #     return
        
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
            print(f"      Score: {futures_decision.total_score}/6 (need {self.futures_brain.min_score_to_trade}+)")
            print(f"      Agents: {futures_decision.agents_voted}")
            
            # ========== AI LOGGER - Полное логирование для анализа ==========
            try:
                ai_logger = get_ai_logger()
                # Извлекаем данные из ai dict
                ml_sig = ai.get('ml_signal')
                ml_signal_str = ml_sig.get('decision') if isinstance(ml_sig, dict) else str(ml_sig) if ml_sig else None
                ml_conf = ai.get('ml_confidence')
                ml_conf_val = ml_conf if isinstance(ml_conf, (int, float)) else None
                
                await ai_logger.log_decision(
                    symbol=symbol,
                    price=price,
                    rsi=technical.get('rsi'),
                    macd=technical.get('macd', {}).get('trend'),
                    trend=technical.get('trend'),
                    news_sentiment=news_sentiment,
                    news_score=ai.get('news_score'),
                    ml_signal=ml_signal_str,
                    ml_confidence=ml_conf_val,
                    ml_predicted_change=ai.get('ml_change'),
                    local_decision=decision,
                    local_confidence=confidence,
                    local_risk=risk_score,
                    agent_consensus=multi_decision.get('consensus'),
                    agent_conservative=futures_decision.agents_voted.get('conservative'),
                    agent_balanced=futures_decision.agents_voted.get('balanced'),
                    agent_aggressive=futures_decision.agents_voted.get('aggressive'),
                    futures_action=futures_decision.action.value,
                    futures_score=futures_decision.total_score,
                    futures_confidence=futures_decision.trading_confidence,
                    futures_leverage=futures_decision.leverage,
                    final_action='EXECUTED' if futures_decision.action != FuturesAction.SKIP else 'SKIPPED',
                    execution_reason=futures_decision.reasoning
                )
            except Exception as e:
                print(f"⚠️ AI logging error: {e}")
            
            if futures_decision.action != FuturesAction.SKIP:
                # ========== ANTI-TILT PROTECTION: Проверка рисков перед открытием ==========
                if self.risk_manager:
                    try:
                        # Получаем текущий баланс
                        from database.db import async_session
                        async with async_session() as session:
                            current_balance = await self.futures_executor.load_balance_from_db()
                            if current_balance is None:
                                current_balance = settings.futures_virtual_balance
                            
                            # Проверяем все риски
                            can_trade, risk_reason = await self.risk_manager.can_open_position(
                                session=session,
                                symbol=symbol,
                                current_balance=current_balance
                            )
                            
                            if not can_trade:
                                # Торговля заблокирована!
                                print(f"\n{risk_reason}")
                                print(f"   ⏭️ Skipping {symbol} due to risk limits")
                                return  # Пропускаем сигнал
                            else:
                                # Риски в норме, продолжаем
                                if "Daily loss check passed" in risk_reason or "Loss cooldown check passed" in risk_reason:
                                    print(f"   ✅ Risk checks passed")
                    except Exception as e:
                        print(f"   ⚠️ Risk Manager check failed: {e}")
                        # Продолжаем торговлю (fail-safe)
                
                # Создаём сигнал с dynamic leverage
                action_str = 'BUY' if futures_decision.action == FuturesAction.LONG else 'SELL'
                
                # Извлекаем ml_features из AI решения (если есть)
                ml_features = ai.get('ml_features') if isinstance(ai, dict) else None
                
                # Извлекаем CHOP и market_mode из gatekeeper (если есть)
                gatekeeper = ai.get('gatekeeper', {}) if isinstance(ai, dict) else {}
                chop = gatekeeper.get('chop')
                
                # Определяем market_mode по CHOP
                market_mode = None
                if chop is not None:
                    market_mode = 'FLAT' if chop > 50.0 else 'TREND'
                
                # Собираем extra_data
                extra_data = {}
                if ml_features:
                    extra_data['ml_features'] = ml_features
                if chop is not None:
                    extra_data['chop'] = chop
                if market_mode:
                    extra_data['market_mode'] = market_mode
                
                futures_signal = TradeSignal(
                    action=action_str,
                    confidence=futures_decision.trading_confidence / 100,
                    risk_score=risk_score,
                    reasoning=futures_decision.reasoning,
                    symbol=symbol,
                    price=price,
                    extra_data=extra_data if extra_data else None
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
        
        # Обновляем GlobalBrainState с торговой статистикой
        try:
            from core.state import get_global_brain_state
            from database.db import async_session
            from database.models import Trade
            from sqlalchemy import select, func
            from datetime import datetime, timedelta
            
            state = get_global_brain_state()
            
            # Получаем статистику из БД
            async with async_session() as session:
                # Общая статистика
                from sqlalchemy import case
                result = await session.execute(
                    select(
                        func.count(Trade.id).label('total'),
                        func.sum(case((Trade.pnl > 0, 1), else_=0)).label('wins'),
                        func.sum(case((Trade.pnl <= 0, 1), else_=0)).label('losses'),
                        func.sum(Trade.pnl).label('total_pnl')
                    ).where(Trade.status == 'CLOSED')
                )
                stats = result.first()
                
                # Статистика за 24ч
                yesterday = datetime.utcnow() - timedelta(hours=24)
                result_24h = await session.execute(
                    select(func.sum(Trade.pnl)).where(
                        Trade.status == 'CLOSED',
                        Trade.exit_time >= yesterday
                    )
                )
                pnl_24h = result_24h.scalar() or 0.0
                
                # Текущий баланс (из config)
                from config import settings
                current_balance = settings.futures_virtual_balance
                
                # Обновляем state
                state.update_trading_performance(
                    total_trades=stats.total or 0,
                    winning_trades=stats.wins or 0,
                    losing_trades=stats.losses or 0,
                    total_pnl=float(stats.total_pnl or 0.0),
                    current_balance=current_balance,
                    performance_24h=float(pnl_24h)
                )
        except Exception as e:
            print(f"⚠️ Failed to update trading stats: {e}")
    
    async def cycle(self):
        """Один цикл торговли"""
        self.cycle_count += 1
        
        print("\n" + "="*80)
        print(f"🔄 Hybrid Cycle #{self.cycle_count} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("="*80)
        
        # ========== 🚨 EMERGENCY BRAKE - ПРИОРИТЕТ #1 ==========
        # Проверяем критические риски ПЕРЕД всем остальным!
        if self.futures_executor and settings.emergency_brake_enabled:
            try:
                print(f"\n🚨 EMERGENCY BRAKE: Checking critical risks...")
                closed_count = await self.futures_executor.execute_emergency_closures()
                
                if closed_count > 0:
                    # Уведомление в Telegram о экстренном закрытии
                    await self.telegram.notify_emergency_closure(closed_count)
                    print(f"   ✅ Emergency Brake: {closed_count} positions closed")
                else:
                    print(f"   ✅ All positions within safe limits")
                    
            except Exception as e:
                print(f"   ⚠️ Emergency Brake error: {e}")
                import traceback
                traceback.print_exc()
        
        # ========== STRATEGY SCALER: Динамическое масштабирование ==========
        # Обновляем стратегию каждые 10 минут или при первом запуске
        should_update_strategy = (
            self.last_strategy_update is None or
            (datetime.utcnow() - self.last_strategy_update).total_seconds() > 600  # 10 минут
        )
        
        if should_update_strategy and self.futures_executor:
            try:
                # Получаем текущий баланс из БД
                current_balance = await self.futures_executor.load_balance_from_db()
                
                # Проверка на None
                if current_balance is None:
                    print(f"⚠️ Balance is None, using config default")
                    current_balance = settings.futures_virtual_balance
                
                # Обновляем стратегию
                strategy_update = self.strategy_scaler.update_strategy(current_balance)
                
                if strategy_update['tier_changed']:
                    # Tier изменился! Обновляем настройки
                    print(f"\n🎯 STRATEGY SCALER: Applying new tier settings...")
                    
                    # Обновляем глобальные настройки
                    settings.futures_pairs = strategy_update['active_pairs']
                    settings.futures_max_open_positions = strategy_update['max_open_positions']
                    settings.futures_risk_per_trade = strategy_update['risk_per_trade']
                    settings.futures_min_confidence = strategy_update['min_confidence']
                    
                    print(f"   ✅ Settings updated:")
                    print(f"      Active Pairs: {', '.join(strategy_update['active_pairs'])}")
                    print(f"      Max Positions: {strategy_update['max_open_positions']}")
                    print(f"      Risk per Trade: {strategy_update['risk_per_trade']*100:.0f}%")
                    print(f"      Min Confidence: {strategy_update['min_confidence']*100:.0f}%")
                    
                    # Уведомление в Telegram
                    await self.telegram.notify_strategy_upgrade(
                        tier_name=strategy_update['tier_name'],
                        balance=current_balance,
                        active_pairs=strategy_update['active_pairs'],
                        max_positions=strategy_update['max_open_positions']
                    )
                
                self.last_strategy_update = datetime.utcnow()
                
            except Exception as e:
                print(f"⚠️ Strategy Scaler error: {e}")
        
        # ========== STRATEGIC COMPLIANCE CHECK (Soft Landing v2.0) ==========
        # Умное управление позициями при смене режима Strategic Brain
        if self.futures_executor and self.ai_brain.strategic_brain:
            try:
                from database.db import async_session
                from database.models import Trade, TradeSide
                from sqlalchemy import select
                
                # Получаем текущий режим
                current_regime = self.ai_brain.strategic_brain.current_regime
                
                # Получаем открытые позиции из БД
                async with async_session() as session:
                    result = await session.execute(
                        select(Trade).where(
                            Trade.status == 'OPEN',
                            Trade.market_type == 'futures'
                        )
                    )
                    open_trades = result.scalars().all()
                    
                    if open_trades and current_regime:
                        positions_to_close = []
                        
                        # ========== SOFT LANDING LOGIC ==========
                        if current_regime == 'UNCERTAIN':
                            # UNCERTAIN: НЕ закрываем позиции, только блокируем новые
                            print(f"\n⚠️ Strategic Regime: UNCERTAIN")
                            print(f"   🔒 Freezing new entries. Managing {len(open_trades)} existing positions.")
                            print(f"   💡 Positions will close via TP/Trailing Stop/Emergency Brake")
                            # НЕ добавляем позиции в positions_to_close!
                        
                        elif current_regime == 'BEAR_CRASH':
                            # BEAR: Закрываем только LONG позиции
                            print(f"\n🐻 Strategic Regime: BEAR_CRASH")
                            for trade in open_trades:
                                if trade.side == TradeSide.BUY:  # LONG позиция
                                    positions_to_close.append({
                                        'trade': trade,
                                        'reason': 'Strategic Compliance: LONG in BEAR market'
                                    })
                                    print(f"   ❌ Closing LONG {trade.symbol} (against trend)")
                                else:
                                    print(f"   ✅ Keeping SHORT {trade.symbol} (with trend)")
                        
                        elif current_regime == 'BULL_RUSH':
                            # BULL: Закрываем только SHORT позиции
                            print(f"\n🐂 Strategic Regime: BULL_RUSH")
                            for trade in open_trades:
                                if trade.side == TradeSide.SELL:  # SHORT позиция
                                    positions_to_close.append({
                                        'trade': trade,
                                        'reason': 'Strategic Compliance: SHORT in BULL market'
                                    })
                                    print(f"   ❌ Closing SHORT {trade.symbol} (against trend)")
                                else:
                                    print(f"   ✅ Keeping LONG {trade.symbol} (with trend)")
                        
                        elif current_regime == 'SIDEWAYS':
                            # SIDEWAYS: Всё разрешено, ничего не закрываем
                            print(f"\n↔️ Strategic Regime: SIDEWAYS")
                            print(f"   ✅ All positions allowed. Managing {len(open_trades)} positions.")
                        
                        # Закрываем только несоответствующие позиции
                        if positions_to_close:
                            print(f"\n🚨 STRATEGIC COMPLIANCE: Closing {len(positions_to_close)} non-compliant positions")
                            
                            for pos_info in positions_to_close:
                                trade = pos_info['trade']
                                reason = pos_info['reason']
                                
                                # Закрываем через executor (правильный расчёт PnL и комиссий)
                                try:
                                    result = await self.futures_executor.close_position(
                                        symbol=trade.symbol,
                                        reason=reason
                                    )
                                    
                                    if result.success:
                                        print(f"   ✅ Closed {trade.symbol} {trade.side.value}: {reason}")
                                    else:
                                        print(f"   ⚠️ Failed to close {trade.symbol}: {result.error}")
                                        
                                except Exception as e:
                                    print(f"   ❌ Error closing {trade.symbol}: {e}")
                            
                            # Уведомление в Telegram
                            await self.telegram.notify_strategic_compliance(
                                regime=current_regime,
                                positions_closed=len(positions_to_close)
                            )
                        
            except Exception as e:
                print(f"⚠️ Strategic Compliance check error: {e}")
                import traceback
                traceback.print_exc()
        
        # Обновляем GlobalBrainState - бот активен
        try:
            from core.state import get_global_brain_state
            state = get_global_brain_state()
            state.update_system_status(running=True, scan_time=datetime.utcnow())
        except:
            pass
        
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
            
            # Определяем пары для анализа
            # Используем symbols_to_scan из Strategy Scaler (включает BTCUSDT для корреляции)
            if self.strategy_scaler.current_tier:
                # Получаем баланс с проверкой на None
                balance = await self.futures_executor.load_balance_from_db() if self.futures_executor else 100.0
                if balance is None:
                    balance = settings.futures_virtual_balance
                
                strategy_info = self.strategy_scaler.update_strategy(balance)
                pairs = set(strategy_info['symbols_to_scan'])
            else:
                # Fallback на статические пары
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
        
        # ========== GATEKEEPER: Загрузка истории для ScenarioTester ==========
        if self.ai_brain.scenario_tester:
            print(f"\n🔍 Gatekeeper: Loading historical data...")
            all_symbols = list(set(get_spot_pairs() + get_futures_pairs()))
            asyncio.create_task(self.ai_brain.scenario_tester.load_initial_history(all_symbols))
        
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
    """Entry point with Telegram Commander"""
    loop = HybridTradingLoop()
    
    # Инициализируем Telegram Commander
    try:
        from core.telegram_commander import get_telegram_commander
        
        # Создаём commander с ссылками на компоненты
        # strategic_brain доступен через ai_brain.strategic_brain
        strategic_brain = loop.ai_brain.strategic_brain if loop.ai_brain else None
        
        commander = get_telegram_commander(
            executor=loop.futures_executor,
            ai_brain=loop.ai_brain,
            strategic_brain=strategic_brain
        )
        
        # Запускаем commander в фоне
        commander_task = asyncio.create_task(commander.start())
        print("✅ Telegram Commander started in background")
        
    except Exception as e:
        print(f"⚠️ Telegram Commander disabled: {e}")
        commander = None
        commander_task = None
    
    # Запускаем основной цикл торговли
    try:
        await loop.run()
    finally:
        # Останавливаем commander при выходе
        if commander:
            try:
                await commander.stop()
            except Exception as e:
                print(f"⚠️ Commander stop error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
