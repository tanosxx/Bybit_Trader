"""
Проверка доступных моделей Gemini API
"""
import requests

# Рабочие ключи
keys = [
    ("Key #2", "AIzaSyDDsvjPVcTzJoGgz7XWmhB7ZEVMCrg6P0c"),
    ("Key #3", "AIzaSyD18h8QwDeSl8U5pFMM1HtoB3VaUksXy-g"),
]

print("=" * 80)
print("🔍 GEMINI API - Доступные модели")
print("=" * 80)

for key_name, key in keys:
    print(f"\n📋 Проверка {key_name}...")
    
    url = f"https://generativelanguage.googleapis.com/v1/models?key={key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            print(f"✅ Найдено моделей: {len(models)}")
            print("\n📊 Доступные модели:")
            
            for model in models:
                name = model.get('name', 'Unknown')
                display_name = model.get('displayName', 'Unknown')
                description = model.get('description', '')
                
                # Показываем только модели для generateContent
                supported_methods = model.get('supportedGenerationMethods', [])
                if 'generateContent' in supported_methods:
                    print(f"\n   🤖 {display_name}")
                    print(f"      ID: {name}")
                    if description:
                        print(f"      Описание: {description[:100]}...")
            
            break  # Если ключ работает, не проверяем остальные
            
        elif response.status_code == 403:
            print(f"❌ Ключ невалидный (403)")
        elif response.status_code == 429:
            print(f"⚠️  Квота исчерпана (429)")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"   {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
