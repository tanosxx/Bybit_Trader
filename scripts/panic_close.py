#!/usr/bin/env python3
"""
🚨 PANIC CLOSE - Экстренное закрытие ВСЕХ фьючерсных позиций

Запуск на сервере:
  docker exec bybit_bot python scripts/panic_close.py

⚠️ ВНИМАНИЕ: Скрипт закроет ВСЕ открытые фьючерсные позиции!
"""
import sys
import os
import asyncio
import hmac
import hashlib
import time
import json
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
END = '\033[0m'


class PanicAPI:
    def __init__(self):
        self.api_key = settings.bybit_api_key
        self.api_secret = settings.bybit_api_secret
        self.base_url = "https://api-demo.bybit.com"
        self.recv_window = "5000"
    
    def _sign(self, timestamp: str, params: str = "") -> str:
        sign_string = f"{timestamp}{self.api_key}{self.recv_window}{params}"
        return hmac.new(
            bytes(self.api_secret, 'utf-8'),
            bytes(sign_string, 'utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _get(self, endpoint: str, params: dict):
        timestamp = str(int(time.time() * 1000))
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        sig = self._sign(timestamp, query)
        url = f"{self.base_url}{endpoint}?{query}"
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers) as r:
                return await r.json()
    
    async def _post(self, endpoint: str, data: dict):
        timestamp = str(int(time.time() * 1000))
        body = json.dumps(data)
        sig = self._sign(timestamp, body)
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=body) as r:
                return await r.json()
    
    async def get_positions(self):
        resp = await self._get("/v5/position/list", {"category": "linear", "settleCoin": "USDT"})
        if resp.get('retCode') == 0:
            return [p for p in resp['result']['list'] if float(p['size']) > 0]
        return []
    
    async def close_position(self, symbol: str, side: str, size: float):
        close_side = "Sell" if side == "Buy" else "Buy"
        data = {
            "category": "linear",
            "symbol": symbol,
            "side": close_side,
            "orderType": "Market",
            "qty": str(size),
            "reduceOnly": True,
            "positionIdx": 0
        }
        return await self._post("/v5/order/create", data)


async def main():
    print(f"\n{RED}{BOLD}🚨 PANIC CLOSE - EMERGENCY POSITION CLOSURE{END}")
    print(f"{YELLOW}Closing ALL futures positions...{END}\n")
    
    api = PanicAPI()
    positions = await api.get_positions()
    
    if not positions:
        print(f"{GREEN}✅ No open positions found.{END}")
        return
    
    print(f"Found {len(positions)} position(s) to close:\n")
    
    total_pnl = 0
    for pos in positions:
        symbol = pos['symbol']
        side = pos['side']
        size = float(pos['size'])
        pnl = float(pos['unrealisedPnl']) if pos['unrealisedPnl'] else 0
        entry = float(pos['avgPrice']) if pos['avgPrice'] else 0
        
        print(f"Closing {symbol} {side} {size}...", end=" ")
        
        result = await api.close_position(symbol, side, size)
        
        if result.get('retCode') == 0:
            print(f"{GREEN}✅ Closed | PnL: ${pnl:+.2f}{END}")
            total_pnl += pnl
        else:
            print(f"{RED}❌ Error: {result.get('retMsg')}{END}")
    
    print(f"\n{BOLD}Total Realized PnL: ${total_pnl:+.2f}{END}")
    print(f"{GREEN}✅ Panic close completed.{END}\n")


if __name__ == "__main__":
    asyncio.run(main())
