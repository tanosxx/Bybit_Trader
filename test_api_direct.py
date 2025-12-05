"""Прямой тест OhMyGPT API"""
import requests

url = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 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"
}
data = {
    "model": "claude-3-5-sonnet-20240620",
    "messages": [{"role": "user", "content": "Say hello in one word"}],
    "max_tokens": 10
}

print("Testing OhMyGPT API...")
print(f"URL: {url}")
print(f"Model: {data['model']}")

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
