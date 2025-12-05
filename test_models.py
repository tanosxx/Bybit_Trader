"""Проверка доступных моделей OhMyGPT API"""
import requests

url = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/models"
headers = {
    "Authorization": "Bearer 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"
}

print("=" * 80)
print("🔍 CHECKING AVAILABLE MODELS")
print("=" * 80)
print(f"\nURL: {url}\n")

try:
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        if 'data' in data:
            models = data['data']
            print(f"✅ Found {len(models)} models:\n")
            
            # Фильтруем Claude модели
            claude_models = [m for m in models if 'claude' in m.get('id', '').lower()]
            
            if claude_models:
                print("🤖 CLAUDE MODELS:")
                print("-" * 80)
                for model in claude_models:
                    model_id = model.get('id', 'unknown')
                    owned_by = model.get('owned_by', 'unknown')
                    print(f"  • {model_id}")
                    print(f"    Owner: {owned_by}")
                    if 'created' in model:
                        print(f"    Created: {model['created']}")
                    print()
            
            # Показываем все модели
            print("\n📋 ALL MODELS:")
            print("-" * 80)
            for i, model in enumerate(models, 1):
                model_id = model.get('id', 'unknown')
                print(f"{i}. {model_id}")
        else:
            print("Response:", response.text[:500])
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
print("✅ CHECK COMPLETE")
print("=" * 80)
