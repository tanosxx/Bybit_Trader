"""
Simple Futures Executor v2.0 - Упрощённый исполнитель для RSI Grid Strategy

Философия: Простота = Надёжность

Функции:
1. Открытие позиций (LONG/SHORT)
2. Установка TP/SL (фиксированные)
3. Мониторинг позиций
4. Закрытие по TP/SL
5. Управление балансом

Без:
- Сложных фильтров
- Адаптивных параметров
- Trailing stop (пока)
- Funding rate checks (пока)
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from pybit.unified_trading import HTTP
from config_v2 import settings
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from sqlalchemy import select, and_


class SimpleExecutor:
    """
    Простой исполнитель для фьючерсной торговли
    
    Основные функции:
    - Открытие позиций с TP/SL
    - Мониторинг открытых позиций
    - Закрытие по TP/SL
    - Управление виртуальным балансом
    """
    
    def __init__(self):
        """Инициализация исполнителя"""
        self.client = HTTP(
            testnet=settings.bybit_testnet,
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret
        )
        
        # Виртуальный баланс
        self.initial_balance = settings.futures_virtual_balance
        self.current_balance = settings.futures_virtual_balance
        
        # Настройки торговли
        self.leverage = settings.futures_leverage
        self.risk_per_trade = settings.futures_risk_per_trade
        self.margin_mode = settings.futures_margin_mode
        
        # TP/SL
        self.tp_pct = settings.take_profit_pct
        self.sl_pct = settings.stop_loss_pct
        
        # Лимиты
        self.max_positions = settings.futures_max_open_positions
        
        # Кэш инструментов
        self._instruments_cache = {}
        
        print("✅ SimpleExecutor initialized")
        print(f"   Balance: ${self.current_balance}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Risk: {self.risk_per_trade*100}%")
        print(f"   TP: +{self.tp_pct}% | SL: -{self.sl_pct}%")
        print(f"   Max Positions: {self.max_positions}")
    
    async def load_balance_from_db(self):
        """
        Загрузить текущий баланс из БД
        
        Баланс = Initial + Sum(PnL) - Sum(Fees)
        """
        try:
            async with async_session() as session:
                # Получаем все закрытые сделки
                result = await session.execute(
                    select(Trade).where(
                        and_(
                            Trade.status == TradeStatus.CLOSED,
                            Trade.market_type == "futures"
                        )
                    )
                )
                trades = result.scalars().all()
                
                # Рассчитываем баланс
                total_pnl = sum(t.pnl or 0 for t in trades)
                total_fees = sum((t.fee_entry or 0) + (t.fee_exit or 0) for t in trades)
                
                self.current_balance = self.initial_balance + total_pnl - total_fees
                
                print(f"💰 Balance loaded from DB:")
                print(f"   Initial: ${self.initial_balance:.2f}")
                print(f"   PnL: ${total_pnl:+.2f}")
                print(f"   Fees: -${total_fees:.2f}")
                print(f"   Current: ${self.current_balance:.2f}")
                
                return self.current_balance
                
        except Exception as e:
            print(f"❌ Error loading balance: {e}")
            return self.current_balance
    
    async def get_balance(self) -> float:
        """Получить текущий баланс"""
        return self.current_balance
    
    async def get_instrument_info(self, symbol: str) -> Dict:
        """
        Получить информацию об инструменте (tick size, qty step)
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Dict с информацией об инструменте
        """
        if symbol in self._instruments_cache:
            return self._instruments_cache[symbol]
        
        try:
            response = self.client.get_instruments_info(
                category="linear",
                symbol=symbol
            )
            
            if response["retCode"] != 0:
                print(f"❌ Error getting instrument info: {response['retMsg']}")
                return {}
            
            info = response["result"]["list"][0]
            
            # Кэшируем
            self._instruments_cache[symbol] = {
                "tickSize": float(info["priceFilter"]["tickSize"]),
                "qtyStep": float(info["lotSizeFilter"]["qtyStep"]),
                "minQty": float(info["lotSizeFilter"]["minOrderQty"]),
                "maxQty": float(info["lotSizeFilter"]["maxOrderQty"])
            }
            
            return self._instruments_cache[symbol]
            
        except Exception as e:
            print(f"❌ Exception getting instrument info: {e}")
            return {}
    
    def round_price(self, price: float, tick_size: float) -> str:
        """Округлить цену по tick size"""
        decimal_price = Decimal(str(price))
        decimal_tick = Decimal(str(tick_size))
        rounded = (decimal_price / decimal_tick).quantize(Decimal('1'), rounding=ROUND_DOWN) * decimal_tick
        return str(rounded)
    
    def round_quantity(self, quantity: float, qty_step: float) -> str:
        """Округлить количество по qty step"""
        decimal_qty = Decimal(str(quantity))
        decimal_step = Decimal(str(qty_step))
        rounded = (decimal_qty / decimal_step).quantize(Decimal('1'), rounding=ROUND_DOWN) * decimal_step
        return str(rounded)
    
    async def setup_leverage_and_margin(self, symbol: str):
        """
        Установить leverage и margin mode
        
        Args:
            symbol: Торговая пара
        """
        try:
            # Установить leverage
            response = self.client.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(self.leverage),
                sellLeverage=str(self.leverage)
            )
            
            if response["retCode"] != 0:
                print(f"⚠️ Set leverage warning: {response['retMsg']}")
            
            # Установить margin mode
            response = self.client.switch_margin_mode(
                category="linear",
                symbol=symbol,
                tradeMode=1 if self.margin_mode == "ISOLATED" else 0,
                buyLeverage=str(self.leverage),
                sellLeverage=str(self.leverage)
            )
            
            if response["retCode"] != 0:
                # Игнорируем ошибку если margin mode уже установлен
                if "margin mode" not in response["retMsg"].lower():
                    print(f"⚠️ Set margin mode warning: {response['retMsg']}")
            
            print(f"✅ Setup: {symbol} | {self.leverage}x | {self.margin_mode}")
            
        except Exception as e:
            print(f"❌ Setup error: {e}")
    
    async def open_position(
        self,
        symbol: str,
        side: str,  # "LONG" or "SHORT"
        price: float,
        quantity: float,
        reason: str = ""
    ) -> Optional[Dict]:
        """
        Открыть позицию с TP/SL
        
        Args:
            symbol: Торговая пара
            side: LONG или SHORT
            price: Цена входа
            quantity: Количество
            reason: Причина входа
            
        Returns:
            Dict с информацией о позиции или None
        """
        try:
            # Получаем информацию об инструменте
            instrument = await self.get_instrument_info(symbol)
            if not instrument:
                print(f"❌ Cannot get instrument info for {symbol}")
                return None
            
            # Настраиваем leverage и margin
            await self.setup_leverage_and_margin(symbol)
            
            # Округляем цену и количество
            rounded_price = self.round_price(price, instrument["tickSize"])
            rounded_qty = self.round_quantity(quantity, instrument["qtyStep"])
            
            # Рассчитываем TP/SL
            if side == "LONG":
                tp_price = price * (1 + self.tp_pct / 100)
                sl_price = price * (1 - self.sl_pct / 100)
                order_side = "Buy"
            else:  # SHORT
                tp_price = price * (1 - self.tp_pct / 100)
                sl_price = price * (1 + self.sl_pct / 100)
                order_side = "Sell"
            
            # Округляем TP/SL
            tp_price_str = self.round_price(tp_price, instrument["tickSize"])
            sl_price_str = self.round_price(sl_price, instrument["tickSize"])
            
            print(f"\n📤 Opening {side} position:")
            print(f"   Symbol: {symbol}")
            print(f"   Price: {rounded_price}")
            print(f"   Quantity: {rounded_qty}")
            print(f"   TP: {tp_price_str} (+{self.tp_pct}%)")
            print(f"   SL: {sl_price_str} (-{self.sl_pct}%)")
            print(f"   Reason: {reason}")
            
            # Размещаем Market ордер с TP/SL
            response = self.client.place_order(
                category="linear",
                symbol=symbol,
                side=order_side,
                orderType="Market",
                qty=rounded_qty,
                takeProfit=tp_price_str,
                stopLoss=sl_price_str,
                tpslMode="Full",
                positionIdx=0  # One-way mode
            )
            
            if response["retCode"] != 0:
                print(f"❌ Order placement failed: {response['retMsg']}")
                return None
            
            order_id = response["result"]["orderId"]
            
            print(f"✅ Order placed: {order_id}")
            
            # Сохраняем в БД
            await self._save_trade_to_db(
                symbol=symbol,
                side=side,
                entry_price=float(rounded_price),
                quantity=float(rounded_qty),
                tp_price=float(tp_price_str),
                sl_price=float(sl_price_str),
                order_id=order_id,
                reason=reason
            )
            
            return {
                "symbol": symbol,
                "side": side,
                "entry_price": float(rounded_price),
                "quantity": float(rounded_qty),
                "tp_price": float(tp_price_str),
                "sl_price": float(sl_price_str),
                "order_id": order_id
            }
            
        except Exception as e:
            print(f"❌ Exception opening position: {e}")
            return None
    
    async def _save_trade_to_db(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        tp_price: float,
        sl_price: float,
        order_id: str,
        reason: str
    ):
        """Сохранить сделку в БД"""
        try:
            async with async_session() as session:
                trade = Trade(
                    symbol=symbol,
                    side=TradeSide.LONG if side == "LONG" else TradeSide.SHORT,
                    entry_price=entry_price,
                    quantity=quantity,
                    tp_price=tp_price,
                    sl_price=sl_price,
                    status=TradeStatus.OPEN,
                    market_type="futures",
                    entry_time=datetime.now(),
                    order_id=order_id,
                    reason=reason
                )
                
                session.add(trade)
                await session.commit()
                
                print(f"💾 Trade saved to DB: {symbol} {side}")
                
        except Exception as e:
            print(f"❌ Error saving trade: {e}")
    
    async def get_open_positions(self) -> List[Dict]:
        """
        Получить открытые позиции из БД
        
        Returns:
            Список открытых позиций
        """
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Trade).where(
                        and_(
                            Trade.status == TradeStatus.OPEN,
                            Trade.market_type == "futures"
                        )
                    )
                )
                trades = result.scalars().all()
                
                positions = []
                for trade in trades:
                    positions.append({
                        "symbol": trade.symbol,
                        "side": trade.side.value,
                        "entry_price": trade.entry_price,
                        "quantity": trade.quantity,
                        "tp_price": trade.tp_price,
                        "sl_price": trade.sl_price,
                        "entry_time": trade.entry_time,
                        "order_id": trade.order_id
                    })
                
                return positions
                
        except Exception as e:
            print(f"❌ Error getting positions: {e}")
            return []
    
    async def check_positions(self):
        """
        Проверить открытые позиции и обновить статус
        
        Проверяет на бирже статус позиций и обновляет БД
        Если позиция закрыта (по TP/SL), рассчитывает PnL
        """
        positions = await self.get_open_positions()
        
        for pos in positions:
            try:
                # Получаем текущую позицию с биржи
                response = self.client.get_positions(
                    category="linear",
                    symbol=pos["symbol"]
                )
                
                if response["retCode"] != 0:
                    continue
                
                # Проверяем есть ли позиция
                bybit_positions = response["result"]["list"]
                
                # Если позиции нет на бирже - значит закрыта (по TP/SL)
                if not bybit_positions or float(bybit_positions[0]["size"]) == 0:
                    print(f"📊 Position closed on exchange: {pos['symbol']}")
                    await self._close_position_in_db(pos["symbol"], pos["order_id"])
                
            except Exception as e:
                print(f"⚠️ Error checking position {pos['symbol']}: {e}")
    
    async def close_position(self, symbol: str, reason: str = "Manual close") -> bool:
        """
        Закрыть позицию вручную (для /panic или других случаев)
        
        Args:
            symbol: Торговая пара
            reason: Причина закрытия
            
        Returns:
            True если успешно закрыто
        """
        try:
            # Получаем открытую позицию из БД
            async with async_session() as session:
                result = await session.execute(
                    select(Trade).where(
                        and_(
                            Trade.symbol == symbol,
                            Trade.status == TradeStatus.OPEN,
                            Trade.market_type == "futures"
                        )
                    )
                )
                trade = result.scalar_one_or_none()
                
                if not trade:
                    print(f"⚠️ No open position found for {symbol}")
                    return False
                
                # Получаем текущую позицию с биржи
                response = self.client.get_positions(
                    category="linear",
                    symbol=symbol
                )
                
                if response["retCode"] != 0:
                    print(f"❌ Error getting position: {response['retMsg']}")
                    return False
                
                positions = response["result"]["list"]
                if not positions or float(positions[0]["size"]) == 0:
                    print(f"⚠️ No position on exchange for {symbol}")
                    # Закрываем в БД
                    await self._close_position_in_db(symbol, trade.order_id)
                    return True
                
                # Закрываем позицию Market ордером
                bybit_position = positions[0]
                side = "Sell" if bybit_position["side"] == "Buy" else "Buy"
                qty = bybit_position["size"]
                
                print(f"\n📤 Closing position:")
                print(f"   Symbol: {symbol}")
                print(f"   Side: {side}")
                print(f"   Quantity: {qty}")
                print(f"   Reason: {reason}")
                
                response = self.client.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side,
                    orderType="Market",
                    qty=qty,
                    positionIdx=0,
                    reduceOnly=True
                )
                
                if response["retCode"] != 0:
                    print(f"❌ Close order failed: {response['retMsg']}")
                    return False
                
                print(f"✅ Position closed: {symbol}")
                
                # Обновляем в БД
                await self._close_position_in_db(symbol, trade.order_id)
                
                return True
                
        except Exception as e:
            print(f"❌ Exception closing position: {e}")
            return False
    
    async def _close_position_in_db(self, symbol: str, order_id: str):
        """Закрыть позицию в БД и рассчитать PnL"""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Trade).where(
                        and_(
                            Trade.symbol == symbol,
                            Trade.order_id == order_id,
                            Trade.status == TradeStatus.OPEN
                        )
                    )
                )
                trade = result.scalar_one_or_none()
                
                if trade:
                    # Получаем текущую цену с биржи
                    try:
                        ticker_response = self.client.get_tickers(
                            category="linear",
                            symbol=symbol
                        )
                        
                        if ticker_response["retCode"] == 0:
                            current_price = float(ticker_response["result"]["list"][0]["lastPrice"])
                            
                            # Рассчитываем PnL
                            if trade.side == TradeSide.LONG:
                                pnl = (current_price - trade.entry_price) * trade.quantity
                            else:  # SHORT
                                pnl = (trade.entry_price - current_price) * trade.quantity
                            
                            # Рассчитываем комиссию выхода
                            exit_value = current_price * trade.quantity
                            fee_exit = exit_value * settings.estimated_fee_rate
                            
                            # Обновляем trade
                            trade.exit_price = current_price
                            trade.pnl = pnl
                            trade.fee_exit = fee_exit
                            trade.status = TradeStatus.CLOSED
                            trade.exit_time = datetime.now()
                            
                            # Обновляем баланс
                            net_pnl = pnl - fee_exit
                            self.current_balance += net_pnl
                            
                            print(f"💰 PnL: ${pnl:.2f} | Fee: ${fee_exit:.2f} | Net: ${net_pnl:.2f}")
                            print(f"💰 New Balance: ${self.current_balance:.2f}")
                        else:
                            # Если не получили цену, просто закрываем
                            trade.status = TradeStatus.CLOSED
                            trade.exit_time = datetime.now()
                            
                    except Exception as e:
                        print(f"⚠️ Error getting exit price: {e}")
                        trade.status = TradeStatus.CLOSED
                        trade.exit_time = datetime.now()
                    
                    await session.commit()
                    
                    print(f"✅ Position closed in DB: {symbol}")
                    
        except Exception as e:
            print(f"❌ Error closing position in DB: {e}")


# ========== SINGLETON ==========

_simple_executor: Optional[SimpleExecutor] = None

def get_simple_executor() -> SimpleExecutor:
    """Получить singleton SimpleExecutor"""
    global _simple_executor
    if _simple_executor is None:
        _simple_executor = SimpleExecutor()
    return _simple_executor
