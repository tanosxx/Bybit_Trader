"""
Скрипт для проверки балансов на Demo счёте Bybit
и переноса средств между кошельками
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bybit_api import get_bybit_api


async def check_all_balances():
    """Проверить все балансы на Demo счёте"""
    api = get_bybit_api()
    
    print("="*60)
    print("💰 BYBIT DEMO ACCOUNT BALANCES")
    print("="*60)
    
    # Unified Trading Account
    print("\n📊 Unified Trading Account:")
    balances = await api.get_wallet_balance()
    
    if not balances:
        print("   ❌ Failed to get balance")
        return None
    
    total_usdt = 0
    coins_with_balance = []
    
    for coin, data in balances.items():
        total = data['total']
        available = data['available']
        
        if total > 0.01:  # Показываем только значимые балансы
            print(f"\n   {coin}:")
            print(f"      Total: {total:.4f}")
            print(f"      Available: {available:.4f}")
            
            coins_with_balance.append({
                'coin': coin,
                'total': total,
                'available': available
            })
            
            # Конвертируем в USDT для общей суммы
            if coin == 'USDT':
                total_usdt += total
            elif coin == 'USDC':
                total_usdt += total  # 1:1 с USDT
    
    print(f"\n💵 Total (USDT equivalent): ~${total_usdt:.2f}")
    
    return coins_with_balance


async def get_futures_balance():
    """Получить баланс фьючерсного кошелька"""
    api = get_bybit_api()
    
    print("\n📊 Checking Futures Wallet...")
    
    # Для Unified Account баланс общий
    # Проверим открытые позиции
    positions = await api.get_positions()
    
    if positions:
        print(f"\n⚠️  Open Positions: {len(positions)}")
        for pos in positions:
            print(f"   - {pos['symbol']}: {pos['side']} {pos['size']} @ ${pos['entry_price']}")
            print(f"     Unrealized PnL: ${pos['unrealized_pnl']:.2f}")
    else:
        print("   ✅ No open positions")
    
    return positions


async def show_transfer_options(coins_with_balance):
    """Показать опции для переноса средств"""
    print("\n" + "="*60)
    print("💱 TRANSFER OPTIONS")
    print("="*60)
    
    print("\n📝 Bybit Demo Account использует Unified Trading Account")
    print("   Это значит что все средства уже в одном кошельке!")
    print("   USDT, USDC, BTC, ETH и другие монеты доступны для торговли.")
    
    print("\n💡 Рекомендации:")
    print("   1. Для фьючерсной торговли используется USDT из Unified Account")
    print("   2. Не нужно переводить средства между кошельками")
    print("   3. Можно установить виртуальный лимит в config.py:")
    print("      futures_virtual_balance = 50.0  # или 100.0")
    
    # Показываем текущий USDT баланс
    usdt_balance = next((c['total'] for c in coins_with_balance if c['coin'] == 'USDT'), 0)
    usdc_balance = next((c['total'] for c in coins_with_balance if c['coin'] == 'USDC'), 0)
    
    print(f"\n💵 Available for Futures Trading:")
    print(f"   USDT: ${usdt_balance:.2f}")
    print(f"   USDC: ${usdc_balance:.2f}")
    print(f"   Total: ${usdt_balance + usdc_balance:.2f}")
    
    print("\n⚠️  ВАЖНО:")
    print("   Demo счёт имеет виртуальный баланс ~$185k")
    print("   Для реалистичного тестирования рекомендуем:")
    print("   - Установить futures_virtual_balance = 50 или 100")
    print("   - Бот будет использовать только этот лимит для расчёта позиций")
    print("   - Реальный баланс на Demo не будет затронут")


async def suggest_config_changes():
    """Предложить изменения в конфиге"""
    print("\n" + "="*60)
    print("⚙️  RECOMMENDED CONFIG CHANGES")
    print("="*60)
    
    print("\n📝 В файле config.py измените:")
    print("""
    # ========== FUTURES Settings ==========
    futures_virtual_balance: float = 50.0  # Стартовый капитал $50
    futures_leverage: int = 3  # Консервативное плечо 3x
    futures_risk_per_trade: float = 0.10  # 10% от баланса на сделку
    futures_margin_mode: Literal['ISOLATED', 'CROSS'] = 'ISOLATED'
    
    # ========== POSITION LIMITS ==========
    futures_max_open_positions: int = 5  # Макс 5 позиций одновременно
    futures_min_confidence: float = 0.60  # Мин 60% уверенность AI
    """)
    
    print("\n💡 Это даст:")
    print("   - Реалистичный стартовый капитал ($50)")
    print("   - Безопасное плечо (3x)")
    print("   - Контролируемый риск (10% на сделку = $5)")
    print("   - Максимум 5 позиций одновременно")
    print("   - Только уверенные сигналы (60%+)")


async def main():
    """Главная функция"""
    print("\n🔍 Checking Bybit Demo Account...")
    
    # 1. Проверить все балансы
    coins = await check_all_balances()
    
    if not coins:
        print("\n❌ Failed to get balances")
        return
    
    # 2. Проверить фьючерсный кошелёк
    await get_futures_balance()
    
    # 3. Показать опции переноса
    await show_transfer_options(coins)
    
    # 4. Предложить изменения конфига
    await suggest_config_changes()
    
    print("\n" + "="*60)
    print("✅ ANALYSIS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
