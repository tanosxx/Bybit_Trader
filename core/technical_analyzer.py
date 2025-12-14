"""
Технический анализ для крипто рынков
Индикаторы: RSI, MACD, Bollinger Bands, EMA
"""
import numpy as np
from typing import List, Dict, Optional


class TechnicalAnalyzer:
    """Технический анализ свечей"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Relative Strength Index (RSI)
        
        RSI < 30 = Oversold (перепроданность) → BUY signal
        RSI > 70 = Overbought (перекупленность) → SELL signal
        """
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[Dict]:
        """
        Moving Average Convergence Divergence (MACD)
        
        Returns:
            {
                "macd": value,
                "signal": value,
                "histogram": value,
                "trend": "bullish" or "bearish"
            }
        """
        if len(prices) < slow_period + signal_period:
            return None
        
        prices_array = np.array(prices)
        
        # EMA calculation
        def ema(data, period):
            return data.ewm(span=period, adjust=False).mean()
        
        import pandas as pd
        prices_series = pd.Series(prices_array)
        
        ema_fast = ema(prices_series, fast_period)
        ema_slow = ema(prices_series, slow_period)
        
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        
        macd_value = macd_line.iloc[-1]
        signal_value = signal_line.iloc[-1]
        histogram_value = histogram.iloc[-1]
        
        # Определяем тренд
        if histogram_value > 0 and histogram.iloc[-2] <= 0:
            trend = "bullish_crossover"  # Сильный BUY сигнал
        elif histogram_value < 0 and histogram.iloc[-2] >= 0:
            trend = "bearish_crossover"  # Сильный SELL сигнал
        elif histogram_value > 0:
            trend = "bullish"
        else:
            trend = "bearish"
        
        return {
            "macd": round(macd_value, 2),
            "signal": round(signal_value, 2),
            "histogram": round(histogram_value, 2),
            "trend": trend
        }
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[Dict]:
        """
        Bollinger Bands
        
        Price < Lower Band = Oversold → BUY signal
        Price > Upper Band = Overbought → SELL signal
        """
        if len(prices) < period:
            return None
        
        prices_array = np.array(prices[-period:])
        
        sma = np.mean(prices_array)
        std = np.std(prices_array)
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        current_price = prices[-1]
        
        # Определяем позицию цены
        if current_price < lower_band:
            position = "below_lower"  # BUY signal
        elif current_price > upper_band:
            position = "above_upper"  # SELL signal
        else:
            position = "within_bands"
        
        # Bandwidth (волатильность)
        bandwidth = ((upper_band - lower_band) / sma) * 100
        
        return {
            "upper": round(upper_band, 2),
            "middle": round(sma, 2),
            "lower": round(lower_band, 2),
            "current": round(current_price, 2),
            "position": position,
            "bandwidth": round(bandwidth, 2)
        }
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        import pandas as pd
        prices_series = pd.Series(prices)
        ema_value = prices_series.ewm(span=period, adjust=False).mean().iloc[-1]
        
        return round(ema_value, 2)
    
    @staticmethod
    def analyze_trend(prices: List[float]) -> str:
        """
        Определить тренд
        
        Returns: "uptrend", "downtrend", "sideways"
        """
        if len(prices) < 20:
            return "unknown"
        
        ema_20 = TechnicalAnalyzer.calculate_ema(prices, 20)
        ema_50 = TechnicalAnalyzer.calculate_ema(prices, 50) if len(prices) >= 50 else None
        
        current_price = prices[-1]
        
        if ema_50:
            if current_price > ema_20 > ema_50:
                return "strong_uptrend"
            elif current_price < ema_20 < ema_50:
                return "strong_downtrend"
            elif current_price > ema_20:
                return "uptrend"
            elif current_price < ema_20:
                return "downtrend"
        else:
            if current_price > ema_20:
                return "uptrend"
            elif current_price < ema_20:
                return "downtrend"
        
        return "sideways"
    
    @staticmethod
    def analyze_volume(volumes: List[float]) -> str:
        """
        Анализ объема
        
        Returns: "increasing", "decreasing", "stable"
        """
        if len(volumes) < 10:
            return "unknown"
        
        recent_avg = np.mean(volumes[-5:])
        previous_avg = np.mean(volumes[-10:-5])
        
        change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
        
        if change_pct > 20:
            return "increasing"
        elif change_pct < -20:
            return "decreasing"
        else:
            return "stable"
    
    def analyze_market(self, candles: List[Dict]) -> Dict:
        """
        Полный анализ рынка
        
        Args:
            candles: List of {timestamp, open, high, low, close, volume}
        
        Returns:
            {
                "price": current_price,
                "rsi": rsi_value,
                "macd": {...},
                "bollinger_bands": {...},
                "trend": "uptrend/downtrend",
                "volume_trend": "increasing/decreasing",
                "signal": "BUY/SELL/NEUTRAL"
            }
        """
        if not candles or len(candles) < 50:
            return {"error": "Not enough data"}
        
        prices = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        
        current_price = prices[-1]
        rsi = self.calculate_rsi(prices)
        macd = self.calculate_macd(prices)
        bb = self.calculate_bollinger_bands(prices)
        trend = self.analyze_trend(prices)
        volume_trend = self.analyze_volume(volumes)
        
        # Определяем сигнал
        signal = "NEUTRAL"
        signal_strength = 0
        
        # RSI сигналы
        if rsi and rsi < 30:
            signal_strength += 1  # BUY
        elif rsi and rsi > 70:
            signal_strength -= 1  # SELL
        
        # MACD сигналы
        if macd:
            if macd["trend"] == "bullish_crossover":
                signal_strength += 2  # Сильный BUY
            elif macd["trend"] == "bearish_crossover":
                signal_strength -= 2  # Сильный SELL
            elif macd["trend"] == "bullish":
                signal_strength += 1
            elif macd["trend"] == "bearish":
                signal_strength -= 1
        
        # Bollinger Bands сигналы
        if bb:
            if bb["position"] == "below_lower":
                signal_strength += 1  # BUY
            elif bb["position"] == "above_upper":
                signal_strength -= 1  # SELL
        
        # Итоговый сигнал
        if signal_strength >= 2:
            signal = "BUY"
        elif signal_strength <= -2:
            signal = "SELL"
        
        return {
            "price": current_price,
            "rsi": rsi,
            "macd": macd,
            "bollinger_bands": bb,
            "trend": trend,
            "volume_trend": volume_trend,
            "signal": signal,
            "signal_strength": signal_strength
        }


# Singleton
_technical_analyzer = None

def get_technical_analyzer() -> TechnicalAnalyzer:
    """Получить singleton instance"""
    global _technical_analyzer
    if _technical_analyzer is None:
        _technical_analyzer = TechnicalAnalyzer()
    return _technical_analyzer
