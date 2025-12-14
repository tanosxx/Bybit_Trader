"""
Тест CryptoPanic API
"""
import asyncio
import aiohttp

API_KEY = "3e44ec47b8bdffdf84526285e2eb948c2537bdd4"
BASE_URL = "https://cryptopanic.com/api/v1/posts/"

async def test_api():
    print(f"🔍 Testing CryptoPanic API...")
    print(f"   Key: {API_KEY[:10]}...")
    
    params = {
        'auth_token': API_KEY,
        'public': 'true',
        'kind': 'news'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    print(f"   ✅ Got {len(results)} news items!")
                    
                    # Показываем первые 3 новости
                    for i, item in enumerate(results[:3]):
                        title = item.get('title', 'No title')[:60]
                        print(f"   {i+1}. {title}...")
                else:
                    text = await response.text()
                    print(f"   ❌ Error: {text[:200]}")
    
    except asyncio.TimeoutError:
        print(f"   ❌ Timeout!")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
