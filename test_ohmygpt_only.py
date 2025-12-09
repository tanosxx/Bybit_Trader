#!/usr/bin/env python3
"""
Тест OhMyGPT API - проверка работоспособности Claude 3.5 Sonnet
"""

import requests
import json

# Данные из .env
OHMYGPT_KEY = "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"
STRATEGIC_DRIVER_URL = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg"  # Базовый endpoint (без /v1)
STRATEGIC_MODEL = "claude-3-5-sonnet-20240620"


def test_ohmygpt_simple():
    """Простой тест - просто проверяем работает ли API"""
    print("=" * 70)
    print("TEST 1: Simple API Check")
    print("=" * 70)
    
    url = f"{STRATEGIC_DRIVER_URL}/v1/chat/completions"  # Добавляем /v1/chat/completions
    headers = {
        "Authorization": f"Bearer {OHMYGPT_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": STRATEGIC_MODEL,
        "messages": [
            {"role": "user", "content": "Say 'OK' if you work"}
        ],
        "max_tokens": 10
    }
    
    try:
        print(f"\n🔑 Testing OhMyGPT...")
        print(f"   URL: {url}")
        print(f"   Model: {STRATEGIC_MODEL}")
        print(f"   Key: {OHMYGPT_KEY[:20]}...")
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS!")
            print(f"\n   Full Response:")
            print(json.dumps(result, indent=2))
            
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                print(f"\n   💬 Claude says: {text}")
                return True
        else:
            print(f"   ❌ FAILED")
            print(f"\n   Response Text:")
            print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def test_ohmygpt_strategic():
    """Тест с реальным промптом для Strategic Brain"""
    print("\n" + "=" * 70)
    print("TEST 2: Strategic Brain Prompt")
    print("=" * 70)
    
    url = f"{STRATEGIC_DRIVER_URL}/v1/chat/completions"  # Добавляем /v1/chat/completions
    headers = {
        "Authorization": f"Bearer {OHMYGPT_KEY}",
        "Content-Type": "application/json"
    }
    
    # Упрощённый промпт для теста
    prompt = """Analyze the crypto market and respond with ONE word only:
- BULL_RUSH (strong uptrend, only LONG)
- BEAR_CRASH (strong downtrend, only SHORT)
- SIDEWAYS (ranging market, both allowed)
- UNCERTAIN (high volatility, no trading)

Recent BTC price: $96,500 (up 2% today)
Recent ETH price: $3,050 (up 1.5% today)

Your answer (one word only):"""
    
    data = {
        "model": STRATEGIC_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50,
        "temperature": 0.3
    }
    
    try:
        print(f"\n🔑 Testing Strategic Brain prompt...")
        
        response = requests.post(url, headers=headers, json=data, timeout=20)
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS!")
            
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                print(f"\n   💬 Claude's analysis: {text}")
                
                # Проверяем что ответ содержит один из режимов
                valid_regimes = ['BULL_RUSH', 'BEAR_CRASH', 'SIDEWAYS', 'UNCERTAIN']
                regime = None
                for r in valid_regimes:
                    if r in text.upper():
                        regime = r
                        break
                
                if regime:
                    print(f"\n   ✅ Valid regime detected: {regime}")
                    return True
                else:
                    print(f"\n   ⚠️  No valid regime in response")
                    return False
        else:
            print(f"   ❌ FAILED")
            print(f"\n   Response Text:")
            print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


def test_ohmygpt_balance():
    """Проверка баланса (если API поддерживает)"""
    print("\n" + "=" * 70)
    print("TEST 3: Balance Check (if supported)")
    print("=" * 70)
    
    # Попробуем разные endpoints для проверки баланса
    endpoints = [
        f"{STRATEGIC_DRIVER_URL}/balance",
        f"{STRATEGIC_DRIVER_URL}/v1/balance",
        "https://apic1.ohmycdn.com/api/v1/balance",
    ]
    
    headers = {
        "Authorization": f"Bearer {OHMYGPT_KEY}",
        "Content-Type": "application/json"
    }
    
    for endpoint in endpoints:
        try:
            print(f"\n🔍 Trying: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ Response:")
                print(json.dumps(response.json(), indent=2))
                return True
            else:
                print(f"   ❌ Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n   ℹ️  Balance endpoint not found (not critical)")
    return False


def main():
    """Главная функция"""
    print("\n" + "=" * 70)
    print("OHMYGPT API TEST - Claude 3.5 Sonnet")
    print("=" * 70)
    
    results = {}
    
    # Тест 1: Простая проверка
    results['simple'] = test_ohmygpt_simple()
    
    # Тест 2: Strategic Brain промпт
    if results['simple']:
        results['strategic'] = test_ohmygpt_strategic()
    else:
        results['strategic'] = False
        print("\n⚠️  Skipping strategic test (simple test failed)")
    
    # Тест 3: Баланс
    results['balance'] = test_ohmygpt_balance()
    
    # Итоги
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\nTest Results:")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {status}: {test_name}")
    
    # Рекомендация
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    if results['simple'] and results['strategic']:
        print("\n✅ OhMyGPT is WORKING!")
        print("   → Can be used as alternative for Strategic Brain")
        print("   → Add to .env on server to enable")
    elif results['simple']:
        print("\n⚠️  OhMyGPT works but strategic prompt needs adjustment")
        print("   → API is functional but response format may differ")
    else:
        print("\n❌ OhMyGPT is NOT WORKING")
        print("   → Check API key validity")
        print("   → Check if service is available")
        print("   → Stick with Gemini API")


if __name__ == "__main__":
    main()
