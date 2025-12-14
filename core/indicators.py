"""
Технические индикаторы для анализа криптовалют
Используется для расчета RSI, MACD, Bollinger Bands и других индикаторов
"""
import pandas as pd
import numpy as np
from typing import Tuple


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Рассчитать RSI (Relative Strength Index)
    
    Args:
        prices: Series цен закрытия
        period: период для расчета (default: 14)
    
    Returns:
        Series со значениями RSI (0-100)
    """
    # Рассчитываем изменения цен
    delta = prices.diff()
    
    # Разделяем на прибыль и убыток
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Рассчитываем RS и RSI
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Рассчитать EMA (Exponential Moving Average)
    
    Args:
        prices: Series цен
        period: период для расчета
    
    Returns:
        Series со значениями EMA
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    Рассчитать SMA (Simple Moving Average)
    
    Args:
        prices: Series цен
        period: период для расчета
    
    Returns:
        Series со значениями SMA
    """
    return prices.rolling(window=period).mean()


def calculate_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Рассчитать MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: Series цен закрытия
        fast: период быстрой EMA (default: 12)
        slow: период медленной EMA (default: 26)
        signal: период сигнальной линии (default: 9)
    
    Returns:
        Tuple (macd, signal_line, histogram)
    """
    # Рассчитываем быструю и медленную EMA
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # MACD линия
    macd_line = ema_fast - ema_slow
    
    # Сигнальная линия
    signal_line = calculate_ema(macd_line, signal)
    
    # Гистограмма
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Рассчитать Bollinger Bands
    
    Args:
        prices: Series цен закрытия
        period: период для расчета (default: 20)
        std_dev: количество стандартных отклонений (default: 2.0)
    
    Returns:
        Tuple (upper_band, middle_band, lower_band)
    """
    # Средняя линия (SMA)
    middle_band = calculate_sma(prices, period)
    
    # Стандартное отклонение
    std = prices.rolling(window=period).std()
    
    # Верхняя и нижняя полосы
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return upper_band, middle_band, lower_band


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Рассчитать ATR (Average True Range)
    
    Args:
        high: Series максимальных цен
        low: Series минимальных цен
        close: Series цен закрытия
        period: период для расчета (default: 14)
    
    Returns:
        Series со значениями ATR
    """
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Tuple[pd.Series, pd.Series]:
    """
    Рассчитать Stochastic Oscillator
    
    Args:
        high: Series максимальных цен
        low: Series минимальных цен
        close: Series цен закрытия
        period: период для расчета (default: 14)
    
    Returns:
        Tuple (%K, %D)
    """
    # %K
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    
    # %D (3-period SMA of %K)
    d = k.rolling(window=3).mean()
    
    return k, d


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавить все технические индикаторы к DataFrame
    
    Args:
        df: DataFrame с колонками: open, high, low, close, volume
    
    Returns:
        DataFrame с добавленными индикаторами
    """
    # RSI
    df['rsi'] = calculate_rsi(df['close'], period=14)
    
    # MACD
    macd, signal, histogram = calculate_macd(df['close'])
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_histogram'] = histogram
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
    df['bb_upper'] = bb_upper
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_lower
    
    # ATR
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    
    # Stochastic
    stoch_k, stoch_d = calculate_stochastic(df['high'], df['low'], df['close'])
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # Moving Averages
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['sma_50'] = calculate_sma(df['close'], 50)
    df['ema_12'] = calculate_ema(df['close'], 12)
    df['ema_26'] = calculate_ema(df['close'], 26)
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    
    return df
