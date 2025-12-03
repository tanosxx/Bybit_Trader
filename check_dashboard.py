import requests
import json

response = requests.get('http://localhost:8585/api/data')
data = response.json()

fb = data['futures_balance']
print(f"\n💰 FUTURES BALANCE:")
print(f"  Current: ${fb['current_balance']:.2f}")
print(f"  Initial: ${fb['initial_balance']:.2f}")
print(f"  Realized PnL: ${fb['realized_pnl']:.2f}")
print(f"  Fees: ${fb['total_fees']:.2f}")
print(f"  Net PnL: ${fb['net_pnl']:.2f}")
print(f"  ROI: {fb['pnl_pct']:.2f}%")

print(f"\n📊 POSITIONS:")
print(f"  Open: {fb['open_positions']}")
print(f"  On Exchange: {len(data['futures_positions'])}")

for pos in data['futures_positions']:
    print(f"\n  {pos['side']} {pos['symbol']}:")
    print(f"    Size: {pos['size']}")
    print(f"    Entry: ${pos['entry_price']:.2f}")
    print(f"    Mark: ${pos['mark_price']:.2f}")
    print(f"    PnL: ${pos['unrealized_pnl']:.2f} ({pos['pnl_pct']:.2f}%)")
