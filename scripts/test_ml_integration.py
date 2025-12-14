"""
Тестовый скрипт для проверки интеграции ML с Real Trader
Запускать на сервере: docker exec bybit_bot python scripts/test_ml_integration.py
"""
import asyncio
import sys
sys.path.append('/app')

from core.real_trader import RealTrader


async def test_ml_integration():
    """Тест интеграции ML с трейдером"""
    print("\n" + "="*60)
    print("🤖 Testing ML Integration with Real Trader")
    print("="*60)
    
    # Создаём трейдера
    trader = RealTrader()
    
    # Инициализация ML
    print("\n1. Initializing ML model...")
    await trader.initialize_ml()
    
    if not trader.ml_enabled:
        print("❌ ML not available, testing AI only")
    else:
        print("✅ ML enabled")
    
    # Тест анализа для BTC
    print("\n2. Testing combined analysis for BTCUSDT...")
    
    try:
        # Получаем текущую цену
        ticker = await trader.bybit_api.get_ticker("BTCUSDT")
        if not ticker:
            print("❌ Failed to get ticker")
            return
        
        current_price = ticker['last_price']
        print(f"   Current BTC price: ${current_price:,.2f}")
        
        # Комбинированный анализ
        result = await trader.analyze_with_ml_and_ai("BTCUSDT", current_price)
        
        print("\n" + "="*60)
        print("📊 Combined Analysis Results")
        print("="*60)
        
        # ML результаты
        if result['ml_prediction']:
            ml = result['ml_prediction']
            print(f"🤖 ML Prediction:")
            print(f"   Predicted Price: ${ml['predicted_price']:,.2f}")
            print(f"   Direction: {ml['direction']}")
            print(f"   Confidence: {ml['confidence']:.2%}")
            print(f"   Change: {ml['change_pct']:+.2f}%")
        else:
            print(f"🤖 ML Prediction: Not available")
        
        print()
        
        # AI результаты
        if result['ai_analysis']:
            ai = result['ai_analysis']
            print(f"🧠 AI Analysis:")
            print(f"   Decision: {ai.get('decision', 'UNKNOWN')}")
            print(f"   Confidence: {ai.get('confidence', 0):.2%}")
        else:
            print(f"🧠 AI Analysis: Not available")
        
        print()
        
        # Финальное решение
        print(f"🎯 Final Decision:")
        print(f"   Action: {result['final_decision']}")
        print(f"   Confidence: {result['final_confidence']:.2%}")
        
        # Проверяем логику принятия решений
        if result['final_confidence'] > 0.7:
            print(f"   ✅ High confidence - would execute trade")
        elif result['final_confidence'] > 0.5:
            print(f"   ⚠️  Medium confidence - might execute")
        else:
            print(f"   ❌ Low confidence - would skip")
        
        print("="*60)
        
        # Тест для ETH
        print("\n3. Testing combined analysis for ETHUSDT...")
        
        ticker_eth = await trader.bybit_api.get_ticker("ETHUSDT")
        if ticker_eth:
            eth_price = ticker_eth['last_price']
            print(f"   Current ETH price: ${eth_price:,.2f}")
            
            result_eth = await trader.analyze_with_ml_and_ai("ETHUSDT", eth_price)
            
            print(f"\n   ML: {result_eth['ml_prediction']['direction'] if result_eth['ml_prediction'] else 'N/A'}")
            print(f"   AI: {result_eth['ai_analysis'].get('decision', 'N/A') if result_eth['ai_analysis'] else 'N/A'}")
            print(f"   Final: {result_eth['final_decision']} ({result_eth['final_confidence']:.2%})")
        
        print("\n" + "="*60)
        print("✅ ML Integration test completed!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ml_integration())
