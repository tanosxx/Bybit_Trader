"""
Оптимизация параметров стратегий
Тестирует разные комбинации ATR multipliers и position sizes
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.backtester import BacktestEngine
from core.bybit_api import get_bybit_api
from itertools import product


async def main():
    """Оптимизация параметров"""
    print("="*60)
    print("🔬 PARAMETER OPTIMIZATION")
    print("="*60)
    
    # Загружаем данные
    api = get_bybit_api()
    klines = await api.get_klines("BTCUSDT", "5", limit=1000)  # 5-минутки лучше
    
    if not klines or len(klines) < 200:
        print("❌ Недостаточно данных")
        return
    
    print(f"✅ Загружено {len(klines)} свечей (5m)")
    
    # Параметры для тестирования
    atr_sl_multipliers = [1.5, 2.0, 2.5, 3.0]
    atr_tp_multipliers = [2.0, 3.0, 4.0, 5.0]
    position_sizes = [0.05, 0.10, 0.15]
    strategies = ["trend_following", "rsi_extreme"]
    
    best_result = None
    best_params = None
    best_pnl = -float('inf')
    
    results = []
    
    for strategy in strategies:
        for sl_mult in atr_sl_multipliers:
            for tp_mult in atr_tp_multipliers:
                if tp_mult <= sl_mult:  # R:R должен быть > 1
                    continue
                    
                for pos_size in position_sizes:
                    engine = BacktestEngine(
                        initial_balance=10000,
                        commission_pct=0.1,
                        slippage_pct=0.05,
                        use_dynamic_risk=True
                    )
                    
                    # Устанавливаем параметры
                    engine.risk_manager.atr_multiplier_sl = sl_mult
                    engine.risk_manager.atr_multiplier_tp = tp_mult
                    
                    result = await engine.run(
                        klines=klines,
                        symbol="BTCUSDT",
                        strategy=strategy,
                        position_size_pct=pos_size,
                        max_open_trades=1
                    )
                    
                    rr = tp_mult / sl_mult
                    
                    results.append({
                        'strategy': strategy,
                        'sl_mult': sl_mult,
                        'tp_mult': tp_mult,
                        'pos_size': pos_size,
                        'rr': rr,
                        'trades': result.total_trades,
                        'win_rate': result.win_rate,
                        'pnl': result.total_pnl,
                        'pnl_pct': result.total_pnl_pct,
                        'max_dd': result.max_drawdown_pct,
                        'sharpe': result.sharpe_ratio,
                        'profit_factor': result.profit_factor
                    })
                    
                    if result.total_pnl > best_pnl and result.total_trades >= 5:
                        best_pnl = result.total_pnl
                        best_result = result
                        best_params = {
                            'strategy': strategy,
                            'sl_mult': sl_mult,
                            'tp_mult': tp_mult,
                            'pos_size': pos_size
                        }
    
    # Сортируем по PnL
    results.sort(key=lambda x: x['pnl'], reverse=True)
    
    print("\n" + "="*60)
    print("📊 TOP 10 CONFIGURATIONS")
    print("="*60)
    
    for i, r in enumerate(results[:10], 1):
        print(f"\n{i}. {r['strategy']} | SL:{r['sl_mult']}x TP:{r['tp_mult']}x | Size:{r['pos_size']*100:.0f}%")
        print(f"   Trades: {r['trades']} | WR: {r['win_rate']:.1f}% | PnL: ${r['pnl']:+.2f} ({r['pnl_pct']:+.2f}%)")
        print(f"   Max DD: {r['max_dd']:.2f}% | PF: {r['profit_factor']:.2f} | R:R: 1:{r['rr']:.1f}")
    
    if best_params:
        print("\n" + "="*60)
        print("🏆 BEST CONFIGURATION")
        print("="*60)
        print(f"   Strategy: {best_params['strategy']}")
        print(f"   ATR SL Multiplier: {best_params['sl_mult']}")
        print(f"   ATR TP Multiplier: {best_params['tp_mult']}")
        print(f"   Position Size: {best_params['pos_size']*100:.0f}%")
        print(f"   PnL: ${best_pnl:+.2f}")


if __name__ == "__main__":
    asyncio.run(main())
