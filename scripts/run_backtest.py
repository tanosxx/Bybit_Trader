"""
Скрипт для запуска бэктеста
Использование: python scripts/run_backtest.py

Запускать ТОЛЬКО на сервере!
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.backtester import BacktestEngine
from core.bybit_api import get_bybit_api
from datetime import datetime, timedelta


async def main():
    """Запуск бэктеста"""
    print("="*60)
    print("🔬 BYBIT TRADING BOT - BACKTEST")
    print("="*60)
    
    # Параметры - ОПТИМИЗИРОВАННЫЕ
    symbol = "BTCUSDT"
    timeframe = "5"  # 5-минутки меньше шума
    initial_balance = 10000.0
    position_size_pct = 0.10  # 10% от баланса (консервативнее)
    
    print(f"\n⚙️  Параметры:")
    print(f"   Symbol: {symbol}")
    print(f"   Timeframe: {timeframe}m")
    print(f"   Initial Balance: ${initial_balance:,.2f}")
    print(f"   Position Size: {position_size_pct*100:.0f}%")
    
    # Получаем исторические данные
    print(f"\n📥 Загрузка исторических данных...")
    
    api = get_bybit_api()
    
    # 5-минутные свечи - меньше шума
    klines = await api.get_klines(symbol, timeframe, limit=1000)
    
    if not klines:
        print("❌ Не удалось загрузить данные")
        return
    
    # Сортируем по времени
    klines.sort(key=lambda x: x['timestamp'])
    
    print(f"✅ Загружено {len(klines)} свечей ({timeframe}m)")
    
    if len(klines) < 100:
        print("❌ Недостаточно данных для бэктеста")
        return
    
    # Запускаем бэктест с оптимизированными параметрами
    print(f"\n🚀 Запуск бэктеста...")
    
    engine = BacktestEngine(
        initial_balance=initial_balance,
        commission_pct=0.1,
        slippage_pct=0.05,
        use_dynamic_risk=True
    )
    
    # Оптимизированные ATR multipliers
    engine.risk_manager.atr_multiplier_sl = 2.5  # Шире SL
    engine.risk_manager.atr_multiplier_tp = 4.0  # R:R = 1.6
    
    result = await engine.run(
        klines=klines,
        symbol=symbol,
        strategy="momentum",  # Новая стратегия
        position_size_pct=position_size_pct,
        max_open_trades=1
    )
    
    # Выводим отчёт
    engine.print_report(result)
    
    # Сравнение стратегий
    print("\n" + "="*60)
    print("📊 СРАВНЕНИЕ СТРАТЕГИЙ (5m, ATR SL:2.5 TP:4.0)")
    print("="*60)
    
    strategies = ["trend_following", "mean_reversion", "rsi_extreme", "momentum", "breakout"]
    
    for strat in strategies:
        engine.reset()
        engine.risk_manager.atr_multiplier_sl = 2.5
        engine.risk_manager.atr_multiplier_tp = 4.0
        
        res = await engine.run(
            klines=klines,
            symbol=symbol,
            strategy=strat,
            position_size_pct=position_size_pct,
            max_open_trades=1
        )
        
        print(f"\n{strat}:")
        print(f"   Trades: {res.total_trades} | Win Rate: {res.win_rate:.1f}%")
        print(f"   PnL: ${res.total_pnl:+,.2f} ({res.total_pnl_pct:+.2f}%)")
        print(f"   Max DD: {res.max_drawdown_pct:.2f}% | Sharpe: {res.sharpe_ratio:.2f} | PF: {res.profit_factor:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
