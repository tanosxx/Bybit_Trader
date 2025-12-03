import requests
import json

response = requests.get('http://localhost:8585/api/data')
data = response.json()

print(f"\n📊 API DATA:")
print(f"  Positions: {len(data.get('futures_positions', []))}")
print(f"  Trades: {len(data.get('futures_trades', []))}")
print(f"  Balance history: {len(data.get('balance_history', []))}")
print(f"  Has ml_status: {'ml_status' in data}")
print(f"  Has futures_balance: {'futures_balance' in data}")

if len(data.get('futures_positions', [])) > 0:
    print(f"\n  First position: {data['futures_positions'][0]}")

if len(data.get('futures_trades', [])) > 0:
    print(f"\n  First trade: {data['futures_trades'][0]}")
