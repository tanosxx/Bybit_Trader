"""Тест разных моделей Claude через chat/completions"""
import requests

base_url = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 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"
}

# Возможные модели Claude
models_to_test = [
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
    "claude-2.1",
    "claude-2",
]

print("=" * 80)
print("🧪 TESTING CLAUDE MODELS")
print("=" * 80)

for model in models_to_test:
    print(f"\n🔍 Testing: {model}")
    print("-" * 80)
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "Say 'OK' if you work"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"✅ SUCCESS!")
                print(f"   Response: {content}")
                print(f"   Model: {result.get('model', 'unknown')}")
            else:
                print(f"⚠️  Unexpected response format")
                print(f"   {response.text[:200]}")
        else:
            print(f"❌ FAILED (Status: {response.status_code})")
            error_msg = response.text[:200]
            print(f"   Error: {error_msg}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)
