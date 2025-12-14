import requests
import json

response = requests.get('http://localhost:8585/api/data')
data = response.json()

print("API Response Keys:", list(data.keys()))
print("\nBalance keys:", list(data['balance'].keys()) if 'balance' in data else "N/A")
print("Balances count:", len(data['balance']['balances']) if 'balance' in data and 'balances' in data['balance'] else 0)
print("\nFirst balance:", data['balance']['balances'][0] if data['balance']['balances'] else "N/A")
print("\nStats:", data.get('stats', 'N/A'))
print("\nClosed trades count:", len(data.get('closed_trades', [])))
