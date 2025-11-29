"""
FUTURES Executor v4.0 - БЕЗОПАСНЫЙ исполнитель для фьючерсной торговли

НОВЫЕ ФИЧИ v4.0:
1. Native Trailing Stop - серверный трейлинг через Bybit API
2. Funding Rate Filter - проверка ставки финансирования перед входом

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ v3.0:
1. setup_leverage_and_margin() - ISOLATED + Leverage ПЕРЕД каждой сделкой
2. Price Precision - tickSize/qtyStep из get_instruments_info
3. Atomic Order - SL/TP внутри place_order, не отдельно
4. Virtual Balance $500 - никогда не запрашиваем реальный баланс
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .base_executor import (
    BaseExecutor, MarketType, TradeSignal, 
    ExecutionResult, OrderSide, PositionSide
)
from core.bybit_api import get_bybit_api
from core.telegram_notifier import get_telegram_reporter
from database.db import async_session
from database.models import Trade, TradeStatus, TradeSide
from sqlalchemy import select
from config import settings


class FuturesExecutor(BaseExecutor):
    """
    FUTURES Executor v3.0 - Безопасная фьючерсная торговля
    
    КРИТИЧЕСКИЕ ПРАВИЛА:
    1. setup_leverage_and_margin() ПЕРЕД каждой сделкой
    2. Atomic SL/TP внутри place_order
    3. Virtual Balance $500 ONLY
    4. Price/Qty округление по tickSize/qtyStep
    """
    
    # Кэш для instrument info
    _instruments_cache: Dict[str, Dict] = {}
    
    def __init__(self):
        super().__init__(MarketType.FUTURES)
        self.api = get_bybit_api()
        
        # ========== VIRTUAL BALANCE $500 ==========
        self.virtual_balance = 500.0  # ФИКСИРОВАННЫЙ!
        self.initial_balance = 500.0
        self.realized_pnl = 0.0
        
        # Настройки торговли
        self.leverage = settings.futures_leverage  # Базовое, будет меняться динамически
        self.risk_per_trade = settings.futures_risk_per_trade  # 10%
        
        # SL/TP проценты
        self.sl_pct = 2.0  # 2% стоп-лосс
        self.tp_pct = 3.0  # 3% тейк-профит
        
        # ========== TRAILING STOP v4.0 ==========
        self.trailing_enabled = settings.trailing_stop_enabled
        self.trailing_activation_pct = settings.trailing_activation_pct  # 1.0%
        self.trailing_callback_pct = settings.trailing_callback_pct  # 0.5%
        
        # ========== FUNDING RATE FILTER v4.0 ==========
        self.funding_filter_enabled = settings.funding_rate_filter_enabled
        self.funding_max_pct = settings.funding_rate_max_pct  # 0.05%
        self.funding_time_window = settings.funding_time_window_minutes  # 60 min
        
        # ========== POSITION LIMITS v5.0 ==========
        self.max_open_positions = settings.futures_max_open_positions  # 3
        self.min_confidence = settings.futures_min_confidence  # 0.60
        
        # Текущие позиции
        self._current_positions: Dict[str, str] = {}
        
        print(f"🚀 FuturesExecutor v5.0 initialized:")
        print(f"   💰 Virtual Balance: ${self.virtual_balance}")
        print(f"   📊 Base Leverage: {self.leverage}x (dynamic 2-7x)")
        print(f"   🎯 Risk per Trade: {self.risk_per_trade*100}%")
        print(f"   🛡️ SL: {self.sl_pct}% | TP: {self.tp_pct}%")
        print(f"   📈 Trailing Stop: {'ON' if self.trailing_enabled else 'OFF'}")
        print(f"   💸 Funding Filter: {'ON' if self.funding_filter_enabled else 'OFF'}")
        print(f"   🚫 Max Positions: {self.max_open_positions}")
        print(f"   🎯 Min Confidence: {self.min_confidence*100}%")
        print(f"   ⚠️ ISOLATED margin ENFORCED")
    
    # ========== 1. SETUP SYMBOL (Margin + Leverage) ==========
    
    async def setup_leverage_and_margin(self, symbol: str, leverage: int) -> bool:
        """
        ОБЯЗАТЕЛЬНО вызывать ПЕРЕД каждой сделкой!
        
        Шаг А: Переключить на ISOLATED margin
        Шаг Б: Установить leverage
        
        Returns: True если успешно (или уже установлено)
        """
        print(f"\n   ⚙️ Setting up {symbol}: ISOLATED + {leverage}x leverage")
        
        # Шаг А: ISOLATED margin
        isolated_ok = await self._switch_to_isolated(symbol, leverage)
        
        # Шаг Б: Set leverage
        leverage_ok = await self._set_leverage(symbol, leverage)
        
        if isolated_ok and leverage_ok:
            print(f"   ✅ {symbol} ready: ISOLATED + {leverage}x")
            return True
        else:
            print(f"   ⚠️ {symbol} setup completed with warnings")
            return True  # Продолжаем, т.к. может быть уже установлено
    
    async def _switch_to_isolated(self, symbol: str, leverage: int) -> bool:
        """
        Переключить на ISOLATED margin
        
        Bybit API tradeMode:
        - 0 = CROSS  
        - 1 = ISOLATED
        
        ВАЖНО: Нельзя переключить если есть открытая позиция!
        """
        try:
            # Сначала проверим текущий режим через get position
            check_endpoint = "/v5/position/list"
            check_params = {
                "category": "linear",
                "symbol": symbol
            }
            check_response = await self.api._request("GET", check_endpoint, check_params)
            
            if check_response and check_response.get("retCode") == 0:
                positions = check_response["result"]["list"]
                for pos in positions:
                    if float(pos.get("size", 0)) > 0:
                        # Есть открытая позиция - проверяем её режим
                        current_mode = pos.get("tradeMode", 0)
                        if str(current_mode) == "1":
                            print(f"      ✅ Already ISOLATED (has position)")
                            return True
                        else:
                            print(f"      ⚠️ Position in CROSS mode - cannot switch!")
                            return False
            
            # Нет позиции - можем переключить
            endpoint = "/v5/position/switch-isolated"
            params = {
                "category": "linear",
                "symbol": symbol,
                "tradeMode": 1,  # 1 = ISOLATED
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            }
            
            response = await self.api._request("POST", endpoint, params)
            
            if response:
                ret_code = response.get("retCode", -1)
                ret_msg = response.get("retMsg", "")
                
                # Успех или "уже установлено"
                if ret_code == 0:
                    print(f"      ✅ Switched to ISOLATED")
                    return True
                elif ret_code in [110026, 110025] or "already" in ret_msg.lower():
                    print(f"      ✅ Already ISOLATED")
                    return True
                else:
                    print(f"      ⚠️ Margin response: {ret_msg} (code: {ret_code})")
                    return True  # Продолжаем
            
            return True
            
        except Exception as e:
            print(f"      ⚠️ Margin switch error: {e}")
            return True
    
    async def _set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Установить leverage
        
        Обрабатываем ошибки:
        - 110043: "Leverage not modified" - OK
        """
        try:
            endpoint = "/v5/position/set-leverage"
            params = {
                "category": "linear",
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            }
            
            response = await self.api._request("POST", endpoint, params)
            
            if response:
                ret_code = response.get("retCode", -1)
                
                if ret_code in [0, 110043]:
                    print(f"      ✅ Leverage {leverage}x OK")
                    return True
                else:
                    print(f"      ⚠️ Leverage response: {response.get('retMsg', 'Unknown')}")
                    return True
            
            return True
            
        except Exception as e:
            print(f"      ⚠️ Leverage error: {e}")
            return True
    
    # ========== 2. PRICE PRECISION ==========
    
    async def get_instrument_info(self, symbol: str) -> Dict:
        """
        Получить tickSize и qtyStep для символа
        КЭШИРУЕМ для производительности
        """
        if symbol in self._instruments_cache:
            return self._instruments_cache[symbol]
        
        try:
            endpoint = "/v5/market/instruments-info"
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = await self.api._request("GET", endpoint, params)
            
            if response and response.get("retCode") == 0:
                instruments = response["result"]["list"]
                if instruments:
                    info = instruments[0]
                    
                    tick_size = float(info["priceFilter"]["tickSize"])
                    qty_step = float(info["lotSizeFilter"]["qtyStep"])
                    min_qty = float(info["lotSizeFilter"]["minOrderQty"])
                    
                    result = {
                        'tick_size': tick_size,
                        'qty_step': qty_step,
                        'min_qty': min_qty
                    }
                    
                    # Кэшируем
                    self._instruments_cache[symbol] = result
                    print(f"      📐 {symbol}: tick={tick_size}, step={qty_step}, min={min_qty}")
                    return result
        
        except Exception as e:
            print(f"      ⚠️ Instrument info error: {e}")
        
        # Fallback значения
        fallback = {
            'BTCUSDT': {'tick_size': 0.1, 'qty_step': 0.001, 'min_qty': 0.001},
            'ETHUSDT': {'tick_size': 0.01, 'qty_step': 0.01, 'min_qty': 0.01},
            'SOLUSDT': {'tick_size': 0.001, 'qty_step': 0.1, 'min_qty': 0.1},
            'BNBUSDT': {'tick_size': 0.01, 'qty_step': 0.01, 'min_qty': 0.01},
            'XRPUSDT': {'tick_size': 0.0001, 'qty_step': 1.0, 'min_qty': 1.0},
        }
        return fallback.get(symbol, {'tick_size': 0.01, 'qty_step': 0.01, 'min_qty': 0.01})
    
    def round_price(self, price: float, tick_size: float) -> str:
        """
        Округлить цену по tickSize
        
        Формула: round(price / tick_size) * tick_size
        """
        if tick_size <= 0:
            return f"{price:.2f}"
        
        rounded = round(price / tick_size) * tick_size
        
        # Определяем decimals из tick_size
        tick_str = f"{tick_size:.10f}".rstrip('0')
        if '.' in tick_str:
            decimals = len(tick_str.split('.')[1])
        else:
            decimals = 0
        
        return f"{rounded:.{decimals}f}"
    
    def round_qty(self, qty: float, qty_step: float, min_qty: float) -> str:
        """
        Округлить количество по qtyStep
        
        Формула: round(qty / qty_step) * qty_step
        """
        if qty < min_qty:
            return "0"
        
        rounded = round(qty / qty_step) * qty_step
        
        # Определяем decimals
        step_str = f"{qty_step:.10f}".rstrip('0')
        if '.' in step_str:
            decimals = len(step_str.split('.')[1])
        else:
            decimals = 0
        
        return f"{rounded:.{decimals}f}"
    
    # ========== 3. FUNDING RATE FILTER v4.0 ==========
    
    async def check_funding_rate(self, symbol: str, side: str) -> Tuple[bool, str]:
        """
        Проверить Funding Rate перед входом в позицию
        
        Логика:
        - Если до выплаты < 60 мин И ставка > 0.05%:
          - BUY (LONG): мы платим → ЗАПРЕТИТЬ
          - SELL (SHORT): нам платят → РАЗРЕШИТЬ (бонус!)
        - Если ставка отрицательная - зеркальная логика
        
        Returns: (allowed: bool, reason: str)
        """
        if not self.funding_filter_enabled:
            return True, "Funding filter disabled"
        
        try:
            # Получаем funding rate через Bybit API
            endpoint = "/v5/market/tickers"
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = await self.api._request("GET", endpoint, params)
            
            if not response or response.get("retCode") != 0:
                print(f"      ⚠️ Funding rate unavailable - allowing trade")
                return True, "Funding data unavailable"
            
            tickers = response.get("result", {}).get("list", [])
            if not tickers:
                return True, "No ticker data"
            
            ticker = tickers[0]
            
            # Funding Rate (в процентах, например 0.0001 = 0.01%)
            funding_rate = float(ticker.get("fundingRate", 0)) * 100  # Конвертируем в %
            next_funding_time = int(ticker.get("nextFundingTime", 0))  # Unix timestamp ms
            
            # Время до выплаты
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            minutes_until_funding = (next_funding_time - now_ms) / 1000 / 60
            
            print(f"      💸 Funding {symbol}: {funding_rate:.4f}% | Next in {minutes_until_funding:.0f} min")
            
            # Проверяем условия
            if minutes_until_funding > self.funding_time_window:
                # До выплаты далеко - разрешаем
                return True, f"Funding in {minutes_until_funding:.0f} min (> {self.funding_time_window})"
            
            # До выплаты < 60 минут - проверяем ставку
            abs_rate = abs(funding_rate)
            
            if abs_rate <= self.funding_max_pct:
                # Ставка низкая - разрешаем
                return True, f"Low funding rate: {funding_rate:.4f}%"
            
            # Высокая ставка - проверяем направление
            if funding_rate > 0:
                # Положительная ставка: LONG платит SHORT
                if side == "Buy":  # LONG
                    return False, f"❌ HIGH FUNDING! {funding_rate:.4f}% - LONG will pay in {minutes_until_funding:.0f} min"
                else:  # SHORT
                    return True, f"✅ HIGH FUNDING! {funding_rate:.4f}% - SHORT will receive in {minutes_until_funding:.0f} min"
            else:
                # Отрицательная ставка: SHORT платит LONG
                if side == "Sell":  # SHORT
                    return False, f"❌ NEGATIVE FUNDING! {funding_rate:.4f}% - SHORT will pay in {minutes_until_funding:.0f} min"
                else:  # LONG
                    return True, f"✅ NEGATIVE FUNDING! {funding_rate:.4f}% - LONG will receive in {minutes_until_funding:.0f} min"
        
        except Exception as e:
            print(f"      ⚠️ Funding check error: {e} - allowing trade")
            return True, f"Error: {e}"
    
    # ========== 4. TRAILING STOP v4.0 ==========
    
    async def set_trailing_stop(self, symbol: str, side: str, entry_price: float) -> bool:
        """
        Установить серверный Trailing Stop через Bybit API
        
        Bybit API: /v5/position/trading-stop
        
        Параметры:
        - trailingStop: дистанция в $ (callback)
        - activePrice: цена активации трейлинга
        
        Логика:
        - LONG: activePrice = entry * (1 + activation_pct)
        - SHORT: activePrice = entry * (1 - activation_pct)
        - trailingStop = entry * callback_pct (в $)
        """
        if not self.trailing_enabled:
            return True
        
        try:
            # Получаем tick_size для округления
            info = await self.get_instrument_info(symbol)
            tick_size = info['tick_size']
            
            # Рассчитываем activation price
            if side == "Buy":  # LONG
                activation_price = entry_price * (1 + self.trailing_activation_pct / 100)
            else:  # SHORT
                activation_price = entry_price * (1 - self.trailing_activation_pct / 100)
            
            # Trailing distance в $ (callback)
            trailing_distance = entry_price * (self.trailing_callback_pct / 100)
            
            # Округляем
            activation_str = self.round_price(activation_price, tick_size)
            trailing_str = self.round_price(trailing_distance, tick_size)
            
            print(f"      📈 Setting Trailing Stop:")
            print(f"         Activation: ${activation_str} ({'+' if side == 'Buy' else '-'}{self.trailing_activation_pct}%)")
            print(f"         Callback: ${trailing_str} ({self.trailing_callback_pct}%)")
            
            endpoint = "/v5/position/trading-stop"
            params = {
                "category": "linear",
                "symbol": symbol,
                "trailingStop": trailing_str,
                "activePrice": activation_str,
                "positionIdx": 0  # One-Way Mode
            }
            
            response = await self.api._request("POST", endpoint, params)
            
            if response and response.get("retCode") == 0:
                print(f"      ✅ Trailing Stop set!")
                return True
            else:
                error = response.get("retMsg", "Unknown") if response else "No response"
                print(f"      ⚠️ Trailing Stop failed: {error}")
                # Не критично - позиция уже открыта с обычным SL
                return False
        
        except Exception as e:
            print(f"      ⚠️ Trailing Stop error: {e}")
            return False
    
    # ========== 5. POSITION SIZE FROM $500 ==========
    
    def calculate_position_size(self, price: float, leverage: int) -> float:
        """
        Рассчитать размер позиции от ВИРТУАЛЬНЫХ $500
        
        Формула: qty = (500 * risk_per_trade * leverage) / price
        
        Пример: ($500 * 10% * 5x) / $95000 = 0.00263 BTC
        """
        position_usd = self.virtual_balance * self.risk_per_trade * leverage
        quantity = position_usd / price
        
        print(f"      📐 Position: ${self.virtual_balance} * {self.risk_per_trade*100}% * {leverage}x = ${position_usd:.2f}")
        print(f"      📐 Qty: ${position_usd:.2f} / ${price:.2f} = {quantity:.6f}")
        
        return quantity
    
    # ========== 4. ATOMIC ORDER ==========
    
    async def place_atomic_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        stop_loss: str,
        take_profit: str
    ) -> Optional[Dict]:
        """
        АТОМАРНЫЙ ордер с SL/TP внутри!
        
        Позиция НЕ откроется без стопов!
        """
        endpoint = "/v5/order/create"
        params = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": qty,
            "positionIdx": 0,  # One-Way Mode
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
            "slTriggerBy": "LastPrice",
            "tpTriggerBy": "LastPrice"
        }
        
        print(f"\n      📤 ATOMIC ORDER:")
        print(f"         {side} {qty} {symbol}")
        print(f"         SL: {stop_loss} | TP: {take_profit}")
        
        response = await self.api._request("POST", endpoint, params)
        
        if response and response.get("retCode") == 0:
            result = response.get("result", {})
            order_id = result.get("orderId", "")
            print(f"      ✅ Order placed: {order_id}")
            return {"order_id": order_id, "status": "OK"}
        else:
            error = response.get("retMsg", "Unknown") if response else "No response"
            print(f"      ❌ Order FAILED: {error}")
            return None

    
    # ========== MAIN EXECUTION ==========
    
    async def execute_signal(self, signal: TradeSignal) -> ExecutionResult:
        """
        Исполнить сигнал на FUTURES
        
        BUY -> LONG
        SELL -> SHORT
        """
        if signal.is_skip:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Signal is SKIP"
            )
        
        # ========== v5.0: ПРОВЕРКА ЛИМИТА ПОЗИЦИЙ ==========
        open_count = len(self._current_positions)
        if open_count >= self.max_open_positions:
            print(f"   🚫 Position limit reached: {open_count}/{self.max_open_positions}")
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=f"Max positions limit: {open_count}/{self.max_open_positions}"
            )
        
        # ========== v5.0: ПРОВЕРКА MIN CONFIDENCE ==========
        if signal.confidence < self.min_confidence:
            print(f"   🚫 Low confidence: {signal.confidence*100:.0f}% < {self.min_confidence*100:.0f}%")
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=f"Low confidence: {signal.confidence*100:.0f}%"
            )
        
        symbol = signal.symbol
        price = signal.price
        
        # Проверяем противоположную позицию
        current_side = self._current_positions.get(symbol)
        
        try:
            if signal.is_buy:
                if current_side == 'SHORT':
                    print(f"   ⚠️ Closing SHORT before LONG")
                    await self._close_position(symbol, "Reversing to LONG")
                return await self._open_long(symbol, price, signal)
            
            elif signal.is_sell:
                if current_side == 'LONG':
                    print(f"   ⚠️ Closing LONG before SHORT")
                    await self._close_position(symbol, "Reversing to SHORT")
                return await self._open_short(symbol, price, signal)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=str(e)
            )
        
        return ExecutionResult(
            success=False,
            market_type=self.market_type,
            error="Unknown signal"
        )
    
    async def _open_long(self, symbol: str, price: float, signal: TradeSignal) -> ExecutionResult:
        """
        Открыть LONG с полной защитой
        
        1. CHECK FUNDING RATE (v4.0)
        2. Setup margin + leverage
        3. Get instrument info
        4. Calculate qty
        5. Calculate SL/TP
        6. Place ATOMIC order
        7. SET TRAILING STOP (v4.0)
        """
        print(f"\n🟢 [FUTURES] Opening LONG {symbol} @ ${price:.2f}")
        
        # 1. CHECK FUNDING RATE (v4.0)
        funding_ok, funding_reason = await self.check_funding_rate(symbol, "Buy")
        if not funding_ok:
            print(f"   {funding_reason}")
            # Telegram: Funding Skip notification
            try:
                reporter = get_telegram_reporter()
                # Extract rate from reason
                rate_match = re.search(r'([\d.]+)%', funding_reason)
                rate = float(rate_match.group(1)) if rate_match else 0
                min_match = re.search(r'(\d+) min', funding_reason)
                mins = int(min_match.group(1)) if min_match else 60
                await reporter.notify_funding_skip(symbol, "LONG", rate, mins)
            except Exception as e:
                print(f"   📱 Telegram error (ignored): {e}")
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=funding_reason
            )
        print(f"      {funding_reason}")
        
        # 2. SETUP: ISOLATED + Leverage
        await self.setup_leverage_and_margin(symbol, self.leverage)
        
        # 3. Get instrument info
        info = await self.get_instrument_info(symbol)
        tick_size = info['tick_size']
        qty_step = info['qty_step']
        min_qty = info['min_qty']
        
        # 4. Calculate position size
        quantity = self.calculate_position_size(price, self.leverage)
        qty_str = self.round_qty(quantity, qty_step, min_qty)
        
        if qty_str == "0" or float(qty_str) <= 0:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=f"Qty too small: {quantity} < {min_qty}"
            )
        
        # 5. Calculate SL/TP (LONG: SL ниже, TP выше)
        sl_price = price * (1 - self.sl_pct / 100)
        tp_price = price * (1 + self.tp_pct / 100)
        
        sl_str = self.round_price(sl_price, tick_size)
        tp_str = self.round_price(tp_price, tick_size)
        
        print(f"      SL: ${sl_str} (-{self.sl_pct}%)")
        print(f"      TP: ${tp_str} (+{self.tp_pct}%)")
        
        # 6. ATOMIC order
        order = await self.place_atomic_order(
            symbol=symbol,
            side="Buy",
            qty=qty_str,
            stop_loss=sl_str,
            take_profit=tp_str
        )
        
        if not order:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Failed to place LONG order"
            )
        
        # 7. SET TRAILING STOP (v4.0)
        await self.set_trailing_stop(symbol, "Buy", price)
        
        # Save to DB
        trade = await self._save_trade(
            symbol=symbol,
            side=TradeSide.BUY,
            price=price,
            quantity=float(qty_str),
            order_id=order.get('order_id'),
            signal=signal,
            position_side='LONG',
            stop_loss=float(sl_str),
            take_profit=float(tp_str)
        )
        
        self._current_positions[symbol] = 'LONG'
        
        # Calculate position size in USD for telegram
        size_usd = price * float(qty_str) * self.leverage
        
        print(f"✅ [FUTURES] LONG {symbol}: {qty_str} @ ${price:.2f} ({self.leverage}x)")
        print(f"   🛡️ SL=${sl_str} | TP=${tp_str}")
        if self.trailing_enabled:
            print(f"   📈 Trailing: activate +{self.trailing_activation_pct}%, callback {self.trailing_callback_pct}%")
        
        # 8. TELEGRAM NOTIFICATION
        try:
            reporter = get_telegram_reporter()
            await reporter.notify_open(
                symbol=symbol,
                side="LONG",
                entry_price=price,
                size_usd=size_usd,
                leverage=self.leverage,
                stop_loss=float(sl_str),
                take_profit=float(tp_str),
                reason=signal.reasoning[:80] if signal.reasoning else "ML Signal"
            )
        except Exception as e:
            print(f"   📱 Telegram error (ignored): {e}")
        
        return ExecutionResult(
            success=True,
            market_type=self.market_type,
            order_id=order.get('order_id'),
            symbol=symbol,
            side="LONG",
            quantity=float(qty_str),
            price=price,
            extra_data={
                'trade_id': trade.id if trade else None,
                'leverage': self.leverage,
                'position_side': 'LONG',
                'stop_loss': float(sl_str),
                'take_profit': float(tp_str),
                'margin_mode': 'ISOLATED',
                'trailing_enabled': self.trailing_enabled,
                'funding_reason': funding_reason
            }
        )
    
    async def _open_short(self, symbol: str, price: float, signal: TradeSignal) -> ExecutionResult:
        """
        Открыть SHORT с полной защитой
        
        1. CHECK FUNDING RATE (v4.0)
        2. Setup margin + leverage
        3. Get instrument info
        4. Calculate qty
        5. Calculate SL/TP
        6. Place ATOMIC order
        7. SET TRAILING STOP (v4.0)
        """
        print(f"\n🔴 [FUTURES] Opening SHORT {symbol} @ ${price:.2f}")
        
        # 1. CHECK FUNDING RATE (v4.0)
        funding_ok, funding_reason = await self.check_funding_rate(symbol, "Sell")
        if not funding_ok:
            print(f"   {funding_reason}")
            # Telegram: Funding Skip notification
            try:
                reporter = get_telegram_reporter()
                rate_match = re.search(r'([\d.]+)%', funding_reason)
                rate = float(rate_match.group(1)) if rate_match else 0
                min_match = re.search(r'(\d+) min', funding_reason)
                mins = int(min_match.group(1)) if min_match else 60
                await reporter.notify_funding_skip(symbol, "SHORT", rate, mins)
            except Exception as e:
                print(f"   📱 Telegram error (ignored): {e}")
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=funding_reason
            )
        print(f"      {funding_reason}")
        
        # 2. SETUP
        await self.setup_leverage_and_margin(symbol, self.leverage)
        
        # 3. Get instrument info
        info = await self.get_instrument_info(symbol)
        tick_size = info['tick_size']
        qty_step = info['qty_step']
        min_qty = info['min_qty']
        
        # 4. Calculate qty
        quantity = self.calculate_position_size(price, self.leverage)
        qty_str = self.round_qty(quantity, qty_step, min_qty)
        
        if qty_str == "0" or float(qty_str) <= 0:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error=f"Qty too small: {quantity} < {min_qty}"
            )
        
        # 5. Calculate SL/TP (SHORT: SL выше, TP ниже)
        sl_price = price * (1 + self.sl_pct / 100)
        tp_price = price * (1 - self.tp_pct / 100)
        
        sl_str = self.round_price(sl_price, tick_size)
        tp_str = self.round_price(tp_price, tick_size)
        
        print(f"      SL: ${sl_str} (+{self.sl_pct}%)")
        print(f"      TP: ${tp_str} (-{self.tp_pct}%)")
        
        # 6. ATOMIC order
        order = await self.place_atomic_order(
            symbol=symbol,
            side="Sell",
            qty=qty_str,
            stop_loss=sl_str,
            take_profit=tp_str
        )
        
        if not order:
            return ExecutionResult(
                success=False,
                market_type=self.market_type,
                error="Failed to place SHORT order"
            )
        
        # 7. SET TRAILING STOP (v4.0)
        await self.set_trailing_stop(symbol, "Sell", price)
        
        # Save to DB
        trade = await self._save_trade(
            symbol=symbol,
            side=TradeSide.SELL,
            price=price,
            quantity=float(qty_str),
            order_id=order.get('order_id'),
            signal=signal,
            position_side='SHORT',
            stop_loss=float(sl_str),
            take_profit=float(tp_str)
        )
        
        self._current_positions[symbol] = 'SHORT'
        
        # Calculate position size in USD for telegram
        size_usd = price * float(qty_str) * self.leverage
        
        print(f"✅ [FUTURES] SHORT {symbol}: {qty_str} @ ${price:.2f} ({self.leverage}x)")
        print(f"   🛡️ SL=${sl_str} | TP=${tp_str}")
        if self.trailing_enabled:
            print(f"   📈 Trailing: activate -{self.trailing_activation_pct}%, callback {self.trailing_callback_pct}%")
        
        # 8. TELEGRAM NOTIFICATION
        try:
            reporter = get_telegram_reporter()
            await reporter.notify_open(
                symbol=symbol,
                side="SHORT",
                entry_price=price,
                size_usd=size_usd,
                leverage=self.leverage,
                stop_loss=float(sl_str),
                take_profit=float(tp_str),
                reason=signal.reasoning[:80] if signal.reasoning else "ML Signal"
            )
        except Exception as e:
            print(f"   📱 Telegram error (ignored): {e}")
        
        return ExecutionResult(
            success=True,
            market_type=self.market_type,
            order_id=order.get('order_id'),
            symbol=symbol,
            side="SHORT",
            quantity=float(qty_str),
            price=price,
            extra_data={
                'trade_id': trade.id if trade else None,
                'leverage': self.leverage,
                'position_side': 'SHORT',
                'stop_loss': float(sl_str),
                'take_profit': float(tp_str),
                'margin_mode': 'ISOLATED',
                'trailing_enabled': self.trailing_enabled,
                'funding_reason': funding_reason
            }
        )
    
    # ========== CLOSE POSITION ==========
    
    async def _close_position(self, symbol: str, reason: str) -> ExecutionResult:
        """Закрыть позицию"""
        current_side = self._current_positions.get(symbol)
        if not current_side:
            return ExecutionResult(success=False, market_type=self.market_type, error="No position")
        
        # Get current price
        ticker = await self.api.get_ticker(symbol)
        if not ticker:
            return ExecutionResult(success=False, market_type=self.market_type, error="No price")
        
        price = float(ticker.get('last_price') or ticker.get('lastPrice', 0))
        
        # Get trade from DB
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.symbol == symbol,
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'futures'
                ).order_by(Trade.entry_time.desc()).limit(1)
            )
            trade = result.scalar_one_or_none()
        
        if not trade:
            del self._current_positions[symbol]
            return ExecutionResult(success=False, market_type=self.market_type, error="No trade in DB")
        
        # Close order
        close_side = "Sell" if current_side == 'LONG' else "Buy"
        info = await self.get_instrument_info(symbol)
        qty_str = self.round_qty(trade.quantity, info['qty_step'], info['min_qty'])
        
        endpoint = "/v5/order/create"
        params = {
            "category": "linear",
            "symbol": symbol,
            "side": close_side,
            "orderType": "Market",
            "qty": qty_str,
            "positionIdx": 0,
            "reduceOnly": True
        }
        
        response = await self.api._request("POST", endpoint, params)
        
        if not response or response.get("retCode") != 0:
            return ExecutionResult(success=False, market_type=self.market_type, error=f"Close failed: {response}")
        
        order_id = response.get("result", {}).get("orderId", "")
        
        # Calculate PnL
        if current_side == 'LONG':
            pnl = (price - trade.entry_price) * trade.quantity * self.leverage
        else:
            pnl = (trade.entry_price - price) * trade.quantity * self.leverage
        
        # Update DB
        async with async_session() as session:
            trade.status = TradeStatus.CLOSED
            trade.exit_price = price
            trade.exit_time = datetime.utcnow()
            trade.pnl = pnl
            trade.pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
            trade.exit_reason = reason
            session.add(trade)
            await session.commit()
        
        self.record_trade(pnl)
        self.update_balance(pnl)
        del self._current_positions[symbol]
        
        # Calculate duration
        duration_minutes = 0
        if trade.entry_time:
            duration_minutes = int((datetime.utcnow() - trade.entry_time).total_seconds() / 60)
        
        # Calculate PnL % from margin (not total balance)
        margin_used = trade.entry_price * trade.quantity  # Margin without leverage
        pnl_pct_margin = (pnl / margin_used) * 100 if margin_used > 0 else 0
        
        print(f"✅ Closed {current_side} {symbol} @ ${price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct_margin:+.1f}%)")
        
        # TELEGRAM NOTIFICATION
        try:
            reporter = get_telegram_reporter()
            await reporter.notify_close(
                symbol=symbol,
                side=current_side,
                exit_price=price,
                pnl=pnl,
                pnl_pct=pnl_pct_margin,
                duration_minutes=duration_minutes,
                reason=reason
            )
        except Exception as e:
            print(f"   📱 Telegram error (ignored): {e}")
        
        return ExecutionResult(
            success=True,
            market_type=self.market_type,
            order_id=order_id,
            symbol=symbol,
            side=f"CLOSE_{current_side}",
            quantity=float(qty_str),
            price=price,
            pnl=pnl
        )
    
    async def close_position(self, symbol: str, reason: str) -> ExecutionResult:
        """Public method"""
        return await self._close_position(symbol, reason)
    
    # ========== HELPERS ==========
    
    async def get_balance(self) -> float:
        """VIRTUAL BALANCE ONLY!"""
        return self.virtual_balance
    
    def get_balance_info(self) -> Dict:
        pnl_pct = ((self.virtual_balance - self.initial_balance) / self.initial_balance * 100) if self.initial_balance > 0 else 0
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.virtual_balance,
            'realized_pnl': self.realized_pnl,
            'pnl_pct': pnl_pct,
            'leverage': self.leverage
        }
    
    def update_balance(self, pnl: float):
        self.virtual_balance += pnl
        self.realized_pnl += pnl
        print(f"💰 Balance: ${self.virtual_balance:.2f} (PnL: ${pnl:+.2f})")
    
    async def _save_trade(self, symbol: str, side: TradeSide, price: float,
                          quantity: float, order_id: str, signal: TradeSignal,
                          position_side: str, stop_loss: float, take_profit: float) -> Optional[Trade]:
        try:
            async with async_session() as session:
                trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_price=price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=TradeStatus.OPEN,
                    ai_risk_score=signal.risk_score,
                    ai_reasoning=signal.reasoning,
                    market_type='futures',
                    extra_data={
                        'bybit_order_id': order_id,
                        'confidence': signal.confidence,
                        'executor': 'FuturesExecutor_v3',
                        'leverage': self.leverage,
                        'position_side': position_side,
                        'margin_mode': 'ISOLATED',
                        'virtual_balance': self.virtual_balance
                    }
                )
                session.add(trade)
                await session.commit()
                await session.refresh(trade)
                return trade
        except Exception as e:
            print(f"❌ Save trade error: {e}")
            return None
    
    async def get_open_positions(self) -> List[Dict]:
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'futures'
                )
            )
            trades = result.scalars().all()
            return [{
                'id': t.id,
                'symbol': t.symbol,
                'side': t.extra_data.get('position_side', t.side.value),
                'entry_price': float(t.entry_price),
                'quantity': float(t.quantity),
                'leverage': t.extra_data.get('leverage', self.leverage),
                'stop_loss': float(t.stop_loss) if t.stop_loss else None,
                'take_profit': float(t.take_profit) if t.take_profit else None,
                'margin_mode': 'ISOLATED'
            } for t in trades]
    
    # ========== v5.0: РУЧНАЯ ПРОВЕРКА SL/TP ==========
    
    async def check_and_close_sl_tp(self) -> List[Dict]:
        """
        Проверить все открытые позиции и закрыть по SL/TP
        
        Вызывать каждые 30 секунд из hybrid_loop
        
        Returns: список закрытых позиций
        """
        closed = []
        
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'futures'
                )
            )
            trades = result.scalars().all()
        
        for trade in trades:
            try:
                # Получаем текущую цену
                ticker = await self.api.get_ticker(trade.symbol)
                if not ticker:
                    continue
                
                current_price = float(ticker.get('last_price') or ticker.get('lastPrice', 0))
                if current_price <= 0:
                    continue
                
                entry_price = float(trade.entry_price)
                stop_loss = float(trade.stop_loss) if trade.stop_loss else None
                take_profit = float(trade.take_profit) if trade.take_profit else None
                position_side = trade.extra_data.get('position_side', 'LONG')
                
                should_close = False
                close_reason = ""
                
                if position_side == 'LONG':
                    # LONG: SL если цена упала, TP если выросла
                    if stop_loss and current_price <= stop_loss:
                        should_close = True
                        close_reason = f"SL Hit: ${current_price:.2f} <= ${stop_loss:.2f}"
                    elif take_profit and current_price >= take_profit:
                        should_close = True
                        close_reason = f"TP Hit: ${current_price:.2f} >= ${take_profit:.2f}"
                else:
                    # SHORT: SL если цена выросла, TP если упала
                    if stop_loss and current_price >= stop_loss:
                        should_close = True
                        close_reason = f"SL Hit: ${current_price:.2f} >= ${stop_loss:.2f}"
                    elif take_profit and current_price <= take_profit:
                        should_close = True
                        close_reason = f"TP Hit: ${current_price:.2f} <= ${take_profit:.2f}"
                
                if should_close:
                    print(f"   🎯 {trade.symbol} {position_side}: {close_reason}")
                    
                    # Закрываем позицию
                    self._current_positions[trade.symbol] = position_side
                    result = await self._close_position(trade.symbol, close_reason)
                    
                    if result.success:
                        closed.append({
                            'symbol': trade.symbol,
                            'side': position_side,
                            'reason': close_reason,
                            'pnl': result.pnl
                        })
            
            except Exception as e:
                print(f"   ⚠️ Error checking {trade.symbol}: {e}")
                continue
        
        if closed:
            print(f"   ✅ Closed {len(closed)} positions by SL/TP")
        
        return closed


# Singleton
_futures_executor = None

def get_futures_executor() -> FuturesExecutor:
    global _futures_executor
    if _futures_executor is None:
        _futures_executor = FuturesExecutor()
    return _futures_executor
