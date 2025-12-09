#!/usr/bin/env python3
"""
Тест Gemini API - проверка всех ключей и моделей
"""

import os
import sys
import requests
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from config import settings


def test_gemini_model(key, model, key_name):
    """Тестирует одну комбинацию ключ+модель"""
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": "Say 'OK' if you work"}]}],
        "generationConfig": {
            "maxOutputTokens": 10,
            "temperature": 0.1
        }
    }
    
    try:
        print(f"\n🔑 Testing {key_name} + {model}...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text = candidate['content']['parts'][0].get('text', '')
                    print(f"   ✅ SUCCESS: {text[:50]}")
                    return True
        elif response.status_code == 429:
            print(f"   ⚠️  QUOTA EXCEEDED")
            return False
        elif response.status_code == 404:
            error_data = response.json()
            print(f"   ❌ MODEL NOT FOUND: {error_data.get('error', {}).get('message', 'Unknown')}")
            return False
        else:
            print(f"   ❌ HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"      Error: {error_data.get('error', {}).get('message', 'Unknown')}")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def test_ohmygpt():
    """Тестирует OhMyGPT API"""
    api_key = os.getenv("OHMYGPT_KEY")
    if not api_key:
        print("\n⚠️  OHMYGPT_KEY not found in environment")
        return False
    
    url = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "messages": [
            {"role": "user", "content": "Say 'OK' if you work"}
        ],
        "max_tokens": 10
    }
    
    try:
        print(f"\n🔑 Testing OhMyGPT (Claude 3.5 Sonnet)...")
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                print(f"   ✅ SUCCESS: {text[:50]}")
                return True
        elif response.status_code == 429:
            print(f"   ⚠️  QUOTA EXCEEDED")
            return False
        elif response.status_code == 401:
            print(f"   ❌ UNAUTHORIZED: Invalid API key")
            return False
        elif response.status_code == 503:
            print(f"   ❌ SERVICE UNAVAILABLE")
            return False
        else:
            print(f"   ❌ HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"      Error: {error_data}")
            except:
                print(f"      Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def main():
    """Главная функция"""
    print("=" * 70)
    print("GEMINI & OHMYGPT API TEST")
    print("=" * 70)
    
    # Gemini ключи
    gemini_keys = [
        (os.getenv("GOOGLE_API_KEY_2"), "Key #1 (GOOGLE_API_KEY_2)"),
        (os.getenv("GOOGLE_API_KEY_3"), "Key #2 (GOOGLE_API_KEY_3)"),
    ]
    
    # Gemini модели
    gemini_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-exp",  # Попробуем и эту
        "gemini-1.5-flash",      # И эту для сравнения
    ]
    
    print("\n" + "=" * 70)
    print("TESTING GEMINI API")
    print("=" * 70)
    
    results = {}
    
    for key, key_name in gemini_keys:
        if not key:
            print(f"\n⚠️  {key_name} not found in environment")
            continue
        
        for model in gemini_models:
            combo = f"{key_name} + {model}"
            results[combo] = test_gemini_model(key, model, key_name)
    
    # Тестируем OhMyGPT
    print("\n" + "=" * 70)
    print("TESTING OHMYGPT API")
    print("=" * 70)
    
    ohmygpt_result = test_ohmygpt()
    
    # Итоги
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\nGemini API:")
    for combo, result in results.items():
        status = "✅ WORKING" if result else "❌ FAILED"
        print(f"   {status}: {combo}")
    
    print("\nOhMyGPT API:")
    status = "✅ WORKING" if ohmygpt_result else "❌ FAILED"
    print(f"   {status}: Claude 3.5 Sonnet")
    
    # Рекомендации
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    
    working_combos = [k for k, v in results.items() if v]
    if working_combos:
        print(f"\n✅ Found {len(working_combos)} working Gemini combinations:")
        for combo in working_combos:
            print(f"   • {combo}")
    else:
        print("\n⚠️  No working Gemini combinations found")
        print("   → All quotas exhausted, wait for reset (00:00 UTC)")
    
    if ohmygpt_result:
        print("\n✅ OhMyGPT is working!")
        print("   → Can use as alternative for Strategic Brain")
    else:
        print("\n❌ OhMyGPT is not working")
        print("   → Stick with Gemini API")


if __name__ == "__main__":
    main()
