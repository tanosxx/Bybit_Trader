import sys
import asyncio
sys.path.insert(0, "/app")

from core.ml_predictor import get_ml_predictor

async def test():
    ml = get_ml_predictor()
    loaded = await ml.load_model()
    
    print(f"Load result: {loaded}")
    print(f"Model: {ml.model is not None}")
    print(f"Scaler X: {ml.scaler_X is not None}")
    print(f"Scaler Y: {ml.scaler_y is not None}")
    print(f"Is loaded: {ml.is_loaded}")

asyncio.run(test())
