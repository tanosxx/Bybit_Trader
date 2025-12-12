"""
Тест Dynamic Balance - проверка загрузки баланса из БД
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.executors.futures_executor import FuturesExecutor


async def test_balance():
    print("🧪 Testing Dynamic Balance...\n")
    
    # Создаём executor
    executor = FuturesExecutor()
    
    print(f"\n1️⃣ Initial state:")
    print(f"   virtual_balance: ${executor.virtual_balance:.2f}")
    print(f"   _balance_loaded: {executor._balance_loaded}")
    
    # Загружаем баланс из БД
    print(f"\n2️⃣ Loading balance from DB...")
    await executor.load_balance_from_db()
    
    print(f"\n3️⃣ After loading:")
    print(f"   virtual_balance: ${executor.virtual_balance:.2f}")
    print(f"   realized_pnl: ${executor.realized_pnl:.2f}")
    print(f"   _balance_loaded: {executor._balance_loaded}")
    
    # Проверяем расчёт позиции
    print(f"\n4️⃣ Position size calculation:")
    price = 95000.0  # BTC price
    leverage = 5
    quantity = executor.calculate_position_size(price, leverage)
    position_usd = executor.virtual_balance * executor.risk_per_trade * leverage
    
    print(f"   Price: ${price:.2f}")
    print(f"   Leverage: {leverage}x")
    print(f"   Position USD: ${position_usd:.2f}")
    print(f"   Quantity: {quantity:.8f} BTC")
    
    # Сравнение с фиксированным балансом
    print(f"\n5️⃣ Comparison:")
    fixed_position = 100.0 * executor.risk_per_trade * leverage
    print(f"   Fixed $100: ${fixed_position:.2f} position")
    print(f"   Dynamic ${executor.virtual_balance:.2f}: ${position_usd:.2f} position")
    print(f"   Increase: {position_usd / fixed_position:.2f}x")
    
    print(f"\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_balance())
