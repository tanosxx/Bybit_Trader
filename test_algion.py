"""
Тестирование Algion Client
Проверка работы fallback для Gemini
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Проверяем токен
algion_token = os.getenv("ALGION_BEARER_TOKEN")
if not algion_token:
    print("❌ ALGION_BEARER_TOKEN не установлен в .env")
    print("   Добавьте: ALGION_BEARER_TOKEN=your_token_here")
    sys.exit(1)

print("="*70)
print("🧪 ТЕСТИРОВАНИЕ ALGION CLIENT")
print("="*70)

# Импортируем клиент
try:
    from core.algion_client import get_algion_client
    print("✅ Algion Client импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Получаем клиент
client = get_algion_client()
if not client:
    print("❌ Не удалось инициализировать Algion Client")
    sys.exit(1)

print(f"✅ Algion Client инициализирован")
print(f"   Токен: {algion_token[:20]}...")
print(f"   Модели: {', '.join(client.models)}")
print()

# Тест 1: Простой запрос
print("-"*70)
print("📝 ТЕСТ 1: Простой запрос")
print("-"*70)

result = client.generate_text(
    prompt="Say hello in one sentence.",
    system_prompt="You are a helpful assistant.",
    temperature=0.7,
    max_tokens=50
)

if result:
    print(f"✅ Результат: {result}")
else:
    print("❌ Запрос не удался")

print()

# Тест 2: Анализ рынка (как Strategic Brain)
print("-"*70)
print("📊 ТЕСТ 2: Анализ рынка (Strategic Brain)")
print("-"*70)

market_prompt = """Market Data:
BTC: $90,000 (-2.5% today)
ETH: $3,200 (-3.8% today)
SOL: $130 (-4.2% today)

News: Market correction, fear index rising.

Analyze and respond with ONE WORD: BULL_RUSH, BEAR_CRASH, SIDEWAYS, or UNCERTAIN"""

system_prompt = """You are a crypto market analyst. Respond with ONLY ONE WORD:
- BULL_RUSH (strong uptrend)
- BEAR_CRASH (strong downtrend)
- SIDEWAYS (ranging market)
- UNCERTAIN (high volatility)"""

result = client.generate_text(
    prompt=market_prompt,
    system_prompt=system_prompt,
    temperature=0.3,
    max_tokens=50
)

if result:
    print(f"✅ Результат: {result}")
    
    # Проверяем что ответ валидный
    result_clean = result.strip().upper()
    valid_regimes = ["BULL_RUSH", "BEAR_CRASH", "SIDEWAYS", "UNCERTAIN"]
    
    if any(regime in result_clean for regime in valid_regimes):
        print(f"✅ Ответ валидный (содержит режим)")
    else:
        print(f"⚠️ Ответ не содержит валидный режим")
else:
    print("❌ Запрос не удался")

print()

# Тест 3: Ротация моделей (симуляция rate limit)
print("-"*70)
print("🔄 ТЕСТ 3: Ротация моделей")
print("-"*70)

print(f"Текущая модель: {client._get_current_model()}")
print("Симулируем переключение...")

for i in range(len(client.models) + 1):
    current = client._get_current_model()
    print(f"  Попытка {i+1}: {current}")
    has_next = client._rotate_model()
    if not has_next:
        print(f"  → Все модели исчерпаны, сброс на первую")
        break

print()

# Статистика
print("-"*70)
print("📊 СТАТИСТИКА")
print("-"*70)

stats = client.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

print()
print("="*70)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("="*70)
