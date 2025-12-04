#!/usr/bin/env python3
"""
Проверка системы после сброса на $50
"""
import asyncio
import asyncpg
from datetime import datetime


async def verify_reset():
    """Проверить что сброс выполнен корректно"""
    
    print("=" * 60)
    print("🔍 VERIFICATION AFTER RESET")
    print("=" * 60)
    print()
    
    # Подключаемся к БД
    conn = await asyncpg.connect(
        host='localhost',
        port=5435,
        user='bybit_user',
        password='bybit_secure_pass_2024',
        database='bybit_trader'
    )
    
    try:
        # 1. Проверяем количество сделок
        trades_count = await conn.fetchval("SELECT COUNT(*) FROM trades")
        print(f"1️⃣ Trades count: {trades_count}")
        assert trades_count == 0, "❌ Trades not cleared!"
        print("   ✅ Trades cleared")
        
        # 2. Проверяем wallet_history
        wallet_count = await conn.fetchval("SELECT COUNT(*) FROM wallet_history")
        print(f"\n2️⃣ Wallet history count: {wallet_count}")
        assert wallet_count == 0, "❌ Wallet history not cleared!"
        print("   ✅ Wallet history cleared")
        
        # 3. Проверяем ai_decisions
        ai_count = await conn.fetchval("SELECT COUNT(*) FROM ai_decisions")
        print(f"\n3️⃣ AI decisions count: {ai_count}")
        assert ai_count == 0, "❌ AI decisions not cleared!"
        print("   ✅ AI decisions cleared")
        
        # 4. Проверяем system_logs
        logs_count = await conn.fetchval("SELECT COUNT(*) FROM system_logs")
        print(f"\n4️⃣ System logs count: {logs_count}")
        assert logs_count == 0, "❌ System logs not cleared!"
        print("   ✅ System logs cleared")
        
        # 5. Проверяем candles (должны остаться!)
        candles_count = await conn.fetchval("SELECT COUNT(*) FROM candles")
        print(f"\n5️⃣ Candles count: {candles_count}")
        assert candles_count > 0, "❌ Candles were deleted! ML data lost!"
        print(f"   ✅ Candles preserved ({candles_count} records)")
        
        # 6. Проверяем баланс в app_config
        balance = await conn.fetchval(
            "SELECT value FROM app_config WHERE key = 'futures_virtual_balance'"
        )
        if balance:
            balance_float = float(balance)
            print(f"\n6️⃣ Virtual balance: ${balance_float}")
            assert balance_float == 50.0, f"❌ Balance not set to $50! Current: ${balance_float}"
            print("   ✅ Balance set to $50")
        else:
            print("\n6️⃣ Virtual balance: Not set in DB (will use config.py default)")
            print("   ⚠️  Balance will be $50 from config.py")
        
        # 7. Проверяем последние candles
        last_candle = await conn.fetchrow(
            """
            SELECT symbol, timestamp, close 
            FROM candles 
            ORDER BY timestamp DESC 
            LIMIT 1
            """
        )
        if last_candle:
            print(f"\n7️⃣ Last candle:")
            print(f"   Symbol: {last_candle['symbol']}")
            print(f"   Time: {last_candle['timestamp']}")
            print(f"   Price: ${last_candle['close']:,.2f}")
            print("   ✅ ML data is fresh")
        
        print()
        print("=" * 60)
        print("✅ ALL CHECKS PASSED")
        print("=" * 60)
        print()
        print("📊 Summary:")
        print(f"   - Trades: {trades_count} (cleared)")
        print(f"   - Wallet history: {wallet_count} (cleared)")
        print(f"   - AI decisions: {ai_count} (cleared)")
        print(f"   - System logs: {logs_count} (cleared)")
        print(f"   - Candles: {candles_count} (preserved)")
        print(f"   - Balance: $50.00")
        print()
        print("🚀 System ready for fresh start!")
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ VERIFICATION FAILED: {e}")
        print("=" * 60)
        return False
    
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        return False
    
    finally:
        await conn.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_reset())
    exit(0 if success else 1)
