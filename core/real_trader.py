"""
Реальный трейдер для Bybit
Открывает реальные ордера на бирже через API
"""
from datetime import datetime
from typing import Dict, List, Optional
from database.db import async_session
from database.models import Trade, WalletHistory, SystemLog, TradeStatus, TradeSide, LogLevel
from sqlalchemy import select, desc
from config import settings
from core.bybit_api import get_bybit_api
from core.ml_predictor import get_ml_predictor
from core.ai_brain_local import get_local_brain  # Local Brain (автономный)


class RealTrader:
    """Реальный трейдер - открывает ордера на Bybit"""
    
    # Правила округления для разных монет (Bybit требования)
    QUANTITY_PRECISION = {
        'BTCUSDT': 6,   # 0.000001
        'ETHUSDT': 5,   # 0.00001
        'BNBUSDT': 3,   # 0.001
        'SOLUSDT': 2,   # 0.01
        'XRPUSDT': 0,   # целые числа!
        'DOGEUSDT': 0,  # целые числа
        'ADAUSDT': 0,   # целые числа
    }
    
    def __init__(self):
        self.bybit_api = get_bybit_api()
        self.ml_predictor = get_ml_predictor()
        self.ai_brain = get_local_brain()  # Используем Local Brain (автономный)
        self.initial_balance = settings.initial_balance
        self.ml_enabled = False
    
    def round_quantity(self, symbol: str, quantity: float) -> float:
        """Округлить количество согласно требованиям Bybit"""
        precision = self.QUANTITY_PRECISION.get(symbol, 2)
        if precision == 0:
            return int(quantity)
        return round(quantity, precision)
    
    async def get_balance(self) -> float:
        """Получить реальный баланс с Bybit"""
        balances = await self.bybit_api.get_wallet_balance()
        
        if balances and "USDT" in balances:
            return balances["USDT"]["total"]
        
        return 0.0
    
    async def get_open_trades(self) -> List[Trade]:
        """Получить открытые сделки из БД"""
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.OPEN)
            )
            return result.scalars().all()
    
    async def open_trade(
        self,
        symbol: str,
        side: TradeSide,
        entry_price: float,
        quantity: float,
        ai_risk_score: int = 5,
        ai_reasoning: str = "",
        stop_loss_override: float = None,
        take_profit_override: float = None,
        extra_data: Dict = None
    ) -> Optional[Trade]:
        """
        Открыть реальную сделку на Bybit
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            side: BUY (LONG) или SELL (SHORT)
            entry_price: цена входа
            quantity: количество
            ai_risk_score: оценка риска AI
            ai_reasoning: объяснение AI
            stop_loss_override: Динамический SL (ATR-based)
            take_profit_override: Динамический TP (ATR-based)
            extra_data: дополнительные данные
        
        Returns:
            Trade объект или None
        """
        try:
            # Используем динамические SL/TP если переданы, иначе фиксированные
            if stop_loss_override and take_profit_override:
                stop_loss = stop_loss_override
                take_profit = take_profit_override
                print(f"   📊 Using DYNAMIC SL/TP (ATR-based)")
            else:
                # Fallback на фиксированные проценты
                if side == TradeSide.BUY:
                    stop_loss = entry_price * (1 - settings.stop_loss_pct / 100)
                    take_profit = entry_price * (1 + settings.take_profit_pct / 100)
                else:  # SELL (SHORT)
                    stop_loss = entry_price * (1 + settings.stop_loss_pct / 100)
                    take_profit = entry_price * (1 - settings.take_profit_pct / 100)
                print(f"   📊 Using FIXED SL/TP ({settings.stop_loss_pct}%/{settings.take_profit_pct}%)")
            # 1. Открываем SPOT ордер на Bybit
            bybit_side = "Buy" if side == TradeSide.BUY else "Sell"
            
            order_result = await self.bybit_api.place_order(
                symbol=symbol,
                side=bybit_side,
                order_type="Market",  # Рыночный ордер
                qty=quantity
            )
            
            if not order_result:
                print(f"❌ Не удалось открыть ордер на Bybit")
                return None
            
            print(f"✅ Ордер открыт на Bybit: {order_result['order_id']}")
            
            # 2. Сохраняем в БД
            async with async_session() as session:
                trade_extra_data = extra_data or {}
                trade_extra_data['bybit_order_id'] = order_result['order_id']
                
                trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=TradeStatus.OPEN,
                    ai_risk_score=ai_risk_score,
                    ai_reasoning=ai_reasoning,
                    extra_data=trade_extra_data
                )
                
                session.add(trade)
                await session.commit()
                await session.refresh(trade)
                
                # Логируем
                log = SystemLog(
                    level=LogLevel.BUY if side == TradeSide.BUY else LogLevel.SELL,
                    component="RealTrader",
                    message=f"Opened {side.value} {symbol} @ ${entry_price:.2f}",
                    extra_data={
                        'trade_id': trade.id,
                        'bybit_order_id': order_result['order_id'],
                        'quantity': quantity,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
                )
                session.add(log)
                await session.commit()
                
                print(f"✅ Opened {side.value} {symbol} @ ${entry_price:.2f}")
                print(f"   Bybit Order ID: {order_result['order_id']}")
                print(f"   Quantity: {quantity}, Cost: ${entry_price * quantity:.2f}")
                print(f"   Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
                
                return trade
        
        except Exception as e:
            print(f"❌ Ошибка открытия сделки: {e}")
            return None
    
    async def close_trade(
        self,
        trade: Trade,
        exit_price: float,
        reason: str
    ) -> Dict:
        """
        Закрыть реальную сделку на Bybit (SPOT)
        
        Args:
            trade: Trade объект
            exit_price: цена выхода
            reason: причина закрытия
        
        Returns:
            Dict с информацией о закрытии
        """
        try:
            # 1. Получаем реальное количество монет на балансе
            balances = await self.bybit_api.get_wallet_balance()
            base_coin = trade.symbol.replace('USDT', '').replace('USDC', '')
            
            if base_coin not in balances or balances[base_coin]['total'] <= 0:
                print(f"⚠️  Монеты {base_coin} не найдены на балансе, закрываем только в БД")
                # Закрываем только в БД
                return await self._close_in_db_only(trade, exit_price, reason + " (coins not found)")
            
            # Используем реальное количество с баланса (с правильным округлением!)
            real_quantity = self.round_quantity(trade.symbol, balances[base_coin]['total'])
            
            if real_quantity <= 0:
                print(f"⚠️  Количество {base_coin} слишком мало после округления")
                return await self._close_in_db_only(trade, exit_price, reason + " (qty too small)")
            
            # 2. Закрываем позицию на Bybit (продаем монеты)
            bybit_side = "Sell" if trade.side == TradeSide.BUY else "Buy"
            
            order_result = await self.bybit_api.place_order(
                symbol=trade.symbol,
                side=bybit_side,
                order_type="Market",
                qty=real_quantity  # Используем округлённое количество!
            )
            
            if not order_result:
                print(f"❌ Не удалось закрыть ордер на Bybit")
                return {"success": False}
            
            print(f"✅ Ордер закрыт на Bybit: {order_result['order_id']}")
            print(f"   Продано: {real_quantity:.8f} {base_coin} (было в БД: {trade.quantity:.8f})")
            
            # 2. Рассчитываем PnL
            if trade.side == TradeSide.BUY:
                pnl = (exit_price - trade.entry_price) * trade.quantity
            else:  # SELL (SHORT)
                pnl = (trade.entry_price - exit_price) * trade.quantity
            
            pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
            
            # 3. Обновляем в БД
            async with async_session() as session:
                trade.status = TradeStatus.CLOSED
                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                trade.exit_reason = reason
                
                if trade.extra_data is None:
                    trade.extra_data = {}
                trade.extra_data['bybit_close_order_id'] = order_result['order_id']
                
                session.add(trade)
                
                # Обновляем баланс
                current_balance = await self.get_balance()
                
                wallet = WalletHistory(
                    balance_usdt=current_balance,
                    equity=current_balance,
                    change_amount=pnl,
                    change_reason=f"Closed {trade.side.value} {trade.symbol}: {reason}"
                )
                session.add(wallet)
                
                # Логируем
                emoji = "🟢" if pnl > 0 else "🔴"
                log = SystemLog(
                    level=LogLevel.INFO,
                    component="RealTrader",
                    message=f"{emoji} Closed {trade.side.value} {trade.symbol} @ ${exit_price:.2f}",
                    extra_data={
                        'trade_id': trade.id,
                        'bybit_close_order_id': order_result['order_id'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': reason
                    }
                )
                session.add(log)
                
                await session.commit()
                
                print(f"{emoji} Closed {trade.side.value} {trade.symbol} @ ${exit_price:.2f}")
                print(f"   Bybit Close Order ID: {order_result['order_id']}")
                print(f"   PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
                print(f"   Reason: {reason}")
                
                return {
                    "success": True,
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "entry_price": trade.entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": reason
                }
        
        except Exception as e:
            print(f"❌ Ошибка закрытия сделки: {e}")
            return {"success": False}
    
    async def _close_in_db_only(self, trade: Trade, exit_price: float, reason: str) -> Dict:
        """
        Закрыть позицию только в БД (без продажи на бирже)
        Используется когда монеты уже проданы или не найдены
        """
        try:
            async with async_session() as session:
                # Рассчитываем PnL
                if trade.side == TradeSide.BUY:
                    pnl = (exit_price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - exit_price) * trade.quantity
                
                pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
                
                trade.status = TradeStatus.CLOSED
                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                
                if trade.extra_data is None:
                    trade.extra_data = {}
                trade.extra_data['close_reason'] = reason
                
                session.add(trade)
                
                # Логируем
                emoji = "🟢" if pnl > 0 else "🔴"
                log = SystemLog(
                    level=LogLevel.INFO,
                    component="RealTrader",
                    message=f"{emoji} Closed in DB only: {trade.side.value} {trade.symbol} @ ${exit_price:.2f}",
                    extra_data={
                        'trade_id': trade.id,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': reason
                    }
                )
                session.add(log)
                
                await session.commit()
                
                print(f"{emoji} Closed in DB: {trade.symbol} PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
                print(f"   Reason: {reason}")
                
                return {
                    "success": True,
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side.value,
                    "entry_price": trade.entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": reason
                }
        
        except Exception as e:
            print(f"❌ Error closing in DB: {e}")
            return {"success": False}
    
    async def check_stop_loss_take_profit(self, current_prices: Dict[str, float], telegram_notifier=None):
        """
        Проверить Stop Loss и Take Profit для открытых позиций
        
        Args:
            current_prices: {"BTCUSDT": 43250.50, "ETHUSDT": 2250.30}
            telegram_notifier: Telegram notifier для уведомлений (опционально)
        """
        open_trades = await self.get_open_trades()
        
        for trade in open_trades:
            if trade.symbol not in current_prices:
                continue
            
            current_price = current_prices[trade.symbol]
            
            # Проверяем Stop Loss
            if trade.side == TradeSide.BUY and current_price <= trade.stop_loss:
                result = await self.close_trade(trade, current_price, "Stop Loss triggered")
                if telegram_notifier and result.get("success"):
                    await telegram_notifier.notify_position_closed(result)
            
            elif trade.side == TradeSide.SELL and current_price >= trade.stop_loss:
                result = await self.close_trade(trade, current_price, "Stop Loss triggered")
                if telegram_notifier and result.get("success"):
                    await telegram_notifier.notify_position_closed(result)
            
            # Проверяем Take Profit
            elif trade.side == TradeSide.BUY and current_price >= trade.take_profit:
                result = await self.close_trade(trade, current_price, "Take Profit reached")
                if telegram_notifier and result.get("success"):
                    await telegram_notifier.notify_position_closed(result)
            
            elif trade.side == TradeSide.SELL and current_price <= trade.take_profit:
                result = await self.close_trade(trade, current_price, "Take Profit reached")
                if telegram_notifier and result.get("success"):
                    await telegram_notifier.notify_position_closed(result)
    
    async def get_statistics(self) -> Dict:
        """Получить статистику торговли (алиас для совместимости)"""
        return await self.get_trade_statistics()
    
    async def get_trade_statistics(self) -> Dict:
        """Получить статистику торговли"""
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == TradeStatus.CLOSED)
            )
            closed_trades = result.scalars().all()
            
            if not closed_trades:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "winrate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0
                }
            
            wins = sum(1 for t in closed_trades if t.pnl > 0)
            losses = len(closed_trades) - wins
            total_pnl = sum(t.pnl for t in closed_trades)
            
            return {
                "total_trades": len(closed_trades),
                "wins": wins,
                "losses": losses,
                "winrate": (wins / len(closed_trades)) * 100,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(closed_trades)
            }
    
    async def initialize_ml(self):
        """Инициализация ML модели"""
        try:
            print("🤖 Initializing ML model...")
            success = await self.ml_predictor.load_model()
            if success:
                self.ml_enabled = True
                print("✅ ML model loaded successfully")
            else:
                self.ml_enabled = False
                print("⚠️  ML model not available, using AI only")
        except Exception as e:
            self.ml_enabled = False
            print(f"❌ ML initialization error: {e}")
    
    async def analyze_with_ml_and_ai(self, symbol: str, current_price: float) -> Dict:
        """Комбинированный анализ с ML и AI"""
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'ml_prediction': None,
            'ai_analysis': None,
            'final_decision': 'SKIP',
            'final_confidence': 0.0
        }
        
        # 1. ML предсказание (если доступно)
        if self.ml_enabled:
            try:
                klines = await self.bybit_api.get_klines(symbol, "60", limit=200)
                if klines:
                    ml_prediction = await self.ml_predictor.predict(symbol, current_price, klines)
                    result['ml_prediction'] = ml_prediction
                    
                    print(f"🤖 ML Prediction:")
                    print(f"   Price: ${ml_prediction['predicted_price']:,.2f}")
                    print(f"   Direction: {ml_prediction['direction']}")
                    print(f"   Confidence: {ml_prediction['confidence']:.1%}")
                    print(f"   Change: {ml_prediction['change_pct']:+.2f}%")
                else:
                    print("⚠️  No klines data for ML prediction")
            except Exception as e:
                print(f"❌ ML prediction error: {e}")
        
        # 2. AI анализ
        try:
            # Подготавливаем market_data для AI Brain
            market_data = {
                'symbol': symbol,
                'current_price': current_price,
                'timeframe': '1h'
            }
            
            ai_result = await self.ai_brain.analyze_market(market_data)
            
            if ai_result:
                result['ai_analysis'] = ai_result
                print(f"🧠 AI Analysis:")
                print(f"   Decision: {ai_result.get('decision', 'UNKNOWN')}")
                print(f"   Confidence: {ai_result.get('confidence', 0):.1%}")
            else:
                print("❌ AI analysis failed")
        except Exception as e:
            print(f"❌ AI analysis error: {e}")
        
        # 3. Комбинирование решений
        result['final_decision'], result['final_confidence'] = self._combine_predictions(
            result['ml_prediction'], 
            result['ai_analysis']
        )
        
        return result
    
    def _combine_predictions(self, ml_prediction: Dict, ai_analysis: Dict) -> tuple:
        """Комбинирование ML и AI предсказаний"""
        ml_weight = settings.ml_weight if hasattr(settings, 'ml_weight') else 0.4
        ai_weight = settings.ai_weight if hasattr(settings, 'ai_weight') else 0.6
        
        # Если нет ML предсказания, используем только AI
        if not ml_prediction or ml_prediction['direction'] == 'SKIP':
            if ai_analysis:
                decision = ai_analysis.get('decision', 'SKIP')
                confidence = ai_analysis.get('confidence', 0) * ai_weight
                return decision, confidence
            return 'SKIP', 0.0
        
        # Если нет AI анализа, используем только ML
        if not ai_analysis:
            ml_direction = ml_prediction['direction']
            ml_confidence = ml_prediction['confidence'] * ml_weight
            
            if ml_direction == 'UP':
                return 'BUY', ml_confidence
            elif ml_direction == 'DOWN':
                return 'SELL', ml_confidence
            else:
                return 'SKIP', 0.0
        
        # Комбинируем оба предсказания
        ml_direction = ml_prediction['direction']
        ml_confidence = ml_prediction['confidence']
        ai_decision = ai_analysis.get('decision', 'SKIP')
        ai_confidence = ai_analysis.get('confidence', 0)
        
        # Конвертируем ML в торговые решения
        ml_decision = 'SKIP'
        if ml_direction == 'UP':
            ml_decision = 'BUY'
        elif ml_direction == 'DOWN':
            ml_decision = 'SELL'
        
        # Если решения совпадают - усиливаем уверенность
        if ml_decision == ai_decision and ml_decision != 'SKIP':
            combined_confidence = (ml_confidence * ml_weight) + (ai_confidence * ai_weight)
            combined_confidence = min(combined_confidence * 1.2, 0.95)
            return ml_decision, combined_confidence
        
        # Если решения противоречат - пропускаем
        if ml_decision != ai_decision and ml_decision != 'SKIP' and ai_decision != 'SKIP':
            print("⚠️  ML and AI predictions conflict - SKIP")
            return 'SKIP', 0.0
        
        # Если одно из решений SKIP, используем другое с пониженной уверенностью
        if ml_decision == 'SKIP' and ai_decision != 'SKIP':
            return ai_decision, ai_confidence * ai_weight * 0.8
        
        if ai_decision == 'SKIP' and ml_decision != 'SKIP':
            return ml_decision, ml_confidence * ml_weight * 0.8
        
        return 'SKIP', 0.0


# Singleton
_real_trader = None

def get_real_trader() -> RealTrader:
    """Получить singleton instance"""
    global _real_trader
    if _real_trader is None:
        _real_trader = RealTrader()
    return _real_trader
