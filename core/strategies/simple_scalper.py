"""
Simple RSI Grid Strategy - Mean Reversion Scalper

Философия: Простота = Прибыль
Без ML, без агентов, без сложности. Чистая математика.

Стратегия:
- Покупаем на перепроданности (RSI < 30 + касание нижней BB)
- Продаём на перекупленности (RSI > 70 + касание верхней BB)
- Фиксированные TP/SL без трейлинга
- Таймфрейм: 15m
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
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
        self.bb_period = 20
        self.bb_std = 2.0
        
        self.take_profit_pct = 1.5  # +1.5%
        self.stop_loss_pct = 2.0    # -2.0%
        
        # Торговые пары
        self.symbols = settings.futures_pairs
        
        # Кэш свечей
        self.candles_cache: Dict[str, pd.DataFrame] = {}
        
        print("✅ SimpleScalper initialized")
        print(f"   Timeframe: {self.timeframe}m")
        print(f"   RSI: {self.rsi_period} (OS: {self.rsi_oversold}, OB: {self.rsi_overbought})")
        print(f"   BB: {self.bb_period} periods, {self.bb_std} std")
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
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Анализ символа и генерация сигнала
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Dict с сигналом или None
        """
        # Получаем свечи
        df = await self.fetch_candles(symbol, limit=100)
        
        if df.empty or len(df) < self.bb_period:
            return None
        
        # Рассчитываем индикаторы
        df["rsi"] = self.calculate_rsi(df["close"], self.rsi_period)
        bb = self.calculate_bollinger_bands(df["close"], self.bb_period, self.bb_std)
        df["bb_middle"] = bb["middle"]
        df["bb_upper"] = bb["upper"]
        df["bb_lower"] = bb["lower"]
        
        # Последние значения
        last = df.iloc[-1]
        current_price = last["close"]
        current_rsi = last["rsi"]
        bb_upper = last["bb_upper"]
        bb_lower = last["bb_lower"]
        bb_middle = last["bb_middle"]
        
        # Проверяем на NaN
        if pd.isna(current_rsi) or pd.isna(bb_upper) or pd.isna(bb_lower):
            return None
        
        # Генерируем сигнал
        signal = None
        reason = ""
        
        # LONG сигнал: RSI < 30 AND price <= Lower BB
        if current_rsi < self.rsi_oversold and current_price <= bb_lower:
            signal = "LONG"
            reason = f"RSI {current_rsi:.1f} < {self.rsi_oversold} AND price {current_price:.2f} <= BB Lower {bb_lower:.2f}"
        
        # SHORT сигнал: RSI > 70 AND price >= Upper BB
        elif current_rsi > self.rsi_overbought and current_price >= bb_upper:
            signal = "SHORT"
            reason = f"RSI {current_rsi:.1f} > {self.rsi_overbought} AND price {current_price:.2f} >= BB Upper {bb_upper:.2f}"
        
        if signal:
            return {
                "symbol": symbol,
                "signal": signal,
                "price": current_price,
                "rsi": current_rsi,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
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
