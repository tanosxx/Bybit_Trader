"""
Тестовый скрипт для проверки ML Predictor
Запускать на сервере в Docker:
docker exec bybit_bot python scripts/test_ml_predictor.py
"""
import asyncio
import sys
sys.path.append('/app')

from core.ml_predictor import get_ml_predictor
from core.bybit_api import get_bybit_api


async def test_ml_predictor():
    """Тест ML предсказателя"""
    print("\n" + "="*60)
    print("🤖 Testing ML Predictor")
    print("="*60)
    
    # Инициализация
    predictor = get_ml_predictor()
    api = get_bybit_api()
    
    # Загрузка модели
    print("\n1. Loading ML model...")
    success = await predictor.load_model()
    
    if not success:
        print("❌ Failed to load model")
        return
    
    print("✅ Model loaded successfully")
    
    # Тест предсказания для BTC
    print("\n2. Testing prediction for BTCUSDT...")
    
    # Получаем текущую цену
    ticker = await api.get_ticker("BTCUSDT")
    if not ticker:
        print("❌ Failed to get ticker")
        return
    
    current_price = ticker['last_price']
    print(f"   Current price: ${current_price:,.2f}")
    
    # Получаем исторические свечи
    klines = await api.get_klines("BTCUSDT", "60", limit=200)
    if not klines:
        print("❌ Failed to get klines")
        return
    
    print(f"   Loaded {len(klines)} candles")
    
    # Делаем предсказание
    prediction = await predictor.predict("BTCUSDT", current_price, klines)
    
    print("\n" + "="*60)
    print("📊 ML Prediction Results")
    print("="*60)
    print(f"Symbol:           BTCUSDT")
    print(f"Current Price:    ${current_price:,.2f}")
    print(f"Predicted Price:  ${prediction['predicted_price']:,.2f}")
    print(f"Direction:        {prediction['direction']}")
    print(f"Confidence:       {prediction['confidence']:.2%}")
    print(f"Change:           {prediction['change_pct']:+.2f}%")
    print("="*60)
    
    # Тест для ETH
    print("\n3. Testing prediction for ETHUSDT...")
    
    ticker_eth = await api.get_ticker("ETHUSDT")
    if ticker_eth:
        current_price_eth = ticker_eth['last_price']
        klines_eth = await api.get_klines("ETHUSDT", "60", limit=200)
        
        if klines_eth:
            prediction_eth = await predictor.predict("ETHUSDT", current_price_eth, klines_eth)
            
            print("\n" + "="*60)
            print("📊 ETH Prediction")
            print("="*60)
            print(f"Current:    ${current_price_eth:,.2f}")
            print(f"Predicted:  ${prediction_eth['predicted_price']:,.2f}")
            print(f"Direction:  {prediction_eth['direction']}")
            print(f"Confidence: {prediction_eth['confidence']:.2%}")
            print(f"Change:     {prediction_eth['change_pct']:+.2f}%")
            print("="*60)
    
    print("\n✅ ML Predictor test completed!")


if __name__ == "__main__":
    asyncio.run(test_ml_predictor())
