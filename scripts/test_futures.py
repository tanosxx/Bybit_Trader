"""
Тест фьючерсного модуля
Проверяет API и открывает тестовую позицию

ВНИМАНИЕ: Использует виртуальный баланс $100!
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.bybit_api import get_bybit_api
from core.executors.futures_executor import get_futures_executor
from core.executors.base_executor import TradeSignal
from config import settings


async def test_futures_api():
    """Тест Bybit Futures API"""
    print("="*60)
    print("🧪 FUTURES API TEST")
    print("="*60)
    
    api = get_bybit_api()
    
    # 1. Тест получения позиций
    print("\n1️⃣ Getting futures positions...")
    positions = await api.get_positions("BTCUSDT", "linear")
    print(f"   Positions: {positions}")
    
    # 2. Тест установки leverage
    print("\n2️⃣ Setting leverage to 5x...")
    result = await api.set_leverage("BTCUSDT", 5, "linear")
    print(f"   Result: {result}")
    
    # 3. Тест получения тикера
    print("\n3️⃣ Getting ticker...")
    ticker = await api.get_ticker("BTCUSDT")
    print(f"   BTC Price: ${ticker['last_price']:.2f}" if ticker else "   Failed")
    
    return ticker


async def test_futures_executor():
    """Тест FuturesExecutor"""
    print("\n" + "="*60)
    print("🧪 FUTURES EXECUTOR TEST")
    print("="*60)
    
    executor = get_futures_executor()
    
    print(f"\n📊 Executor Config:")
    print(f"   Virtual Balance: ${executor.virtual_balance}")
    print(f"   Leverage: {executor.leverage}x")
    print(f"   Risk per Trade: {executor.risk_per_trade*100}%")
    
    # Получаем цену
    api = get_bybit_api()
    ticker = await api.get_ticker("BTCUSDT")
    
    if not ticker:
        print("❌ Cannot get price")
        return
    
    price = ticker['last_price']
    
    # Рассчитываем размер позиции
    print(f"\n📐 Position Size Calculation:")
    print(f"   Price: ${price:.2f}")
    qty = executor.calculate_position_size(price)
    qty = executor.round_quantity("BTCUSDT", qty)
    print(f"   Final Quantity: {qty} BTC")
    
    # Создаём тестовый сигнал
    signal = TradeSignal(
        action="BUY",
        confidence=0.75,
        risk_score=5,
        reasoning="Test LONG position",
        symbol="BTCUSDT",
        price=price
    )
    
    print(f"\n🚀 Opening test LONG position...")
    print(f"   Signal: {signal.action} {signal.symbol}")
    print(f"   Confidence: {signal.confidence:.0%}")
    
    # Открываем позицию
    result = await executor.execute_signal(signal)
    
    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"   Order ID: {result.order_id}")
        print(f"   Side: {result.side}")
        print(f"   Quantity: {result.quantity}")
        print(f"   Price: ${result.price:.2f}")
    else:
        print(f"\n❌ FAILED: {result.error}")
    
    return result


async def test_short_position():
    """Тест SHORT позиции"""
    print("\n" + "="*60)
    print("🧪 SHORT POSITION TEST")
    print("="*60)
    
    executor = get_futures_executor()
    api = get_bybit_api()
    
    ticker = await api.get_ticker("ETHUSDT")
    if not ticker:
        print("❌ Cannot get ETH price")
        return
    
    price = ticker['last_price']
    
    signal = TradeSignal(
        action="SELL",
        confidence=0.70,
        risk_score=6,
        reasoning="Test SHORT position",
        symbol="ETHUSDT",
        price=price
    )
    
    print(f"\n🔻 Opening test SHORT position...")
    print(f"   Signal: {signal.action} {signal.symbol}")
    print(f"   Price: ${price:.2f}")
    
    result = await executor.execute_signal(signal)
    
    if result.success:
        print(f"\n✅ SHORT SUCCESS!")
        print(f"   Order ID: {result.order_id}")
        print(f"   Side: {result.side}")
    else:
        print(f"\n❌ SHORT FAILED: {result.error}")
    
    return result


async def main():
    print("\n" + "="*60)
    print("🚀 FUTURES MODULE TEST")
    print(f"   Virtual Balance: ${settings.futures_virtual_balance}")
    print(f"   Leverage: {settings.futures_leverage}x")
    print("="*60)
    
    # 1. Тест API
    await test_futures_api()
    
    # 2. Проверяем открытую позицию
    print("\n4️⃣ Checking open positions...")
    positions = await api.get_positions(None, "linear")
    for p in positions:
        print(f"   {p['symbol']}: {p['side']} {p['size']} @ ${p['entry_price']:.2f} | PnL: ${p['unrealized_pnl']:.2f}")
    
    # 3. Тест Executor (LONG) - уже выполнен
    # await test_futures_executor()
    
    print("\n" + "="*60)
    print("✅ FUTURES TEST COMPLETE")
    print("="*60)
    print("\n⚠️  Раскомментируй test_futures_executor() и test_short_position()")
    print("    чтобы открыть реальные тестовые позиции!")


if __name__ == "__main__":
    asyncio.run(main())
