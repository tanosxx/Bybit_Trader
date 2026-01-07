"""
Конфигурация Bybit Trading Bot v2.0 - Simple Profit Edition

Философия: Простота = Прибыль
Убраны все ML настройки, оставлена только чистая математика.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal, List


class Settings(BaseSettings):
    """Настройки приложения v2.0"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=(),
        extra="ignore"
    )
    
    # ========== BYBIT API ==========
    bybit_api_key: str
    bybit_api_secret: str
    bybit_testnet: bool = True  # Demo trading
    bybit_base_url: str = "https://api-demo.bybit.com"
    
    # ========== DATABASE ==========
    database_url: str
    
    # ========== TELEGRAM (Optional) ==========
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # ========== TRADING MODE ==========
    trading_mode: Literal['FUTURES'] = 'FUTURES'  # Только фьючерсы в v2
    
    # ========== FUTURES SETTINGS ==========
    # Баланс и риски
    futures_virtual_balance: float = 100.0  # $100 стартовый капитал
    futures_leverage: int = 3  # Плечо 3x (консервативно)
    futures_risk_per_trade: float = 0.05  # 5% от баланса на сделку
    futures_margin_mode: Literal['ISOLATED'] = 'ISOLATED'
    
    # Торговые пары (9 пар для большей волатильности)
    futures_pairs: List[str] = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "AVAXUSDT",
        "LINKUSDT"
    ]
    
    # Лимиты позиций
    futures_max_open_positions: int = 3  # Макс. 3 позиции одновременно
    futures_max_positions_per_symbol: int = 1  # 1 позиция на символ
    
    # ========== RSI GRID STRATEGY ==========
    # RSI параметры (смягчены для большей частоты сделок)
    rsi_period: int = 14
    rsi_oversold: int = 35  # Было 30 (смягчено)
    rsi_overbought: int = 65  # Было 70 (смягчено)
    
    # Bollinger Bands параметры (фильтр безопасности)
    bb_period: int = 20
    bb_std: float = 2.0
    require_bb_touch: bool = True  # Цена должна касаться линий BB
    
    # Take Profit / Stop Loss
    take_profit_pct: float = 1.5  # +1.5%
    stop_loss_pct: float = 2.0  # -2.0%
    
    # Таймфрейм
    timeframe: str = "15"  # 15 минут
    
    # ========== КОМИССИИ ==========
    estimated_fee_rate: float = 0.0006  # 0.06% Taker fee
    
    # ========== ИНТЕРВАЛЫ ==========
    scan_interval_seconds: int = 60  # Сканировать рынки каждые 60 секунд
    check_positions_interval: int = 30  # Проверять позиции каждые 30 секунд
    sync_positions_interval: int = 30  # Синхронизация с биржей каждые 30 секунд


# Создаём глобальный экземпляр настроек
settings = Settings()
