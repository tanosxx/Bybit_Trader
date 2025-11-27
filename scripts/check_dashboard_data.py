"""Проверка данных дашборда"""
import requests
import json

response = requests.get('http://localhost:8585/api/data')
data = response.json()

print("=== БАЛАНСЫ ===")
for b in data['balance']['balances']:
    print(f"{b['coin']}: Current={b['total']:.8f}, Initial={b['initial']:.8f}, Change={b['change']:+.8f} ({b['change_pct']:+.2f}%)")

print(f"\nTotal USDT: ${data['balance']['total_usdt']:.2f}")
print(f"\nОткрытых позиций: {len(data['open_trades'])}")
print(f"Закрытых сделок: {len(data['closed_trades'])}")
print(f"Записей истории баланса: {len(data['balance_history'])}")
print(f"Логов: {len(data['logs'])}")
