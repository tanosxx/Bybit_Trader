"""
Тест Strategy Scaler - Проверка работы Tier System
"""
import sys
sys.path.insert(0, '/app')

from core.strategy_scaler import get_strategy_scaler
import json


def test_strategy_scaler():
    """Тестирование Strategy Scaler с разными балансами"""
    
    print("="*80)
    print("🧪 TESTING STRATEGY SCALER")
    print("="*80)
    
    scaler = get_strategy_scaler()
    
    # Тестовые балансы
    test_cases = [
        (50, "Tier 1 - Survival Mode"),
        (150, "Tier 1 - Survival Mode"),
        (250, "Tier 2 - Growth Mode"),
        (377, "Tier 2 - Growth Mode (CURRENT)"),
        (500, "Tier 2 - Growth Mode"),
        (700, "Tier 3 - Dominion Mode"),
        (1000, "Tier 3 - Dominion Mode"),
    ]
    
    print(f"\n📊 Testing {len(test_cases)} balance scenarios:\n")
    
    for balance, expected in test_cases:
        print(f"\n{'='*80}")
        print(f"💰 Balance: ${balance:.2f} - Expected: {expected}")
        print(f"{'='*80}")
        
        result = scaler.update_strategy(balance)
        
        print(f"\n✅ Result:")
        print(f"   Tier Changed: {result['tier_changed']}")
        print(f"   Tier: {result['tier_name']} ({result['tier_id']})")
        print(f"   Active Pairs: {', '.join(result['active_pairs'])}")
        print(f"   Symbols to Scan: {', '.join(result['symbols_to_scan'])}")
        print(f"   Max Positions: {result['max_open_positions']}")
        print(f"   Risk per Trade: {result['risk_per_trade']*100:.0f}%")
        print(f"   Min Confidence: {result['min_confidence']*100:.0f}%")
        
        # Проверка что BTCUSDT в symbols_to_scan
        if 'BTCUSDT' in result['symbols_to_scan']:
            print(f"   ✅ BTCUSDT included for correlation analysis")
        else:
            print(f"   ❌ WARNING: BTCUSDT missing from scan list!")
        
        # Проверка что XRPUSDT исключён
        if 'XRPUSDT' not in result['active_pairs']:
            print(f"   ✅ XRPUSDT excluded (low WinRate)")
        else:
            print(f"   ❌ WARNING: XRPUSDT should be excluded!")
    
    # Статистика по всем Tier-ам
    print(f"\n{'='*80}")
    print(f"📊 TIER STATISTICS")
    print(f"{'='*80}")
    
    stats = scaler.get_tier_stats()
    print(json.dumps(stats, indent=2))
    
    # Проверка исключённых пар
    print(f"\n{'='*80}")
    print(f"🚫 EXCLUDED PAIRS")
    print(f"{'='*80}")
    
    for pair in ['XRPUSDT', 'BTCUSDT']:
        is_allowed = scaler.is_pair_allowed(pair)
        status = "❌ BLOCKED" if not is_allowed else "✅ ALLOWED"
        print(f"   {pair}: {status}")
    
    print(f"\n{'='*80}")
    print(f"✅ TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    test_strategy_scaler()
