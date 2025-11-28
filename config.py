"""
Конфигурация Bybit Trading Bot
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
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
    openrouter_api_key: str
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # News API (CryptoPanic) - несколько ключей для ротации
    cryptopanic_api_key: Optional[str] = None
    cryptopanic_api_key_2: Optional[str] = None
    cryptopanic_api_key_3: Optional[str] = None
    
    # Trading Settings
    initial_balance: float = 50.0
    scan_interval: int = 60  # секунд
    max_open_positions: int = 3
    max_daily_loss: float = 5.0  # $5
    
    # Risk Management
    max_position_size_pct: float = 20.0  # 20% от баланса
    stop_loss_pct: float = 2.0  # -2%
    take_profit_pct: float = 3.0  # +3%
    max_drawdown_pct: float = 20.0  # -20% emergency stop
    
    # Trading Pairs
    trading_pairs: list = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


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
