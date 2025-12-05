"""Проверка Gemini API ключей через REST API"""
import requests
import os

# Ключи из .env
keys = [
    os.getenv("GOOGLE_API_KEY_1", "AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM"),
    os.getenv("GOOGLE_API_KEY_2", "AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c"),
    os.getenv("GOOGLE_API_KEY_3", "AIzaSyD18h8QwDeSl8U5pFMM1HtoB3VaUksXy-g"),
]

print("=" * 80)
print("🔑 TESTING GEMINI API KEYS")
print("=" * 80)

working_keys = []

for i, key in enumerate(keys, 1):
    print(f"\n🔍 Testing Key #{i}: {key[:20]}...")
    print("-" * 80)
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={key}"
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": "Say 'OK' if you work"}]
        }],
        "generationConfig": {
            "maxOutputTokens": 10,
            "temperature": 0.1
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"✅ SUCCESS!")
                print(f"   Response: {text.strip()}")
                working_keys.append((i, key))
            else:
                print(f"⚠️  Unexpected response format")
        elif response.status_code == 429:
            print(f"❌ QUOTA EXCEEDED")
        elif response.status_code == 400:
            error = response.json()
            print(f"❌ INVALID KEY or BAD REQUEST")
            print(f"   Error: {error.get('error', {}).get('message', 'Unknown')[:100]}")
        else:
            print(f"❌ ERROR (Status: {response.status_code})")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

print("\n" + "=" * 80)
print(f"✅ SUMMARY: {len(working_keys)}/{len(keys)} keys working")
print("=" * 80)

if working_keys:
    print("\n🎯 Working Keys:")
    for idx, key in working_keys:
        print(f"   GOOGLE_API_KEY_{idx}: {key[:20]}...{key[-10:]}")
else:
    print("\n⚠️  No working keys found!")
