"""
Конфигурация Bybit Trading Bot v2.0
Гибридная система: SPOT + FUTURES
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, Literal, Dict


class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=(),
        extra="ignore"  # Игнорировать неизвестные поля из .env
    )
    
    # Bybit API
    bybit_api_key: str
    bybit_api_secret: str
    bybit_testnet: bool = False
    bybit_base_url: str = "https://api-demo.bybit.com"  # Demo по умолчанию
    
    # Database
    database_url: str
    
    # AI APIs - Gemini (3 ключа для ротации)
    google_api_key_1: Optional[str] = None
    google_api_key_2: Optional[str] = None
    google_api_key_3: Optional[str] = None
    
    # AI APIs - OpenRouter (резервный)
    openrouter_api_key: str = "dummy"  # Optional, not used currently
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # News API (CryptoPanic) - несколько ключей для ротации
    cryptopanic_api_key: Optional[str] = None
    cryptopanic_api_key_2: Optional[str] = None
    cryptopanic_api_key_3: Optional[str] = None
    
    # Strategic Brain - Claude 3.5 Sonnet через OhMyGPT
    # Примечание: эти настройки читаются напрямую через os.getenv() в strategic_brain.py
    # чтобы избежать конфликтов с Pydantic validation
    
    # ========== HYBRID TRADING MODE ==========
    # Режим торговли: 'SPOT', 'FUTURES', 'HYBRID' (оба одновременно)
    trading_mode: Literal['SPOT', 'FUTURES', 'HYBRID'] = 'HYBRID'
    
    # Включение/выключение рынков
    spot_enabled: bool = False  # Временно отключено (нет монет на Demo)
    futures_enabled: bool = True
    
    # ========== SPOT Settings ==========
    spot_virtual_balance: float = 100.0  # Виртуальный лимит для SPOT
    spot_risk_per_trade: float = 0.10  # 10% от баланса на сделку
    
    # ========== FUTURES Settings - SMART GROWTH $100 ==========
    # КРИТИЧНО: Бот использует ТОЛЬКО этот баланс для расчёта позиций!
    futures_virtual_balance: float = 100.0  # $100 стартовый капитал (Smart Growth)
    futures_leverage: int = 5  # Плечо 5x (Buying Power $500 - безопасно)
    futures_risk_per_trade: float = 0.12  # 12% от баланса в маржу = $12 (позиция $60 с плечом)
    futures_margin_mode: Literal['ISOLATED', 'CROSS'] = 'ISOLATED'  # Изолированная маржа
    
    # Legacy (для совместимости)
    leverage: int = 5
    margin_mode: Literal['ISOLATED', 'CROSS'] = 'ISOLATED'
    
    # ========== TRAILING STOP Settings - SMART GROWTH $100 ==========
    trailing_stop_enabled: bool = True  # Включить трейлинг-стоп
    trailing_activation_pct: float = 0.8  # Активация при +0.8% профита (быстрый безубыток)
    trailing_callback_pct: float = 0.4  # Дистанция трейлинга 0.4% (фиксируем прибыль)
    
    # ========== FUNDING RATE Filter ==========
    funding_rate_filter_enabled: bool = True  # Проверять funding rate
    funding_rate_max_pct: float = 0.05  # Макс. ставка 0.05% для входа
    funding_time_window_minutes: int = 60  # Окно до выплаты (минуты)
    
    # ========== POSITION LIMITS - SMART GROWTH $100 ==========
    futures_max_open_positions: int = 5  # Макс. 5 позиций (5 × $12 = $60 маржи, $40 буфер)
    futures_max_orders_per_symbol: int = 15  # Макс. ордеров на один символ
    futures_max_total_orders: int = 80  # Макс. всего ордеров
    futures_min_confidence: float = 0.60  # Мин. confidence 60% для LONG
    futures_min_confidence_short: float = 0.60  # Мин. confidence 60% для SHORT (равно LONG)
    futures_check_sl_tp_interval: int = 30  # Проверка SL/TP каждые 30 сек
    
    # ========== SIMULATED REALISM - SMART GROWTH $100 ==========
    # Реалистичный учёт комиссий для подготовки к Real Trading
    estimated_fee_rate: float = 0.0006  # 0.06% Taker fee (Bybit standard)
    min_profit_threshold_multiplier: float = 2.0  # Минимальный профит = 2x комиссия
    min_profit_threshold_pct: float = 0.6  # Минимальный TP 0.6% (комиссия + проскальзывание + микро-профит)
    simulate_fees_in_demo: bool = True  # Учитывать комиссии в Demo режиме
    
    # ========== TRADING HOURS FILTER ==========
    trading_hours_enabled: bool = False  # ОТКЛЮЧЕНО - торгуем 24/7
    trading_hours_start: int = 0  # Начало торговли (UTC)
    trading_hours_end: int = 24  # Конец торговли (UTC)
    
    # ========== TREND FILTER ==========
    require_trend_confirmation: bool = False  # ОТКЛЮЧЕНО - торгуем и против тренда
    min_trend_strength: float = 0.2  # Минимальная сила тренда для входа
    
    # Trading Settings
    initial_balance: float = 50.0
    scan_interval: int = 60  # секунд
    max_open_positions: int = 3
    max_daily_loss: float = 5.0  # $5
    
    # ========== МОДУЛЬ 2: Динамический Риск-менеджмент ==========
    # ATR-based Risk Management
    use_atr_stops: bool = True  # Использовать ATR для SL/TP
    atr_period: int = 14  # Период ATR
    atr_sl_multiplier: float = 2.0  # SL = Price ± (ATR * multiplier)
    atr_tp_multiplier: float = 3.0  # TP = Price ± (ATR * multiplier)
    
    # Fallback фиксированные стопы (если ATR недоступен) - OPTIMIZED R:R 1:2
    max_position_size_pct: float = 15.0  # 15% от баланса (уменьшено для безопасности)
    stop_loss_pct: float = 1.5  # -1.5% (уменьшено для лучшего R:R)
    take_profit_pct: float = 3.0  # +3% (R:R = 1:2)
    max_drawdown_pct: float = 15.0  # -15% emergency stop (ужесточено)
    
    # Trading Pairs
    trading_pairs: list = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    
    # Futures-specific pairs (linear USDT perpetuals)
    # Добавлены BNB и XRP для большей активности
    futures_pairs: list = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]


settings = Settings()


# ========== Вспомогательные функции для Hybrid Trading ==========
def is_hybrid_mode() -> bool:
    """Проверить, включен ли гибридный режим"""
    return settings.trading_mode == 'HYBRID'


def is_spot_enabled() -> bool:
    """Проверить, включен ли SPOT"""
    return settings.spot_enabled and settings.trading_mode in ['SPOT', 'HYBRID']


def is_futures_enabled() -> bool:
    """Проверить, включены ли фьючерсы"""
    return settings.futures_enabled and settings.trading_mode in ['FUTURES', 'HYBRID']


def get_spot_pairs() -> list:
    """Получить список SPOT пар"""
    return settings.trading_pairs


def get_futures_pairs() -> list:
    """Получить список Futures пар"""
    return settings.futures_pairs


# Legacy functions (для совместимости)
def is_futures_mode() -> bool:
    return settings.trading_mode == 'FUTURES'


def get_category() -> str:
    return 'linear' if is_futures_mode() else 'spot'


def get_trading_pairs() -> list:
    return settings.futures_pairs if is_futures_mode() else settings.trading_pairs


# ========== FEE CALCULATION (Simulated Realism) ==========
def calculate_fees(entry_value: float, exit_value: float, fee_rate: float = None) -> Dict[str, float]:
    """
    Рассчитать комиссии для сделки
    
    Args:
        entry_value: Стоимость входа (quantity * entry_price)
        exit_value: Стоимость выхода (quantity * exit_price)
        fee_rate: Ставка комиссии (по умолчанию из settings)
    
    Returns:
        {
            'entry_fee': float,  # Комиссия при входе
            'exit_fee': float,   # Комиссия при выходе
            'total_fee': float,  # Общая комиссия
            'fee_rate': float    # Использованная ставка
        }
    """
    if fee_rate is None:
        fee_rate = settings.estimated_fee_rate
    
    entry_fee = entry_value * fee_rate
    exit_fee = exit_value * fee_rate
    total_fee = entry_fee + exit_fee
    
    return {
        'entry_fee': entry_fee,
        'exit_fee': exit_fee,
        'total_fee': total_fee,
        'fee_rate': fee_rate
    }


def calculate_net_pnl(gross_pnl: float, entry_value: float, exit_value: float) -> Dict[str, float]:
    """
    Рассчитать чистый PnL с учётом комиссий
    
    Args:
        gross_pnl: Валовая прибыль (как на бирже)
        entry_value: Стоимость входа
        exit_value: Стоимость выхода
    
    Returns:
        {
            'gross_pnl': float,  # Валовая прибыль
            'fees': dict,        # Детали комиссий
            'net_pnl': float,    # Чистая прибыль (в карман)
            'fee_impact_pct': float  # Влияние комиссий в %
        }
    """
    fees = calculate_fees(entry_value, exit_value)
    net_pnl = gross_pnl - fees['total_fee']
    
    # Процент влияния комиссий
    fee_impact_pct = 0.0
    if gross_pnl != 0:
        fee_impact_pct = (fees['total_fee'] / abs(gross_pnl)) * 100
    
    return {
        'gross_pnl': gross_pnl,
        'fees': fees,
        'net_pnl': net_pnl,
        'fee_impact_pct': fee_impact_pct
    }


def is_trade_profitable_after_fees(
    entry_price: float,
    take_profit: float,
    quantity: float,
    side: str = "LONG"
) -> Dict[str, any]:
    """
    Проверить, будет ли сделка прибыльной после комиссий
    
    Args:
        entry_price: Цена входа
        take_profit: Цена TP
        quantity: Количество
        side: LONG или SHORT
    
    Returns:
        {
            'is_profitable': bool,  # Прибыльна ли сделка
            'gross_profit': float,  # Валовая прибыль
            'net_profit': float,    # Чистая прибыль
            'min_required_profit': float,  # Минимальный профит для окупаемости
            'reason': str  # Объяснение
        }
    """
    entry_value = entry_price * quantity
    exit_value = take_profit * quantity
    
    # Рассчитываем валовую прибыль
    if side.upper() in ["LONG", "BUY"]:
        gross_profit = (take_profit - entry_price) * quantity
    else:  # SHORT
        gross_profit = (entry_price - take_profit) * quantity
    
    # Рассчитываем комиссии
    fees = calculate_fees(entry_value, exit_value)
    total_fee = fees['total_fee']
    
    # Минимальный профит = 2x комиссия (по умолчанию)
    min_required_profit = total_fee * settings.min_profit_threshold_multiplier
    
    # Чистая прибыль
    net_profit = gross_profit - total_fee
    
    # Проверка прибыльности
    is_profitable = net_profit > 0 and gross_profit >= min_required_profit
    
    reason = ""
    if not is_profitable:
        if net_profit <= 0:
            reason = f"Net profit negative: ${net_profit:.2f}"
        else:
            reason = f"Profit too small: ${gross_profit:.2f} < ${min_required_profit:.2f} (min required)"
    else:
        reason = f"Profitable: ${net_profit:.2f} net (after ${total_fee:.2f} fees)"
    
    return {
        'is_profitable': is_profitable,
        'gross_profit': gross_profit,
        'net_profit': net_profit,
        'total_fee': total_fee,
        'min_required_profit': min_required_profit,
        'reason': reason
    }


# AI Prompts для Gemini (специальный промпт чтобы не тупил!)
GEMINI_CRYPTO_ANALYSIS_PROMPT = """Ты профессиональный криптотрейдер. Проанализируй рынок и дай рекомендацию.

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО валидным JSON
2. БЕЗ объяснений, БЕЗ markdown, БЕЗ блоков кода
3. Будь решительным - выбирай BUY (покупка), SELL (продажа) или SKIP (пропустить)
4. Оценка риска: 1 (безопасно) до 10 (очень рискованно)
5. ВАЖНО: Рассматривай как LONG (покупка), так и SHORT (продажа) позиции!
6. SHORT позиции выгодны при падении цены - не бойся их использовать!

Данные рынка:
{market_data}

Отвечай ТОЧНО в таком JSON формате:
{{
  "decision": "BUY" или "SELL" или "SKIP",
  "risk_score": 1-10,
  "confidence": 0.0-1.0,
  "reasoning": "краткое объяснение на русском в 1-2 предложениях",
  "key_factors": ["фактор1", "фактор2", "фактор3"]
}}

JSON ответ:"""


# AI Prompts для OpenRouter (Claude/GPT)
OPENROUTER_CRYPTO_ANALYSIS_PROMPT = """Analyze this crypto market and provide trading recommendation.

Market Data:
{market_data}

Respond with JSON:
{{
  "decision": "BUY/SELL/SKIP",
  "risk_score": 1-10,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "key_factors": ["factor1", "factor2"]
}}"""


# Strategy Configs
STRATEGY_CONFIGS = {
    "conservative": {
        "name": "Conservative",
        "max_risk": 3,
        "min_confidence": 0.80,
        "position_size_pct": 10.0,
        "indicators_weight": {
            "rsi": 0.4,
            "macd": 0.3,
            "bb": 0.3
        }
    },
    "balanced": {
        "name": "Balanced",
        "max_risk": 6,
        "min_confidence": 0.65,
        "position_size_pct": 15.0,
        "indicators_weight": {
            "rsi": 0.35,
            "macd": 0.35,
            "bb": 0.30
        }
    },
    "aggressive": {
        "name": "Aggressive",
        "max_risk": 8,
        "min_confidence": 0.50,
        "position_size_pct": 20.0,
        "indicators_weight": {
            "rsi": 0.3,
            "macd": 0.4,
            "bb": 0.3
        }
    }
}
