import requests
import json

response = requests.get('http://localhost:8585/api/data')
data = response.json()

ml = data['ml_status']
fb = data['futures_balance']
positions = data['futures_positions']

print(f"\n🧠 ML STATUS:")
print(f"  Samples: {ml['learned_samples']}")
print(f"  Ready: {ml['ready']}")
print(f"  Win Rate: {ml['win_rate']:.1f}%")
print(f"  Model Accuracy: {ml['model_accuracy']:.1f}%")

print(f"\n📊 POSITIONS:")
print(f"  In DB: {fb['open_positions']}")
print(f"  On Exchange: {len(positions)}")

print(f"\n💰 BALANCE:")
print(f"  Current: ${fb['current_balance']:.2f}")
print(f"  ROI: {fb['pnl_pct']:.2f}%")
