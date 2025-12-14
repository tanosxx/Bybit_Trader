"""
Тест подписи Bybit API по официальной документации
"""
import hmac
import hashlib
import time

# Данные
api_key = "LmHhFgiAD8Qj27dt1P"
api_secret = "j3GavMoVXrUxL1uCwhqU7sDlRZyqDc4yKkQQ"
recv_window = "5000"

# Timestamp
timestamp = str(int(time.time() * 1000))

# Параметры
params = "accountType=UNIFIED"

# Формируем строку для подписи (по документации V5)
sign_string = f"{timestamp}{api_key}{recv_window}{params}"

print("🔍 Тест подписи Bybit V5 API (Demo Trading)")
print("="*80)
print(f"API Key: {api_key}")
print(f"API Secret: {api_secret}")
print(f"Timestamp: {timestamp}")
print(f"Recv Window: {recv_window}")
print(f"Params: {params}")
print(f"\nSign String: {sign_string}")

# Генерируем подпись
signature = hmac.new(
    bytes(api_secret, 'utf-8'),
    bytes(sign_string, 'utf-8'),
    hashlib.sha256
).hexdigest()

print(f"Signature: {signature}")
print("="*80)

# Тестируем запрос
import requests

# ВАЖНО: Demo Trading использует БОЕВОЙ URL!
url = "https://api.bybit.com/v5/account/wallet-balance"
headers = {
    "X-BAPI-API-KEY": api_key,
    "X-BAPI-SIGN": signature,
    "X-BAPI-TIMESTAMP": timestamp,
    "X-BAPI-RECV-WINDOW": recv_window,
}

print(f"\n📡 Отправляем запрос...")
print(f"URL: {url}?{params}")
print(f"Headers: {headers}")

response = requests.get(url, headers=headers, params={"accountType": "UNIFIED"})

print(f"\n📥 Ответ:")
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
