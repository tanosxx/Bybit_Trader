"""
Полный сброс бота - очистка всех данных и сброс баланса
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime
from database.db import async_session, engine
from database.models import Trade, WalletHistory, SystemLog, Candle
from sqlalchemy import delete, text

async def main():
    print("\n" + "="*80)
    print("🔄 FULL RESET - Полная очистка данных")
    print("="*80 + "\n")
    
    async with async_session() as session:
        # 1. Удаляем все сделки
        result = await session.execute(delete(Trade))
        trades_deleted = result.rowcount
        print(f"✅ Удалено сделок: {trades_deleted}")
        
        # 2. Удаляем историю баланса
        result = await session.execute(delete(WalletHistory))
        wallet_deleted = result.rowcount
        print(f"✅ Удалено записей баланса: {wallet_deleted}")
        
        # 3. Удаляем системные логи
        result = await session.execute(delete(SystemLog))
        logs_deleted = result.rowcount
        print(f"✅ Удалено логов: {logs_deleted}")
        
        # 4. Удаляем свечи (опционально, можно оставить для ML)
        # result = await session.execute(delete(Candle))
        # candles_deleted = result.rowcount
        # print(f"✅ Удалено свечей: {candles_deleted}")
        
        # 5. Создаем начальную запись баланса
        initial_wallet = WalletHistory(
            balance_usdt=500.0,
            equity=500.0,
            change_amount=0.0,
            change_reason="Initial balance (FUTURES virtual)"
        )
        session.add(initial_wallet)
        
        await session.commit()
        
        print(f"\n✅ Начальный баланс установлен: $500.00 (FUTURES virtual)")
    
    print("\n" + "="*80)
    print("✅ RESET COMPLETE!")
    print("="*80 + "\n")
    
    print("📊 Текущее состояние:")
    print("   - Сделок: 0")
    print("   - Баланс: $500.00")
    print("   - Режим: HYBRID (SPOT + FUTURES)")
    print("   - Фьючерсы: Enabled")
    print("   - Leverage: 5x")
    print("   - Margin: ISOLATED")
    print("\n🚀 Бот готов к запуску!\n")

if __name__ == "__main__":
    asyncio.run(main())
