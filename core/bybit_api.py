"""
Bybit API v5 Integration
Docs: https://bybit-exchange.github.io/docs/v5/intro
"""
import hmac
import hashlib
import time
import asyncio
import aiohttp
from typing import Dict, List, Optional
from config import settings


class BybitAPI:
    """Bybit API v5 клиент"""
    
    def __init__(self):
        self.api_key = settings.bybit_api_key
        self.api_secret = settings.bybit_api_secret
        
        # Demo Trading использует ОТДЕЛЬНЫЙ URL!
        # api-demo.bybit.com - для Demo Trading
        # api.bybit.com - для реального аккаунта
        # api-testnet.bybit.com - для Testnet
        self.base_url = "https://api-demo.bybit.com"  # Demo Trading URL!
        
        self.recv_window = "5000"
    
    def _generate_signature(self, timestamp: str, params: str = "") -> str:
        """
        Генерация подписи для V5 API
        
        По документации V5:
        signature = HMAC_SHA256(api_secret, timestamp + api_key + recv_window + params)
        
        Где params:
        - Для GET: query string (например: "accountType=UNIFIED&symbol=BTCUSDT")
        - Для POST: JSON body string
        """
        # Формируем строку для подписи
        sign_string = f"{timestamp}{self.api_key}{self.recv_window}{params}"
        
        # Генерируем HMAC SHA256
        signature = hmac.new(
            bytes(self.api_secret, 'utf-8'),
            bytes(sign_string, 'utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Выполнить API запрос (V5 API)
        
        V5 API требует специальный формат подписи:
        - GET: timestamp + api_key + recv_window + queryString
        - POST: timestamp + api_key + recv_window + jsonBodyString
        """
        timestamp = str(int(time.time() * 1000))
        
        if params is None:
            params = {}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    # Для GET: сортируем параметры и создаем query string
                    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                    
                    # Генерируем подпись
                    signature = self._generate_signature(timestamp, query_string)
                    
                    headers = {
                        "X-BAPI-API-KEY": self.api_key,
                        "X-BAPI-SIGN": signature,
                        "X-BAPI-TIMESTAMP": timestamp,
                        "X-BAPI-RECV-WINDOW": self.recv_window,
                    }
                    
                    async with session.get(url, headers=headers, params=params) as response:
                        text = await response.text()
                        if response.status != 200:
                            print(f"❌ Bybit API error (status {response.status})")
                            print(f"   URL: {url}")
                            print(f"   Query: {query_string}")
                            print(f"   Response: {text}")
                        try:
                            result = await response.json()
                            return result
                        except:
                            return None
                
                elif method == "POST":
                    # Для POST: конвертируем params в JSON string
                    import json
                    json_body = json.dumps(params) if params else ""
                    
                    # Генерируем подпись
                    signature = self._generate_signature(timestamp, json_body)
                    
                    headers = {
                        "X-BAPI-API-KEY": self.api_key,
                        "X-BAPI-SIGN": signature,
                        "X-BAPI-TIMESTAMP": timestamp,
                        "X-BAPI-RECV-WINDOW": self.recv_window,
                        "Content-Type": "application/json"
                    }
                    
                    async with session.post(url, headers=headers, json=params) as response:
                        result = await response.json()
                        if response.status != 200:
                            print(f"❌ Bybit API error (status {response.status}): {result}")
                        return result
        
        except Exception as e:
            print(f"❌ Bybit API request error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> List[Dict]:
        """
        Получить свечи (klines)
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            interval: 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
            limit: количество свечей (max 1000)
        
        Returns:
            List of candles: [timestamp, open, high, low, close, volume]
        """
        endpoint = "/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        response = await self._request("GET", endpoint, params)
        
        if response.get("retCode") == 0:
            candles = response["result"]["list"]
            # Преобразуем в удобный формат
            return [
                {
                    "timestamp": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                }
                for c in candles
            ]
        else:
            print(f"❌ Error getting klines: {response}")
            return []
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Получить текущую цену и статистику
        
        Returns:
            {
                "symbol": "BTCUSDT",
                "lastPrice": "43250.50",
                "volume24h": "12345.67",
                "priceChange24h": "1.5"
            }
        """
        endpoint = "/v5/market/tickers"
        params = {
            "category": "spot",
            "symbol": symbol
        }
        
        response = await self._request("GET", endpoint, params)
        
        if response.get("retCode") == 0 and response["result"]["list"]:
            ticker = response["result"]["list"][0]
            return {
                "symbol": ticker["symbol"],
                "last_price": float(ticker["lastPrice"]),
                "volume_24h": float(ticker["volume24h"]),
                "price_change_24h": float(ticker["price24hPcnt"]) * 100
            }
        else:
            print(f"❌ Error getting ticker: {response}")
            return None
    
    async def get_wallet_balance(self) -> Optional[Dict]:
        """
        Получить баланс кошелька
        
        Returns:
            {
                "USDT": {"available": 50.0, "total": 50.0}
            }
        """
        endpoint = "/v5/account/wallet-balance"
        params = {
            "accountType": "UNIFIED"  # Unified Trading Account
        }
        
        response = await self._request("GET", endpoint, params)
        
        if response is None:
            print(f"❌ Bybit API вернул None")
            return None
        
        if response.get("retCode") == 0:
            coins = response["result"]["list"][0]["coin"]
            balances = {}
            
            for coin in coins:
                balances[coin["coin"]] = {
                    "available": float(coin["availableToWithdraw"] or 0),
                    "total": float(coin["walletBalance"] or 0)
                }
            
            return balances
        else:
            print(f"❌ Error getting balance: {response}")
            return None
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Разместить ордер
        
        Args:
            symbol: BTCUSDT
            side: Buy, Sell
            order_type: Market, Limit
            qty: количество
            price: цена (для Limit)
        
        Returns:
            {"orderId": "...", "status": "..."}
        """
        endpoint = "/v5/order/create"
        params = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": str(qty)
        }
        
        if order_type == "Limit" and price:
            params["price"] = str(price)
        
        response = await self._request("POST", endpoint, params)
        
        if response and response.get("retCode") == 0:
            result = response.get("result", {})
            return {
                "order_id": result.get("orderId", ""),
                "status": result.get("orderStatus", "Unknown")
            }
        else:
            print(f"❌ Error placing order: {response}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Получить открытые ордера"""
        endpoint = "/v5/order/realtime"
        params = {
            "category": "spot"
        }
        
        if symbol:
            params["symbol"] = symbol
        
        response = await self._request("GET", endpoint, params)
        
        if response.get("retCode") == 0:
            return response["result"]["list"]
        else:
            print(f"❌ Error getting open orders: {response}")
            return []
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Отменить ордер"""
        endpoint = "/v5/order/cancel"
        params = {
            "category": "spot",
            "symbol": symbol,
            "orderId": order_id
        }
        
        response = await self._request("POST", endpoint, params)
        
        return response.get("retCode") == 0
    
    async def get_trade_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Получить историю сделок (закрытые ордера)
        
        Returns:
            List of trades with execution details
        """
        endpoint = "/v5/execution/list"
        params = {
            "category": "spot",
            "limit": limit
        }
        
        if symbol:
            params["symbol"] = symbol
        
        try:
            response = await self._request("GET", endpoint, params)
            
            if response.get("retCode") == 0:
                return response["result"]["list"]
            else:
                print(f"❌ Error getting trade history: {response}")
                return []
        except Exception as e:
            print(f"❌ Exception getting trade history: {e}")
            return []
    
    async def get_trade_history_full(
        self, 
        symbol: str = "BTCUSDT", 
        limit: int = 100
    ) -> List[Dict]:
        """
        Получить полную историю сделок с пагинацией
        Собирает ВСЕ доступные данные через API
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            limit: количество записей за запрос (max 100)
        
        Returns:
            List of all trades
        """
        all_trades = []
        cursor = None
        
        print(f"📊 Collecting full trade history for {symbol}...")
        
        while True:
            endpoint = "/v5/execution/list"
            # Параметры в правильном порядке согласно документации
            params = {
                "category": "spot",
                "limit": str(limit),  # Конвертируем в string
                "symbol": symbol
            }
            
            if cursor:
                params["cursor"] = cursor
            
            try:
                response = await self._request("GET", endpoint, params)
                
                if response and response.get("retCode") == 0:
                    trades = response["result"]["list"]
                    
                    if not trades:
                        break
                    
                    all_trades.extend(trades)
                    print(f"   Collected {len(all_trades)} trades...")
                    
                    # Проверяем есть ли еще данные
                    cursor = response["result"].get("nextPageCursor")
                    if not cursor:
                        break
                    
                    # Rate limiting protection
                    await asyncio.sleep(0.5)
                else:
                    print(f"❌ Error getting trade history: {response}")
                    break
                    
            except Exception as e:
                print(f"❌ Exception getting trade history: {e}")
                break
        
        print(f"✅ Total trades collected: {len(all_trades)}")
        return all_trades
    
    async def get_closed_pnl_history(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 100
    ) -> List[Dict]:
        """
        Получить историю закрытых позиций с PnL
        ВНИМАНИЕ: Работает только для futures/linear, не для spot!
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            limit: количество записей за запрос (max 100)
        
        Returns:
            List of closed positions with PnL
        """
        all_pnl = []
        cursor = None
        
        print(f"📊 Collecting PnL history for {symbol}...")
        print(f"⚠️  Note: This endpoint works only for futures/linear, not spot")
        
        while True:
            endpoint = "/v5/position/closed-pnl"
            # Параметры в правильном порядке
            params = {
                "category": "linear",  # Для futures
                "limit": str(limit),  # Конвертируем в string
                "symbol": symbol
            }
            
            if cursor:
                params["cursor"] = cursor
            
            try:
                response = await self._request("GET", endpoint, params)
                
                if response and response.get("retCode") == 0:
                    pnl_records = response["result"]["list"]
                    
                    if not pnl_records:
                        break
                    
                    all_pnl.extend(pnl_records)
                    print(f"   Collected {len(all_pnl)} PnL records...")
                    
                    cursor = response["result"].get("nextPageCursor")
                    if not cursor:
                        break
                    
                    await asyncio.sleep(0.5)
                else:
                    print(f"❌ Error getting PnL history: {response}")
                    break
                    
            except Exception as e:
                print(f"❌ Exception getting PnL history: {e}")
                break
        
        print(f"✅ Total PnL records collected: {len(all_pnl)}")
        return all_pnl
    
    async def get_wallet_transactions(
        self,
        coin: str = "USDT",
        limit: int = 50
    ) -> List[Dict]:
        """
        Получить историю движения средств (internal transfers)
        ВНИМАНИЕ: Может не работать в Demo API!
        
        Args:
            coin: USDT, BTC, ETH
            limit: количество записей за запрос (max 50)
        
        Returns:
            List of wallet transactions
        """
        all_transactions = []
        cursor = None
        
        print(f"📊 Collecting wallet transactions for {coin}...")
        print(f"⚠️  Note: This endpoint may not be available in Demo API")
        
        while True:
            # Правильный endpoint согласно документации
            endpoint = "/v5/asset/transfer/query-inter-transfer-list"
            params = {
                "coin": coin,
                "limit": str(limit)
            }
            
            if cursor:
                params["cursor"] = cursor
            
            try:
                response = await self._request("GET", endpoint, params)
                
                if response and response.get("retCode") == 0:
                    transactions = response["result"]["list"]
                    
                    if not transactions:
                        break
                    
                    all_transactions.extend(transactions)
                    print(f"   Collected {len(all_transactions)} transactions...")
                    
                    cursor = response["result"].get("nextPageCursor")
                    if not cursor:
                        break
                    
                    await asyncio.sleep(0.5)
                else:
                    print(f"❌ Error getting transactions: {response}")
                    print(f"   This endpoint may not be available in Demo API")
                    break
                    
            except Exception as e:
                print(f"❌ Exception getting transactions: {e}")
                break
        
        print(f"✅ Total transactions collected: {len(all_transactions)}")
        return all_transactions
    
    async def get_klines_historical(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить исторические свечи за период
        С пагинацией для больших периодов
        
        Args:
            symbol: BTCUSDT, ETHUSDT
            interval: 1, 5, 15, 60, 240, D
            start_time: timestamp в миллисекундах
            end_time: timestamp в миллисекундах
            limit: количество свечей за запрос (max 1000)
        
        Returns:
            List of historical candles
        """
        all_klines = []
        current_end = end_time
        
        print(f"📊 Collecting historical klines for {symbol} ({interval})...")
        
        while current_end > start_time:
            endpoint = "/v5/market/kline"
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "start": start_time,
                "end": current_end,
                "limit": limit
            }
            
            try:
                response = await self._request("GET", endpoint, params)
                
                if response.get("retCode") == 0:
                    candles = response["result"]["list"]
                    
                    if not candles:
                        break
                    
                    # Преобразуем в удобный формат
                    formatted_candles = [
                        {
                            "timestamp": int(c[0]),
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5])
                        }
                        for c in candles
                    ]
                    
                    all_klines.extend(formatted_candles)
                    print(f"   Collected {len(all_klines)} candles...")
                    
                    # Обновляем current_end для следующей итерации
                    oldest_timestamp = min(int(c[0]) for c in candles)
                    if oldest_timestamp <= start_time:
                        break
                    
                    current_end = oldest_timestamp - 1
                    
                    await asyncio.sleep(0.5)
                else:
                    print(f"❌ Error getting klines: {response}")
                    break
                    
            except Exception as e:
                print(f"❌ Exception getting klines: {e}")
                break
        
        # Сортируем по timestamp (от старых к новым)
        all_klines.sort(key=lambda x: x["timestamp"])
        
        print(f"✅ Total candles collected: {len(all_klines)}")
        return all_klines


# Singleton
_bybit_api = None

def get_bybit_api() -> BybitAPI:
    """Получить singleton instance"""
    global _bybit_api
    if _bybit_api is None:
        _bybit_api = BybitAPI()
    return _bybit_api
