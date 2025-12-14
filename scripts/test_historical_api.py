"""
Тестовый скрипт для проверки новых методов Bybit API
Запускать на сервере в Docker!
"""
import asyncio
import sys
sys.path.append('/app')

from core.bybit_api import get_bybit_api
from datetime import datetime, timedelta


async def test_trade_history_full():
    """Тест получения полной истории сделок"""
    print("\n" + "="*60)
    print("TEST 1: get_trade_history_full()")
    print("="*60)
    
    api = get_bybit_api()
    trades = await api.get_trade_history_full(symbol="BTCUSDT", limit=100)
    
    print(f"\n📊 Results:")
    print(f"   Total trades: {len(trades)}")
    
    if trades:
        print(f"\n   First trade:")
        print(f"   {trades[0]}")
        print(f"\n   Last trade:")
        print(f"   {trades[-1]}")


async def test_closed_pnl_history():
    """Тест получения истории PnL"""
    print("\n" + "="*60)
    print("TEST 2: get_closed_pnl_history()")
    print("="*60)
    
    api = get_bybit_api()
    pnl_records = await api.get_closed_pnl_history(symbol="BTCUSDT", limit=100)
    
    print(f"\n📊 Results:")
    print(f"   Total PnL records: {len(pnl_records)}")
    
    if pnl_records:
        print(f"\n   First record:")
        print(f"   {pnl_records[0]}")


async def test_wallet_transactions():
    """Тест получения транзакций кошелька"""
    print("\n" + "="*60)
    print("TEST 3: get_wallet_transactions()")
    print("="*60)
    
    api = get_bybit_api()
    transactions = await api.get_wallet_transactions(coin="USDT", limit=50)
    
    print(f"\n📊 Results:")
    print(f"   Total transactions: {len(transactions)}")
    
    if transactions:
        print(f"\n   First transaction:")
        print(f"   {transactions[0]}")


async def test_klines_historical():
    """Тест получения исторических свечей"""
    print("\n" + "="*60)
    print("TEST 4: get_klines_historical()")
    print("="*60)
    
    api = get_bybit_api()
    
    # Получаем данные за последние 7 дней
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
    
    klines = await api.get_klines_historical(
        symbol="BTCUSDT",
        interval="60",  # 1 hour
        start_time=start_time,
        end_time=end_time,
        limit=1000
    )
    
    print(f"\n📊 Results:")
    print(f"   Total candles: {len(klines)}")
    print(f"   Period: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    
    if klines:
        print(f"\n   First candle:")
        print(f"   {klines[0]}")
        print(f"\n   Last candle:")
        print(f"   {klines[-1]}")


async def main():
    """Запуск всех тестов"""
    print("\n🚀 Starting Bybit API Historical Methods Tests")
    print("=" * 60)
    
    try:
        # Test 1: Trade History
        await test_trade_history_full()
        
        # Test 2: PnL History
        await test_closed_pnl_history()
        
        # Test 3: Wallet Transactions
        await test_wallet_transactions()
        
        # Test 4: Historical Klines
        await test_klines_historical()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
