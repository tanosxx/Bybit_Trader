"""
Advanced RSI + EMA + ADX Strategy v3 - Trend Filter Edition

Философия: Торгуй ПО тренду, НЕ против него!
Добавлен EMA 200 фильтр для определения глобального тренда.

Стратегия (4 индикатора):
1. EMA 200 - ГЛАВНЫЙ фильтр глобального тренда
2. RSI - определяет перепроданность/перекупленность
3. EMA (9/21) - определяет локальный тренд и точки входа
4. ADX - фильтрует флэт (торгуем только при ADX > 25)

ТРЕНДОВЫЙ ФИЛЬТР (EMA 200):
- Цена > EMA 200 = UPTREND → Разрешены ТОЛЬКО LONG
- Цена < EMA 200 = DOWNTREND → Разрешены ТОЛЬКО SHORT

Сигналы:
- LONG (только в UPTREND): RSI < 40 + Цена < EMA(21) + ADX > 25 + EMA(9) разворачивается вверх
- SHORT (только в DOWNTREND): RSI > 55 + Цена > EMA(21) + ADX > 25 + EMA(9) разворачивается вниз
  (RSI 55 вместо 60 для downtrend - легче поймать отскоки)

Выход:
- TP: +1.5%
- SL: -2.0%

Таймфрейм: 15m
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import numpy as np
import pandas as pd
from pybit.unified_trading import HTTP

from config_v2 import settings


class SimpleScalper:
    """
    Простая скальперская стратегия на основе RSI и Bollinger Bands
    
    Сигналы:
    - LONG: RSI < 30 AND price <= Lower BB
    - SHORT: RSI > 70 AND price >= Upper BB
    
    Выход:
    - TP: +1.5% (или касание средней линии BB)
    - SL: -2.0%
    """
    
    def __init__(self):
        """Инициализация стратегии"""
        self.client = HTTP(
            testnet=settings.bybit_testnet,
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret
        )
        
        # Параметры стратегии
        self.timeframe = "15"  # 15 минут
        self.rsi_period = 14
        self.rsi_oversold = 40  # Для LONG в uptrend
        self.rsi_overbought_uptrend = 60  # Для SHORT в uptrend (не используется)
        self.rsi_overbought_downtrend = 55  # Для SHORT в downtrend (СМЯГЧЕНО!)
        
        self.ema_trend_period = 200  # EMA 200 - ГЛАВНЫЙ трендовый фильтр
        
        self.bb_period = 20
        self.bb_std = 2.0
        self.require_bb_touch = False  # ОТКЛЮЧЕНО для большей частоты сигналов!
        
        self.take_profit_pct = 1.5  # +1.5%
        self.stop_loss_pct = 2.0    # -2.0%
        
        # Торговые пары (13 пар - убрали MATICUSDT)
        self.symbols = settings.futures_pairs
        
        # Кэш свечей
        self.candles_cache: Dict[str, pd.DataFrame] = {}
        
        print("✅ SimpleScalper v3 initialized (EMA 200 Trend Filter)")
        print(f"   Timeframe: {self.timeframe}m")
        print(f"   EMA 200: TREND FILTER (Price > EMA200 = UPTREND, Price < EMA200 = DOWNTREND)")
        print(f"   RSI: {self.rsi_period} (LONG: <{self.rsi_oversold}, SHORT: >{self.rsi_overbought_downtrend} in downtrend)")
        print(f"   EMA: 9/21 (local trend detection)")
        print(f"   ADX: 14 (min 25 for trading)")
        print(f"   TP: +{self.take_profit_pct}%, SL: -{self.stop_loss_pct}%")
        print(f"   Symbols: {', '.join(self.symbols)}")
    
    async def fetch_candles(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Получить свечи с биржи
        
        Args:
            symbol: Торговая пара (BTCUSDT)
            limit: Количество свечей
            
        Returns:
            DataFrame с колонками: timestamp, open, high, low, close, volume
        """
        try:
            response = self.client.get_kline(
                category="linear",
                symbol=symbol,
                interval=self.timeframe,
                limit=limit
            )
            
            if response["retCode"] != 0:
                print(f"❌ Error fetching candles for {symbol}: {response['retMsg']}")
                return pd.DataFrame()
            
            # Преобразуем в DataFrame
            candles = []
            for item in response["result"]["list"]:
                candles.append({
                    "timestamp": int(item[0]),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5])
                })
            
            df = pd.DataFrame(candles)
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"❌ Exception fetching candles for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Рассчитать RSI (Relative Strength Index)
        
        Args:
            prices: Серия цен закрытия
            period: Период RSI
            
        Returns:
            Серия значений RSI
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: float = 2.0) -> Dict[str, pd.Series]:
        """
        Рассчитать Bollinger Bands
        
        Args:
            prices: Серия цен закрытия
            period: Период MA
            std: Количество стандартных отклонений
            
        Returns:
            Dict с ключами: middle, upper, lower
        """
        middle = prices.rolling(window=period).mean()
        std_dev = prices.rolling(window=period).std()
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return {
            "middle": middle,
            "upper": upper,
            "lower": lower
        }
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Рассчитать EMA (Exponential Moving Average)
        
        Args:
            prices: Серия цен закрытия
            period: Период EMA
            
        Returns:
            Серия EMA значений
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Рассчитать ADX (Average Directional Index)
        
        ADX показывает СИЛУ тренда (не направление):
        - ADX > 25 = сильный тренд
        - ADX < 20 = слабый тренд (флэт)
        
        Args:
            high: Серия максимумов
            low: Серия минимумов
            close: Серия закрытий
            period: Период ADX
            
        Returns:
            Серия ADX значений
        """
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Smoothed DM
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Анализ символа и генерация сигнала
        
        СТРАТЕГИЯ v3: EMA 200 Trend Filter + RSI + EMA + ADX
        
        ГЛАВНОЕ ПРАВИЛО (EMA 200 Trend Filter):
        - Цена > EMA 200 = UPTREND → Разрешены ТОЛЬКО LONG
        - Цена < EMA 200 = DOWNTREND → Разрешены ТОЛЬКО SHORT
        
        BUY сигнал (только в UPTREND):
        - Цена > EMA(200) (глобальный uptrend)
        - RSI < 40 (перепроданность)
        - Цена ниже EMA(21) (коррекция в тренде)
        - ADX > 25 (сильный тренд)
        - EMA(9) > EMA(21) ИЛИ EMA(9) начинает разворачиваться вверх
        
        SELL сигнал (только в DOWNTREND):
        - Цена < EMA(200) (глобальный downtrend)
        - RSI > 55 (перекупленность - СМЯГЧЕНО для downtrend!)
        - Цена выше EMA(21)
        - ADX > 25
        - EMA(9) < EMA(21) ИЛИ EMA(9) начинает разворачиваться вниз
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Dict с сигналом или None
        """
        # Получаем свечи (нужно больше для EMA 200)
        df = await self.fetch_candles(symbol, limit=250)
        
        if df.empty or len(df) < 210:  # Нужно минимум 210 свечей для EMA 200
            return None
        
        # Рассчитываем индикаторы
        df["rsi"] = self.calculate_rsi(df["close"], self.rsi_period)
        df["ema_fast"] = self.calculate_ema(df["close"], 9)
        df["ema_slow"] = self.calculate_ema(df["close"], 21)
        df["ema_trend"] = self.calculate_ema(df["close"], self.ema_trend_period)  # EMA 200
        df["adx"] = self.calculate_adx(df["high"], df["low"], df["close"], 14)
        
        # Bollinger Bands (оставляем для справки)
        bb = self.calculate_bollinger_bands(df["close"], self.bb_period, self.bb_std)
        df["bb_middle"] = bb["middle"]
        df["bb_upper"] = bb["upper"]
        df["bb_lower"] = bb["lower"]
        
        # Последние значения
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = last["close"]
        current_rsi = last["rsi"]
        ema_fast = last["ema_fast"]
        ema_slow = last["ema_slow"]
        ema_trend = last["ema_trend"]  # EMA 200
        adx = last["adx"]
        
        # Предыдущие значения для определения разворота
        prev_ema_fast = prev["ema_fast"]
        
        # Проверяем на NaN
        if pd.isna(current_rsi) or pd.isna(ema_fast) or pd.isna(ema_slow) or pd.isna(ema_trend) or pd.isna(adx):
            return None
        
        # Определяем глобальный тренд (EMA 200)
        global_trend = "UP" if current_price > ema_trend else "DOWN"
        
        # Генерируем сигнал
        signal = None
        reason = ""
        
        # ФИЛЬТР: ADX должен быть > 25 (сильный тренд)
        if adx < 25:
            # Слабый тренд - не торгуем
            return None
        
        # LONG сигнал (ТОЛЬКО в UPTREND)
        if global_trend == "UP":
            if current_rsi < self.rsi_oversold and current_price < ema_slow:
                # Проверяем разворот EMA(9) вверх
                ema_turning_up = ema_fast > prev_ema_fast
                
                if ema_turning_up or ema_fast > ema_slow:
                    signal = "LONG"
                    reason = f"UPTREND (Price {current_price:.2f} > EMA200 {ema_trend:.2f}), RSI {current_rsi:.1f} < {self.rsi_oversold}, Price < EMA21 {ema_slow:.2f}, ADX {adx:.1f} > 25"
                    if ema_turning_up:
                        reason += ", EMA9 turning up"
        
        # SHORT сигнал (ТОЛЬКО в DOWNTREND)
        elif global_trend == "DOWN":
            # В downtrend используем СМЯГЧЕННЫЙ порог RSI (55 вместо 60)
            rsi_threshold = self.rsi_overbought_downtrend
            
            if current_rsi > rsi_threshold and current_price > ema_slow:
                # Проверяем разворот EMA(9) вниз
                ema_turning_down = ema_fast < prev_ema_fast
                
                if ema_turning_down or ema_fast < ema_slow:
                    signal = "SHORT"
                    reason = f"DOWNTREND (Price {current_price:.2f} < EMA200 {ema_trend:.2f}), RSI {current_rsi:.1f} > {rsi_threshold}, Price > EMA21 {ema_slow:.2f}, ADX {adx:.1f} > 25"
                    if ema_turning_down:
                        reason += ", EMA9 turning down"
        
        if signal:
            return {
                "symbol": symbol,
                "signal": signal,
                "price": current_price,
                "rsi": current_rsi,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "ema_trend": ema_trend,  # EMA 200
                "global_trend": global_trend,  # UP/DOWN
                "adx": adx,
                "bb_upper": last["bb_upper"],
                "bb_middle": last["bb_middle"],
                "bb_lower": last["bb_lower"],
                "reason": reason,
                "timestamp": datetime.now()
            }
        
        return None
    
    async def scan_markets(self) -> List[Dict]:
        """
        Сканировать все рынки и найти сигналы
        
        Returns:
            Список сигналов
        """
        signals = []
        
        for symbol in self.symbols:
            signal = await self.analyze_symbol(symbol)
            if signal:
                signals.append(signal)
                print(f"🎯 SIGNAL: {signal['signal']} {symbol} @ {signal['price']:.2f}")
                print(f"   {signal['reason']}")
        
        return signals
    
    def calculate_position_size(self, balance: float, price: float, leverage: int = 3) -> float:
        """
        Рассчитать размер позиции
        
        Args:
            balance: Текущий баланс
            price: Цена входа
            leverage: Плечо
            
        Returns:
            Размер позиции в базовой валюте
        """
        # Рискуем 5% от баланса на сделку
        risk_amount = balance * 0.05
        
        # С учётом плеча
        position_value = risk_amount * leverage
        
        # Количество монет
        quantity = position_value / price
        
        return quantity


# ========== SINGLETON ==========

_simple_scalper: Optional[SimpleScalper] = None

def get_simple_scalper() -> SimpleScalper:
    """Получить singleton SimpleScalper"""
    global _simple_scalper
    if _simple_scalper is None:
        _simple_scalper = SimpleScalper()
    return _simple_scalper
