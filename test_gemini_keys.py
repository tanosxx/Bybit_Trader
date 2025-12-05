"""Проверка Gemini API ключей"""
import os
import google.generativeai as genai

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
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(
            "Say 'OK' if you work",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.1,
            )
        )
        
        if response and response.text:
            print(f"✅ SUCCESS!")
            print(f"   Response: {response.text.strip()}")
            working_keys.append((i, key))
        else:
            print(f"⚠️  Empty response")
            
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower():
            print(f"❌ QUOTA EXCEEDED")
        elif "invalid" in error_msg.lower() or "api_key" in error_msg.lower():
            print(f"❌ INVALID KEY")
        else:
            print(f"❌ ERROR: {error_msg[:100]}")

print("\n" + "=" * 80)
print(f"✅ SUMMARY: {len(working_keys)}/{len(keys)} keys working")
print("=" * 80)

if working_keys:
    print("\n🎯 Working Keys:")
    for idx, key in working_keys:
        print(f"   Key #{idx}: {key[:20]}...{key[-10:]}")
else:
    print("\n⚠️  No working keys found!")
