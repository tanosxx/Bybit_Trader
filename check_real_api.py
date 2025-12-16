"""
Проверка подключения к РЕАЛЬНОМУ аккаунту Bybit (Mainnet)

Этот скрипт проверяет:
1. Валидность API ключей
2. Доступ к серверу Bybit
3. Текущий баланс USDT

⚠️ ВАЖНО: Скрипт только ЧИТАЕТ данные, не открывает сделки!
"""
import httpx
import hmac
import hashlib
import time
import sys
import json


def generate_signature(api_secret: str, params: str) -> str:
    """Генерация подписи для Bybit API"""
    return hmac.new(
        api_secret.encode('utf-8'),
        params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def check_real_api():
    """Проверить подключение к реальному аккаунту Bybit"""
    
    # API Credentials (MAINNET)
    API_KEY = "lq2uoJ8GlfoEI1Kdgd"
    API_SECRET = "hnW8T1Q3eT5DniNmBupmCuOVdm7FCv40byzM"
    BASE_URL = "https://api.bybit.com"  # MAINNET
    
    print("="*80)
    print("🔍 BYBIT REAL API CONNECTION TEST")
    print("="*80)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"Environment: MAINNET (Real Trading)")
    print(f"Base URL: {BASE_URL}")
    print("="*80)
    print()
    
    try:
        # Тест 1: Проверка серверного времени (публичный endpoint)
        print("⏰ Testing server connection...")
        try:
            with httpx.Client() as client:
                response = client.get(f"{BASE_URL}/v5/market/time")
                server_time = response.json()
                
                if server_time.get('retCode') == 0:
                    print(f"   ✅ Server Time: {server_time['result']['timeSecond']}")
                else:
                    print(f"   ❌ Server Time Error: {server_time}")
                    return False
        except Exception as e:
            print(f"   ❌ Server Connection Failed: {e}")
            return False
        
        print()
        
        # Тест 2: Проверка баланса кошелька (приватный endpoint)
        print("💰 Fetching wallet balance...")
        try:
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            
            # Параметры запроса
            params = f"accountType=UNIFIED&coin=USDT"
            
            # Строка для подписи
            param_str = f"{timestamp}{API_KEY}{recv_window}{params}"
            signature = generate_signature(API_SECRET, param_str)
            
            # Заголовки
            headers = {
                "X-BAPI-API-KEY": API_KEY,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "Content-Type": "application/json"
            }
            
            # Запрос
            with httpx.Client() as client:
                response = client.get(
                    f"{BASE_URL}/v5/account/wallet-balance?{params}",
                    headers=headers,
                    timeout=10.0
                )
                balance_response = response.json()
            
            if balance_response.get('retCode') == 0:
                print("   ✅ Wallet Access: SUCCESS")
                print()
                
                # Парсим баланс
                result = balance_response['result']
                if 'list' in result and len(result['list']) > 0:
                    account = result['list'][0]
                    
                    # Ищем USDT в монетах
                    usdt_balance = None
                    if 'coin' in account:
                        for coin_data in account['coin']:
                            if coin_data['coin'] == 'USDT':
                                usdt_balance = coin_data
                                break
                    
                    if usdt_balance:
                        # Безопасное преобразование с обработкой пустых строк
                        total_balance = float(usdt_balance.get('walletBalance') or 0)
                        available_balance = float(usdt_balance.get('availableToWithdraw') or 0)
                        equity = float(usdt_balance.get('equity') or 0)
                        
                        print("="*80)
                        print("💵 USDT BALANCE (UNIFIED ACCOUNT)")
                        print("="*80)
                        print(f"   Total Balance:     ${total_balance:.2f}")
                        print(f"   Available:         ${available_balance:.2f}")
                        print(f"   Equity:            ${equity:.2f}")
                        print("="*80)
                        print()
                        
                        if total_balance == 0:
                            print("ℹ️  Balance is $0.00 - This is normal for a new account.")
                            print("   You can now deposit USDT to start trading.")
                        else:
                            print(f"✅ Account has ${total_balance:.2f} USDT")
                            print("   Ready for trading!")
                    else:
                        print("⚠️  USDT not found in wallet")
                        print("   Account may need USDT deposit")
                else:
                    print("⚠️  No account data found")
                    print("   Response:", balance_response)
                
            elif balance_response['retCode'] == 10003:
                print("   ❌ Invalid API Key")
                print("   Please check your API credentials")
                return False
            elif balance_response['retCode'] == 10004:
                print("   ❌ Invalid API Signature")
                print("   Please check your API Secret")
                return False
            elif balance_response['retCode'] == 33004:
                print("   ❌ API Key Permissions Error")
                print("   Please enable 'Read-Write' or at least 'Read' permissions")
                print("   Go to: Bybit > API Management > Edit API > Enable Permissions")
                return False
            elif balance_response['retCode'] == 10005:
                print("   ❌ IP Address Not Whitelisted")
                print("   Please add your IP to API whitelist or disable IP restriction")
                return False
            else:
                print(f"   ❌ API Error: {balance_response['retMsg']} (Code: {balance_response['retCode']})")
                return False
                
        except Exception as e:
            print(f"   ❌ Wallet Balance Error: {e}")
            
            # Проверка на частые ошибки
            error_str = str(e).lower()
            if 'invalid api' in error_str or 'authentication' in error_str:
                print("\n   💡 Possible causes:")
                print("      1. API Key or Secret is incorrect")
                print("      2. API Key doesn't have required permissions")
                print("      3. IP address is not whitelisted")
            
            return False
        
        print()
        print("="*80)
        print("✅ CONNECTION TEST SUCCESSFUL!")
        print("="*80)
        print("Your API keys are valid and working.")
        print("You can now use these keys for real trading.")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("="*80)
        print("❌ CONNECTION TEST FAILED!")
        print("="*80)
        print(f"Error: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check API Key and Secret are correct")
        print("   2. Verify API permissions (need at least 'Read' access)")
        print("   3. Check IP whitelist settings")
        print("   4. Ensure API is enabled for Unified Trading Account")
        print()
        return False


if __name__ == "__main__":
    print()
    success = check_real_api()
    print()
    
    if success:
        print("🎉 Ready to proceed with real trading!")
        sys.exit(0)
    else:
        print("⚠️  Please fix the issues above before proceeding.")
        sys.exit(1)
