"""Проверка доступных моделей Gemini"""
import requests

key = "AIzaSyCalj1ugvpU1thqDtROGCEgIGdXDFBIOJM"
url = f"https://generativelanguage.googleapis.com/v1/models?key={key}"

print("=" * 80)
print("🔍 CHECKING GEMINI MODELS")
print("=" * 80)

try:
    response = requests.get(url, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        if 'models' in data:
            models = data['models']
            print(f"\n✅ Found {len(models)} models:\n")
            
            for model in models:
                name = model.get('name', 'unknown')
                display_name = model.get('displayName', '')
                supported_methods = model.get('supportedGenerationMethods', [])
                
                print(f"📦 {name}")
                if display_name:
                    print(f"   Display: {display_name}")
                if supported_methods:
                    print(f"   Methods: {', '.join(supported_methods)}")
                print()
        else:
            print("No models found")
            print(response.text[:500])
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"❌ Exception: {e}")
