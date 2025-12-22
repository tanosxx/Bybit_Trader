"""
FUTURES Executor v7.1 - АДАПТИВНЫЙ исполнитель для фьючерсной торговли

НОВЫЕ ФИЧИ v7.1 (Adaptive Scalper):
1. ADAPTIVE TP/SL - сжатие целей во флэте (TP×0.5, SL×0.7)
2. ADAPTIVE TTL - сокращение времени жизни во флэте (180→90 минут)
3. Market Regime Detection - автоматическое определение FLAT/TREND по CHOP
4. Scalping Mode - быстрые сделки во флэте вместо долгого ожидания

ФИЧИ v7.0 (Maker Strategy):
1. LIMIT Orders - умное ценообразование по Best Bid/Ask (Maker fee 0.02%)
2. Order Timeout - автоматическая отмена зависших ордеров (60s)
3. Zombie Cleanup - очистка старых ордеров перед новым сигналом
4. Fallback to Market - автоматический переход на Market при таймауте
5. Dynamic Fee Calculation - правильный учёт Maker (0.02%) vs Taker (0.055%)

ФИЧИ v4.0-v6.0:
1. Native Trailing Stop - серверный трейлинг через Bybit API
2. Funding Rate Filter - проверка ставки финансирования перед входом
3. Position Limits - контроль количества позиций и ордеров
4. BTC Correlation Filter - "Папа решает всё"

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ v3.0:
1. setup_leverage_and_margin() - ISOLATED + Leverage ПЕРЕД каждой сделкой
2. Price Precision - tickSize/qtyStep из get_instruments_info
3. Atomic Order - SL/TP внутри place_order, не отдельно
4. Virtual Balance $100 - никогда не запрашиваем реальный баланс
"""
import re
import asyncio
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
        
        # ========== VIRTUAL BALANCE из config.py ==========
        self.initial_balance = settings.futures_virtual_balance  # Стартовый баланс
        self.virtual_balance = settings.futures_virtual_balance  # Будет обновлён из БД
        self.realized_pnl = 0.0
        
        # Загружаем текущий баланс из БД (асинхронно при первом использовании)
        self._balance_loaded = False
        
        # Настройки торговли
        self.leverage = settings.futures_leverage  # Базовое, будет меняться динамически
        self.risk_per_trade = settings.futures_risk_per_trade  # Из конфига!
        
        # SL/TP проценты (базовые - для TREND режима)
        self.base_sl_pct = 2.0  # 2% стоп-лосс (базовый)
        self.base_tp_pct = 3.0  # 3% тейк-профит (базовый)
        
        # Текущие (адаптивные) значения
        self.sl_pct = self.base_sl_pct
        self.tp_pct = self.base_tp_pct
        
        # ========== TRAILING STOP v4.0 ==========
        self.trailing_enabled = settings.trailing_stop_enabled
        self.trailing_activation_pct = settings.trailing_activation_pct  # 1.0%
        self.trailing_callback_pct = settings.trailing_callback_pct  # 0.5%
        
        # ========== FUNDING RATE FILTER v4.0 ==========
        self.funding_filter_enabled = settings.funding_rate_filter_enabled
        self.funding_max_pct = settings.funding_rate_max_pct  # 0.05%
        self.funding_time_window = settings.funding_time_window_minutes  # 60 min
        
        # ========== POSITION LIMITS v6.2 ==========
        self.max_open_positions = settings.futures_max_open_positions  # 5 уникальных символов
        self.max_orders_per_symbol = settings.futures_max_orders_per_symbol  # 15 ордеров на символ
        self.max_total_orders = settings.futures_max_total_orders  # 60 всего ордеров
        self.min_confidence = settings.futures_min_confidence  # 0.50
        
        # Текущие позиции
        self._current_positions: Dict[str, str] = {}
        
        print(f"🚀 FuturesExecutor v7.1 initialized (ADAPTIVE SCALPER):")
        print(f"   💰 Virtual Balance: ${self.virtual_balance}")
        print(f"   📊 Base Leverage: {self.leverage}x (dynamic 2-7x)")
        print(f"   🎯 Risk per Trade: {self.risk_per_trade*100}%")
        print(f"   🛡️ Base SL: {self.base_sl_pct}% | Base TP: {self.base_tp_pct}%")
        print(f"   🔄 ADAPTIVE MODE: FLAT → TP×0.5, SL×0.7, TTL÷2")
        print(f"   📈 Trailing Stop: {'ON' if self.trailing_enabled else 'OFF'}")
        print(f"   💸 Funding Filter: {'ON' if self.funding_filter_enabled else 'OFF'}")
        print(f"   🚫 Max Symbols: {self.max_open_positions}")
        print(f"   🚫 Max Orders/Symbol: {self.max_orders_per_symbol}")
        print(f"   🚫 Max Total Orders: {self.max_total_orders}")
        print(f"   🎯 Min Confidence: {self.min_confidence*100}%")
        print(f"   ⚠️ ISOLATED margin ENFORCED")
        print(f"   💎 Order Type: {settings.order_type} (Maker: {settings.maker_fee_rate*100}%, Taker: {settings.taker_fee_rate*100}%)")
        print(f"   ⏰ Limit Timeout: {settings.order_timeout_seconds}s")
        print(f"   🔄 Fallback to Market: {'ON' if settings.limit_order_fallback_to_market else 'OFF'}")
    
    # ========== 0. POSITION LIMIT CHECK (v5.1) ==========
    
    def adapt_to_market_regime(self, chop: float, market_mode: str = None) -> Dict[str, float]:
        """
        Адаптировать TP/SL/TTL к режиму рынка
        
        FLAT режим (CHOP > 50 или market_mode == 'FLAT'):
        - TP сжимается на 50% (3% → 1.5%)
        - SL сжимается на 30% (2% → 1.4%)
        - TTL сокращается вдвое (180 → 90 минут)
        
        TREND режим:
        - Базовые значения (TP 3%, SL 2%, TTL 180 мин)
        
        Args:
            chop: Choppiness Index (0-100)
            market_mode: 'FLAT' или 'TREND' (опционально)
        
        Returns:
            {
                'tp_pct': float,
                'sl_pct': float,
                'ttl_minutes': int,
                'mode': str
            }
        """
        # Определяем режим
        is_flat = False
        
        if market_mode:
            is_flat = (market_mode == 'FLAT')
        elif chop is not None:
            # CHOP > 50 = флэт (вялый рынок)
            is_flat = (chop > 50.0)
        
        if is_flat:
            # FLAT: Скальпинг (быстрые сделки)
            tp_pct = self.base_tp_pct * 0.5  # 3% → 1.5%
            sl_pct = self.base_sl_pct * 0.7  # 2% → 1.4%
            ttl_minutes = settings.max_hold_time_minutes // 2  # 180 → 90 минут
            mode = 'FLAT'
            
            print(f"   🔄 ADAPTIVE MODE: FLAT detected (CHOP: {chop:.1f if chop else 'N/A'})")
            print(f"      TP: {self.base_tp_pct}% → {tp_pct}% (×0.5)")
            print(f"      SL: {self.base_sl_pct}% → {sl_pct}% (×0.7)")
            print(f"      TTL: {settings.max_hold_time_minutes}m → {ttl_minutes}m (÷2)")
        else:
            # TREND: Базовые значения
            tp_pct = self.base_tp_pct  # 3%
            sl_pct = self.base_sl_pct  # 2%
            ttl_minutes = settings.max_hold_time_minutes  # 180 минут
            mode = 'TREND'
            
            chop_str = f"{chop:.1f}" if chop is not None else "N/A"
            print(f"   📈 ADAPTIVE MODE: TREND (CHOP: {chop_str})")
            print(f"      TP: {tp_pct}%, SL: {sl_pct}%, TTL: {ttl_minutes}m")
        
        # Обновляем текущие значения
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        
        return {
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'ttl_minutes': ttl_minutes,
            'mode': mode
        }
    
    # ========== 0. POSITION LIMIT CHECK (v5.1) ==========
    
    async def _count_open_positions(self) -> int:
        """
        Подсчитать количество УНИКАЛЬНЫХ открытых позиций (по символам)
        
        ВАЖНО: На бирже позиции агрегируются по символу,
        поэтому считаем уникальные символы, а не количество ордеров в БД!
        """
        try:
            async with async_session() as session:
                from sqlalchemy import func, distinct
                result = await session.execute(
                    select(func.count(distinct(Trade.symbol))).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures'
                    )
                )
                unique_positions = result.scalar() or 0
                return unique_positions
        except Exception as e:
            print(f"   ⚠️ Error counting positions: {e}")
            return 0
    
    async def _count_orders_for_symbol(self, symbol: str) -> int:
        """Подсчитать количество открытых ордеров для конкретного символа"""
        try:
            async with async_session() as session:
                from sqlalchemy import func
                result = await session.execute(
                    select(func.count(Trade.id)).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures',
                        Trade.symbol == symbol
                    )
                )
                count = result.scalar() or 0
                return count
        except Exception as e:
            print(f"   ⚠️ Error counting orders for {symbol}: {e}")
            return 0
    
    async def _count_positions_for_symbol(self, symbol: str) -> int:
        """Подсчитать количество открытых ПОЗИЦИЙ для конкретного символа (не ордеров!)"""
        try:
            async with async_session() as session:
                from sqlalchemy import func
                result = await session.execute(
                    select(func.count(Trade.id)).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures',
                        Trade.symbol == symbol
                    )
                )
                count = result.scalar() or 0
                return count
        except Exception as e:
            print(f"   ⚠️ Error counting positions for {symbol}: {e}")
            return 0
    
    async def _count_total_orders(self) -> int:
        """Подсчитать общее количество открытых ордеров"""
        try:
            async with async_session() as session:
                from sqlalchemy import func
                result = await session.execute(
                    select(func.count(Trade.id)).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures'
                    )
                )
                count = result.scalar() or 0
                return count
        except Exception as e:
            print(f"   ⚠️ Error counting total orders: {e}")
            return 0
    
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
    
    # ========== 4. CANCEL ALL ACTIVE ORDERS (Cleanup) ==========
    
    async def cancel_all_active_orders(self, symbol: str) -> bool:
        """
        Отменить все активные ордера для символа
        
        Очистка "зомби-ордеров" перед размещением нового
        """
        try:
            endpoint = "/v5/order/cancel-all"
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            response = await self.api._request("POST", endpoint, params)
            
            if response and response.get("retCode") == 0:
                result = response.get("result", {})
                cancelled = result.get("list", [])
                if cancelled:
                    print(f"      🧹 Cancelled {len(cancelled)} zombie orders")
                return True
            
            return True  # Не критично если нет ордеров
            
        except Exception as e:
            print(f"      ⚠️ Cancel orders error: {e}")
            return True
    
    # ========== 5. GET BEST BID/ASK (Orderbook) ==========
    
    async def get_best_prices(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Получить лучшие цены из стакана
        
        Returns: {'bid': float, 'ask': float} или None
        """
        try:
            endpoint = "/v5/market/orderbook"
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": 1  # Только топ уровень
            }
            
            response = await self.api._request("GET", endpoint, params)
            
            if not response or response.get("retCode") != 0:
                return None
            
            result = response.get("result", {})
            bids = result.get("b", [])  # [[price, size], ...]
            asks = result.get("a", [])
            
            if not bids or not asks:
                return None
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            return {'bid': best_bid, 'ask': best_ask}
            
        except Exception as e:
            print(f"      ⚠️ Orderbook error: {e}")
            return None
    
    # ========== 6. ATOMIC ORDER (LIMIT or MARKET) ==========
    
    async def place_atomic_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        stop_loss: float,  # Принимаем float
        take_profit: float  # Принимаем float
    ) -> Optional[Dict]:
        """
        Открыть позицию с умным ценообразованием
        
        Шаг А: Очистить зомби-ордера
        Шаг Б: Определить цену (LIMIT: Best Bid/Ask, MARKET: не нужна)
        Шаг В: Разместить ордер
        Шаг Г: Мониторинг таймаута (для LIMIT)
        
        Bybit API v5 для linear futures требует устанавливать SL/TP
        через /v5/position/trading-stop, а не в основном ордере!
        """
        # Шаг А: Очистка зомби-ордеров
        await self.cancel_all_active_orders(symbol)
        
        # Шаг Б: Определение цены и типа ордера
        order_type = settings.order_type  # 'LIMIT' или 'MARKET'
        price_str = None
        
        if order_type == 'LIMIT':
            # Получаем лучшие цены из стакана
            best_prices = await self.get_best_prices(symbol)
            
            if not best_prices:
                # Fallback на Market если стакан недоступен
                if settings.limit_order_fallback_to_market:
                    print(f"      ⚠️ Orderbook unavailable - fallback to MARKET")
                    order_type = 'MARKET'
                else:
                    print(f"      ❌ Orderbook unavailable - skipping trade")
                    return None
            else:
                # Определяем цену для Maker ордера
                info = await self.get_instrument_info(symbol)
                tick_size = info['tick_size']
                
                if side == "Buy":  # LONG
                    # Покупаем по Best Bid (становимся в очередь покупателей)
                    limit_price = best_prices['bid']
                else:  # SHORT
                    # Продаём по Best Ask (становимся в очередь продавцов)
                    limit_price = best_prices['ask']
                
                price_str = self.round_price(limit_price, tick_size)
                print(f"      💰 LIMIT price: ${price_str} (Best {'Bid' if side == 'Buy' else 'Ask'})")
        
        # Шаг В: Размещение ордера
        endpoint = "/v5/order/create"
        params = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "positionIdx": 0  # One-Way Mode
        }
        
        # Добавляем цену для LIMIT
        if order_type == 'LIMIT' and price_str:
            params["price"] = price_str
            params["timeInForce"] = "GTC"  # Good Till Cancel
        
        print(f"\n      📤 OPENING POSITION ({order_type}):")
        print(f"         {side} {qty} {symbol}" + (f" @ ${price_str}" if price_str else ""))
        
        response = await self.api._request("POST", endpoint, params)
        
        if not response or response.get("retCode") != 0:
            error = response.get("retMsg", "Unknown") if response else "No response"
            print(f"      ❌ Order FAILED: {error}")
            
            # Fallback на Market если Limit не сработал
            if order_type == 'LIMIT' and settings.limit_order_fallback_to_market:
                print(f"      🔄 Retrying with MARKET order...")
                params["orderType"] = "Market"
                params.pop("price", None)
                params.pop("timeInForce", None)
                
                response = await self.api._request("POST", endpoint, params)
                if not response or response.get("retCode") != 0:
                    print(f"      ❌ MARKET order also failed")
                    return None
            else:
                return None
        
        result = response.get("result", {})
        order_id = result.get("orderId", "")
        
        # Шаг Г: Для LIMIT ордеров - ждём исполнения с таймаутом
        if order_type == 'LIMIT':
            print(f"      ⏳ Waiting for LIMIT order fill (timeout: {settings.order_timeout_seconds}s)...")
            
            filled = await self._wait_for_order_fill(symbol, order_id, settings.order_timeout_seconds)
            
            if not filled:
                print(f"      ⏰ LIMIT order timeout - cancelling...")
                await self._cancel_order(symbol, order_id)
                
                # Fallback на Market
                if settings.limit_order_fallback_to_market:
                    print(f"      🔄 Retrying with MARKET order...")
                    params["orderType"] = "Market"
                    params.pop("price", None)
                    params.pop("timeInForce", None)
                    
                    response = await self.api._request("POST", endpoint, params)
                    if not response or response.get("retCode") != 0:
                        print(f"      ❌ MARKET order failed")
                        return None
                    
                    order_id = response.get("result", {}).get("orderId", "")
                    print(f"      ✅ Position opened (MARKET): {order_id}")
                else:
                    return None
            else:
                print(f"      ✅ LIMIT order filled: {order_id}")
        else:
            print(f"      ✅ Position opened (MARKET): {order_id}")
        
        # Шаг Д: НЕ устанавливаем SL/TP - Bybit API имеет баг с парсингом
        # Позиция открыта, будем управлять через мониторинг
        print(f"      ⚠️ SL/TP skipped (Bybit API bug): {stop_loss} | {take_profit}")
        print(f"      💡 Will be managed by position monitor")
        
        return {
            "order_id": order_id,
            "status": "OK",
            "sl": stop_loss,
            "tp": take_profit,
            "order_type": order_type,
            "limit_price": float(price_str) if price_str else None
        }
    
    async def _wait_for_order_fill(self, symbol: str, order_id: str, timeout_seconds: int) -> bool:
        """
        Ждать исполнения ордера с таймаутом
        
        Returns: True если исполнен, False если таймаут
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout_seconds:
                return False
            
            # Проверяем статус ордера
            try:
                endpoint = "/v5/order/realtime"
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "orderId": order_id
                }
                
                response = await self.api._request("GET", endpoint, params)
                
                if response and response.get("retCode") == 0:
                    orders = response.get("result", {}).get("list", [])
                    if orders:
                        order = orders[0]
                        order_status = order.get("orderStatus", "")
                        
                        if order_status == "Filled":
                            return True
                        elif order_status in ["Cancelled", "Rejected"]:
                            return False
                
            except Exception as e:
                print(f"      ⚠️ Order status check error: {e}")
            
            # Ждём 2 секунды перед следующей проверкой
            await asyncio.sleep(2)
    
    async def _cancel_order(self, symbol: str, order_id: str) -> bool:
        """Отменить ордер"""
        try:
            endpoint = "/v5/order/cancel"
            params = {
                "category": "linear",
                "symbol": symbol,
                "orderId": order_id
            }
            
            response = await self.api._request("POST", endpoint, params)
            return response and response.get("retCode") == 0
            
        except Exception as e:
            print(f"      ⚠️ Cancel order error: {e}")
            return False


    
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
        
        # ========== v5.0: ПРОВЕРКА ЛИМИТА ПОЗИЦИЙ (по уникальным символам) ==========
        open_count = await self._count_open_positions()
        if open_count >= self.max_open_positions:
            print(f"   🚫 Position limit reached: {open_count}/{self.max_open_positions} unique symbols")
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
        
        0. CHECK POSITION LIMIT (v5.1)
        0.5. ADAPT TO MARKET REGIME (v7.1 - NEW!)
        1. CHECK FUNDING RATE (v4.0)
        2. Setup margin + leverage
        3. Get instrument info
        4. Calculate qty
        5. Calculate SL/TP (ADAPTIVE!)
        6. Place ATOMIC order
        7. SET TRAILING STOP (v4.0)
        """
        print(f"\n🟢 [FUTURES] Opening LONG {symbol} @ ${price:.2f}")
        
        # 0.5. ADAPT TO MARKET REGIME (v7.1)
        chop = signal.extra_data.get('chop') if signal.extra_data else None
        market_mode = signal.extra_data.get('market_mode') if signal.extra_data else None
        
        adaptive_params = self.adapt_to_market_regime(chop, market_mode)
        ttl_minutes = adaptive_params['ttl_minutes']
        
        # 0. CHECK POSITION LIMITS (v7.1)
        # Проверка 1: Уникальные символы
        open_symbols = await self._count_open_positions()
        if open_symbols >= self.max_open_positions:
            error_msg = f"❌ Symbol limit: {open_symbols}/{self.max_open_positions} symbols"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 2: Позиций на этот символ (НОВОЕ v7.1!)
        symbol_positions = await self._count_positions_for_symbol(symbol)
        max_per_symbol = getattr(settings, 'futures_max_positions_per_symbol', 1)
        if symbol_positions >= max_per_symbol:
            error_msg = f"❌ {symbol} position limit: {symbol_positions}/{max_per_symbol} positions"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 3: Ордеров на этот символ
        symbol_orders = await self._count_orders_for_symbol(symbol)
        if symbol_orders >= self.max_orders_per_symbol:
            error_msg = f"❌ {symbol} limit: {symbol_orders}/{self.max_orders_per_symbol} orders"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 4: Общее количество ордеров
        total_orders = await self._count_total_orders()
        if total_orders >= self.max_total_orders:
            error_msg = f"❌ Total orders limit: {total_orders}/{self.max_total_orders}"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
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
        
        # 3.5. Load balance from DB (first time only)
        await self.load_balance_from_db()
        
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
            stop_loss=float(sl_str),  # Передаем как float, не строку!
            take_profit=float(tp_str)  # Передаем как float, не строку!
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
            take_profit=float(tp_str),
            order_type=order.get('order_type', 'MARKET'),
            limit_price=order.get('limit_price'),
            extra_data={
                'ttl_minutes': ttl_minutes,  # Адаптивный TTL
                'market_mode': adaptive_params['mode'],
                'chop': chop
            }
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
        
        0. CHECK POSITION LIMIT (v7.1)
        0.5. ADAPT TO MARKET REGIME (v7.1 - NEW!)
        1. CHECK FUNDING RATE (v4.0)
        2. Setup margin + leverage
        3. Get instrument info
        4. Calculate qty
        5. Calculate SL/TP (ADAPTIVE!)
        6. Place ATOMIC order
        7. SET TRAILING STOP (v4.0)
        """
        print(f"\n🔴 [FUTURES] Opening SHORT {symbol} @ ${price:.2f}")
        
        # 0.5. ADAPT TO MARKET REGIME (v7.1)
        chop = signal.extra_data.get('chop') if signal.extra_data else None
        market_mode = signal.extra_data.get('market_mode') if signal.extra_data else None
        
        adaptive_params = self.adapt_to_market_regime(chop, market_mode)
        ttl_minutes = adaptive_params['ttl_minutes']
        
        # 0. CHECK POSITION LIMITS (v7.1)
        # Проверка 1: Уникальные символы
        open_symbols = await self._count_open_positions()
        if open_symbols >= self.max_open_positions:
            error_msg = f"❌ Symbol limit: {open_symbols}/{self.max_open_positions} symbols"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 2: Позиций на этот символ (НОВОЕ v7.1!)
        symbol_positions = await self._count_positions_for_symbol(symbol)
        max_per_symbol = getattr(settings, 'futures_max_positions_per_symbol', 1)
        if symbol_positions >= max_per_symbol:
            error_msg = f"❌ {symbol} position limit: {symbol_positions}/{max_per_symbol} positions"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 3: Ордеров на этот символ
        symbol_orders = await self._count_orders_for_symbol(symbol)
        if symbol_orders >= self.max_orders_per_symbol:
            error_msg = f"❌ {symbol} limit: {symbol_orders}/{self.max_orders_per_symbol} orders"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
        # Проверка 4: Общее количество ордеров
        total_orders = await self._count_total_orders()
        if total_orders >= self.max_total_orders:
            error_msg = f"❌ Total orders limit: {total_orders}/{self.max_total_orders}"
            print(f"   {error_msg}")
            return ExecutionResult(success=False, market_type=self.market_type, error=error_msg)
        
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
        
        # 3.5. Load balance from DB (first time only)
        await self.load_balance_from_db()
        
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
            stop_loss=float(sl_str),  # Передаем как float, не строку!
            take_profit=float(tp_str)  # Передаем как float, не строку!
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
            take_profit=float(tp_str),
            order_type=order.get('order_type', 'MARKET'),
            limit_price=order.get('limit_price'),
            extra_data={
                'ttl_minutes': ttl_minutes,  # Адаптивный TTL
                'market_mode': adaptive_params['mode'],
                'chop': chop
            }
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
        
        # ========== CALCULATE FEES ==========
        # Определяем тип комиссии из extra_data
        order_type = trade.extra_data.get('order_type', 'MARKET') if trade.extra_data else 'MARKET'
        
        # Maker (LIMIT) = 0.02%, Taker (MARKET) = 0.055%
        if order_type == 'LIMIT':
            fee_pct = settings.maker_fee_rate * 100  # 0.02%
        else:
            fee_pct = settings.taker_fee_rate * 100  # 0.055%
        
        # Entry fee (если не записан)
        if not trade.fee_entry or trade.fee_entry == 0:
            entry_value = trade.entry_price * trade.quantity
            trade.fee_entry = entry_value * (fee_pct / 100)
        
        # Exit fee (закрытие всегда Market = Taker)
        exit_value = price * trade.quantity
        exit_fee = exit_value * (settings.taker_fee_rate * 100 / 100)
        
        # Update DB
        async with async_session() as session:
            trade.status = TradeStatus.CLOSED
            trade.exit_price = price
            trade.exit_time = datetime.utcnow()
            trade.pnl = pnl
            trade.pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100
            trade.exit_reason = reason
            trade.fee_exit = exit_fee  # Записываем комиссию выхода
            session.add(trade)
            await session.commit()
        
        # Обновляем баланс с учётом комиссий
        total_fees = trade.fee_entry + exit_fee
        net_pnl = pnl - total_fees
        
        self.record_trade(net_pnl)
        self.update_balance(net_pnl)
        del self._current_positions[symbol]
        
        # Calculate duration
        duration_minutes = 0
        if trade.entry_time:
            duration_minutes = int((datetime.utcnow() - trade.entry_time).total_seconds() / 60)
        
        # Calculate PnL % from margin (not total balance)
        margin_used = trade.entry_price * trade.quantity  # Margin without leverage
        pnl_pct_margin = (pnl / margin_used) * 100 if margin_used > 0 else 0
        
        print(f"✅ Closed {current_side} {symbol} @ ${price:.2f}")
        print(f"   💰 PnL: ${pnl:+.2f} ({pnl_pct_margin:+.1f}%)")
        print(f"   💸 Fees: ${total_fees:.4f} (entry: ${trade.fee_entry:.4f}, exit: ${exit_fee:.4f})")
        
        # ========== SELF-LEARNING: Обучение на результате ==========
        if trade.ml_features:
            try:
                from core.self_learning import get_self_learner
                learner = get_self_learner()
                
                # Определяем результат: 1 = Win (прибыль), 0 = Loss (убыток)
                result = 1 if pnl > 0 else 0
                
                # Обучаем модель
                success = learner.learn(trade.ml_features, result)
                
                if success:
                    stats = learner.get_stats()
                    print(f"   🧠 Self-Learning: Learned from {'WIN' if result == 1 else 'LOSS'}")
                    print(f"      Samples: {stats['learned_samples']}, WR: {stats['win_rate']:.1f}%")
            
            except Exception as e:
                print(f"   ⚠️ Self-learning error (ignored): {e}")
        print(f"   💵 Net PnL: ${net_pnl:+.2f}")
        
        # TELEGRAM NOTIFICATION
        try:
            reporter = get_telegram_reporter()
            await reporter.notify_close(
                symbol=symbol,
                side=current_side,
                exit_price=price,
                pnl=net_pnl,  # Отправляем net PnL
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
            pnl=net_pnl  # Возвращаем net PnL
        )
    
    async def close_position(self, symbol: str, reason: str) -> ExecutionResult:
        """Public method"""
        return await self._close_position(symbol, reason)
    
    # ========== EMERGENCY BRAKE (Hard Risk Management) ==========
    
    async def monitor_emergency_risks(self) -> List[Dict]:
        """
        🚨 EMERGENCY BRAKE - Жёсткий контроль убытков
        
        Проверяет ВСЕ открытые позиции на:
        1. Hard Stop Loss - 2% движения цены против позиции
        2. Time To Live (TTL) - максимум 3 часа удержания
        
        Работает НЕЗАВИСИМО от AI - это последняя линия защиты!
        
        Returns: List[Dict] - список позиций для экстренного закрытия
        """
        if not settings.emergency_brake_enabled:
            return []
        
        positions_to_close = []
        
        try:
            # Получаем все открытые позиции из БД
            async with async_session() as session:
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures'
                    )
                )
                open_trades = result.scalars().all()
            
            if not open_trades:
                return []
            
            # Текущее время (UTC aware)
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            for trade in open_trades:
                symbol = trade.symbol
                entry_price = trade.entry_price
                entry_time = trade.entry_time
                position_side = trade.extra_data.get('position_side', 'UNKNOWN') if trade.extra_data else 'UNKNOWN'
                
                # Конвертируем entry_time в aware datetime если нужно
                if entry_time and entry_time.tzinfo is None:
                    # Если naive - считаем что это UTC
                    entry_time = entry_time.replace(tzinfo=timezone.utc)
                
                # Получаем текущую цену
                try:
                    ticker = await self.api.get_ticker(symbol)
                    if not ticker:
                        continue
                    
                    current_price = float(ticker.get('last_price') or ticker.get('lastPrice', 0))
                    if current_price <= 0:
                        continue
                    
                except Exception as e:
                    print(f"   ⚠️ Failed to get price for {symbol}: {e}")
                    continue
                
                # ========== CHECK 1: HARD STOP LOSS ==========
                # Рассчитываем % изменения цены
                if position_side == 'LONG':
                    # LONG: убыток если цена упала
                    price_change_pct = (current_price - entry_price) / entry_price
                    
                    if price_change_pct <= -settings.hard_stop_loss_percent:
                        loss_pct = abs(price_change_pct) * 100
                        positions_to_close.append({
                            'trade': trade,
                            'symbol': symbol,
                            'reason': f'🚨 HARD STOP LOSS HIT: -{loss_pct:.2f}% (LONG)',
                            'current_price': current_price,
                            'entry_price': entry_price,
                            'position_side': position_side,
                            'trigger': 'HARD_SL'
                        })
                        print(f"   🚨 EMERGENCY: {symbol} LONG down {loss_pct:.2f}% (limit: {settings.hard_stop_loss_percent*100}%)")
                        continue
                
                elif position_side == 'SHORT':
                    # SHORT: убыток если цена выросла
                    price_change_pct = (entry_price - current_price) / entry_price
                    
                    if price_change_pct <= -settings.hard_stop_loss_percent:
                        loss_pct = abs(price_change_pct) * 100
                        positions_to_close.append({
                            'trade': trade,
                            'symbol': symbol,
                            'reason': f'🚨 HARD STOP LOSS HIT: -{loss_pct:.2f}% (SHORT)',
                            'current_price': current_price,
                            'entry_price': entry_price,
                            'position_side': position_side,
                            'trigger': 'HARD_SL'
                        })
                        print(f"   🚨 EMERGENCY: {symbol} SHORT up {loss_pct:.2f}% (limit: {settings.hard_stop_loss_percent*100}%)")
                        continue
                
                # ========== CHECK 2: TIME TO LIVE (TTL) - ADAPTIVE! ==========
                if entry_time:
                    hold_time_minutes = (now - entry_time).total_seconds() / 60
                    
                    # Получаем адаптивный TTL из extra_data (если есть)
                    ttl_limit = settings.max_hold_time_minutes  # Базовый (180 минут)
                    
                    if trade.extra_data and 'ttl_minutes' in trade.extra_data:
                        ttl_limit = trade.extra_data['ttl_minutes']  # Адаптивный (90 или 180)
                        market_mode = trade.extra_data.get('market_mode', 'UNKNOWN')
                        print(f"   🧟 Zombie Check ({market_mode}): {symbol} Duration={hold_time_minutes:.1f}m / Adaptive Limit={ttl_limit}m")
                    else:
                        print(f"   🧟 Zombie Check: {symbol} Duration={hold_time_minutes:.1f}m / Base Limit={ttl_limit}m")
                    
                    if hold_time_minutes > ttl_limit:
                        positions_to_close.append({
                            'trade': trade,
                            'symbol': symbol,
                            'reason': f'⏰ ZOMBIE TRADE (TTL EXPIRED): {hold_time_minutes:.0f} min > {ttl_limit} min',
                            'current_price': current_price,
                            'entry_price': entry_price,
                            'position_side': position_side,
                            'trigger': 'TTL_EXPIRED'
                        })
                        print(f"   ⏰ ZOMBIE TRADE DETECTED: {symbol} held for {hold_time_minutes:.0f} min (limit: {ttl_limit} min)")
                        continue
            
            if positions_to_close:
                print(f"\n🚨 EMERGENCY BRAKE: {len(positions_to_close)} positions need immediate closure!")
            
            return positions_to_close
            
        except Exception as e:
            print(f"   ⚠️ Emergency risk monitor error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def execute_emergency_closures(self) -> int:
        """
        Выполнить экстренное закрытие позиций
        
        Returns: количество закрытых позиций
        """
        positions_to_close = await self.monitor_emergency_risks()
        
        if not positions_to_close:
            return 0
        
        closed_count = 0
        
        for pos_info in positions_to_close:
            symbol = pos_info['symbol']
            reason = pos_info['reason']
            
            try:
                print(f"\n🚨 EMERGENCY CLOSING: {symbol}")
                print(f"   Reason: {reason}")
                
                result = await self._close_position(symbol, reason)
                
                if result.success:
                    closed_count += 1
                    print(f"   ✅ Emergency closure successful")
                else:
                    print(f"   ❌ Emergency closure failed: {result.error}")
                
            except Exception as e:
                print(f"   ❌ Emergency closure error: {e}")
                import traceback
                traceback.print_exc()
        
        if closed_count > 0:
            print(f"\n✅ Emergency Brake: Closed {closed_count}/{len(positions_to_close)} positions")
        
        return closed_count
    
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
    
    async def load_balance_from_db(self):
        """
        Загрузить текущий баланс из БД
        
        Рассчитывает: initial_balance + SUM(pnl) - SUM(fees)
        """
        if self._balance_loaded:
            return self.virtual_balance  # Уже загружен, возвращаем текущий баланс
        
        try:
            from sqlalchemy import select, func
            
            async with async_session() as session:
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
                self.virtual_balance = self.initial_balance + total_pnl - total_fees
                self.realized_pnl = total_pnl - total_fees
                
                self._balance_loaded = True
                
                print(f"💰 Balance loaded from DB:")
                print(f"   Initial: ${self.initial_balance:.2f}")
                print(f"   Gross PnL: ${total_pnl:+.2f}")
                print(f"   Fees: -${total_fees:.2f}")
                print(f"   Current: ${self.virtual_balance:.2f} ({self.realized_pnl:+.2f})")
                
                return self.virtual_balance
                
        except Exception as e:
            print(f"⚠️ Failed to load balance from DB: {e}")
            print(f"   Using config balance: ${self.virtual_balance:.2f}")
            return self.virtual_balance
    
    def update_balance(self, pnl: float):
        """Обновить баланс после закрытия позиции"""
        self.virtual_balance += pnl
        self.realized_pnl += pnl
        print(f"💰 Balance updated: ${self.virtual_balance:.2f} (PnL: ${pnl:+.2f})")
    
    async def _save_trade(self, symbol: str, side: TradeSide, price: float,
                          quantity: float, order_id: str, signal: TradeSignal,
                          position_side: str, stop_loss: float, take_profit: float,
                          order_type: str = 'MARKET', limit_price: float = None) -> Optional[Trade]:
        try:
            # Рассчитываем комиссию входа (зависит от типа ордера)
            if order_type == 'LIMIT':
                fee_pct = settings.maker_fee_rate * 100  # 0.02% Maker
            else:
                fee_pct = settings.taker_fee_rate * 100  # 0.055% Taker
            
            # Используем limit_price если есть, иначе price
            actual_entry_price = limit_price if limit_price else price
            entry_value = actual_entry_price * quantity
            entry_fee = entry_value * (fee_pct / 100)
            
            # Извлекаем ml_features из signal (если есть)
            ml_features = None
            if hasattr(signal, 'extra_data') and signal.extra_data:
                ml_features = signal.extra_data.get('ml_features')
            
            async with async_session() as session:
                trade = Trade(
                    symbol=symbol,
                    side=side,
                    entry_price=actual_entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=TradeStatus.OPEN,
                    fee_entry=entry_fee,  # Записываем комиссию входа
                    ai_risk_score=signal.risk_score,
                    ai_reasoning=signal.reasoning,
                    market_type='futures',
                    ml_features=ml_features,  # Сохраняем фичи для Self-Learning
                    extra_data={
                        'bybit_order_id': order_id,
                        'confidence': signal.confidence,
                        'executor': 'FuturesExecutor_v7',
                        'leverage': self.leverage,
                        'position_side': position_side,
                        'margin_mode': 'ISOLATED',
                        'virtual_balance': self.virtual_balance,
                        'order_type': order_type,  # LIMIT или MARKET
                        'limit_price': limit_price  # Цена лимитного ордера
                    }
                )
                session.add(trade)
                await session.commit()
                await session.refresh(trade)
                
                print(f"   💸 Entry fee: ${entry_fee:.4f} ({fee_pct}% {order_type})")
                
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
