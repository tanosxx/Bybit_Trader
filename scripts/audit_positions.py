#!/usr/bin/env python3
"""
🔍 AUDIT POSITIONS - Проверка безопасности открытых позиций

Скрипт для ручной проверки всех открытых фьючерсных позиций.
Выводит детальный отчёт с предупреждениями о рисках.

Запуск на сервере:
  docker exec bybit_bot python scripts/audit_positions.py
"""
import sys
import os
import asyncio
import hmac
import hashlib
import time
import aiohttp

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from datetime import datetime


# ANSI цвета для консоли
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header():
    """Вывести заголовок"""
    print("\n" + "=" * 80)
    print(f"{Colors.BOLD}{Colors.CYAN}🔍 BYBIT FUTURES POSITIONS AUDIT{Colors.END}")
    print(f"   Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   API: {settings.bybit_base_url}")
    print("=" * 80)


def print_warning(msg: str):
    """Вывести предупреждение"""
    print(f"{Colors.RED}{Colors.BOLD}⚠️  WARNING: {msg}{Colors.END}")


def print_danger(msg: str):
    """Вывести критическое предупреждение"""
    print(f"{Colors.RED}{Colors.BOLD}🚨 DANGER: {msg}{Colors.END}")


def print_ok(msg: str):
    """Вывести OK"""
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def format_price(price: float) -> str:
    """Форматировать цену"""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"


def format_pnl(pnl: float) -> str:
    """Форматировать PnL с цветом"""
    if pnl >= 0:
        return f"{Colors.GREEN}+${pnl:.2f}{Colors.END}"
    else:
        return f"{Colors.RED}-${abs(pnl):.2f}{Colors.END}"


class SimpleBybitAPI:
    """Простой API клиент для аудита"""
    
    def __init__(self):
        self.api_key = settings.bybit_api_key
        self.api_secret = settings.bybit_api_secret
        self.base_url = "https://api-demo.bybit.com"
        self.recv_window = "5000"
    
    def _generate_signature(self, timestamp: str, params: str = "") -> str:
        sign_string = f"{timestamp}{self.api_key}{self.recv_window}{params}"
        return hmac.new(
            bytes(self.api_secret, 'utf-8'),
            bytes(sign_string, 'utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: dict = None):
        timestamp = str(int(time.time() * 1000))
        
        if method == "GET" and params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(timestamp, query_string)
            url = f"{self.base_url}{endpoint}?{query_string}"
        else:
            signature = self._generate_signature(timestamp)
            url = f"{self.base_url}{endpoint}"
        
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": self.recv_window,
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers) as resp:
                return await resp.json()
    
    async def get_positions(self):
        params = {"category": "linear", "settleCoin": "USDT"}
        return await self._request("GET", "/v5/position/list", params)
    
    async def get_wallet_balance(self):
        params = {"accountType": "UNIFIED"}
        return await self._request("GET", "/v5/account/wallet-balance", params)


async def get_positions():
    """Получить все открытые фьючерсные позиции"""
    try:
        api = SimpleBybitAPI()
        response = await api.get_positions()
        
        if response.get('retCode') != 0:
            print(f"{Colors.RED}❌ API Error: {response.get('retMsg')}{Colors.END}")
            return []
        
        positions = response['result']['list']
        open_positions = [p for p in positions if float(p['size']) > 0]
        return open_positions
    
    except Exception as e:
        print(f"{Colors.RED}❌ Error connecting to Bybit: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return []


async def get_wallet_balance():
    """Получить баланс кошелька"""
    try:
        api = SimpleBybitAPI()
        response = await api.get_wallet_balance()
        
        if response.get('retCode') != 0:
            return None
        
        coins = response['result']['list'][0]['coin']
        usdt = next((c for c in coins if c['coin'] == 'USDT'), None)
        
        if usdt:
            return {
                'total': float(usdt['walletBalance']),
                'available': float(usdt['availableToWithdraw']),
                'unrealized_pnl': float(usdt['unrealisedPnl']) if usdt['unrealisedPnl'] else 0
            }
        return None
    except Exception as e:
        print(f"Error getting balance: {e}")
        return None


def audit_position(pos: dict, index: int) -> dict:
    """Проанализировать одну позицию и вернуть отчёт"""
    symbol = pos['symbol']
    side = pos['side']
    size = float(pos['size'])
    leverage = int(pos['leverage'])
    entry_price = float(pos['avgPrice']) if pos['avgPrice'] else 0
    mark_price = float(pos['markPrice']) if pos['markPrice'] else 0
    liq_price = float(pos['liqPrice']) if pos['liqPrice'] else 0
    stop_loss = float(pos['stopLoss']) if pos['stopLoss'] else 0
    take_profit = float(pos['takeProfit']) if pos['takeProfit'] else 0
    unrealized_pnl = float(pos['unrealisedPnl']) if pos['unrealisedPnl'] else 0
    position_value = float(pos['positionValue']) if pos['positionValue'] else 0
    margin_mode = pos.get('tradeMode', 'Unknown')  # 0=Cross, 1=Isolated
    position_margin = float(pos['positionIM']) if pos['positionIM'] else 0
    
    # Определяем режим маржи
    if margin_mode == 0 or margin_mode == '0':
        margin_mode_str = "CROSS"
    else:
        margin_mode_str = "ISOLATED"
    
    warnings = []
    dangers = []
    
    # Проверки безопасности
    if leverage > 7:
        warnings.append(f"High leverage: {leverage}x (recommended max 7x)")
    
    if margin_mode_str == "CROSS":
        dangers.append("CROSS MARGIN MODE - All balance at risk!")
    
    if stop_loss == 0:
        dangers.append("NO STOP LOSS SET!")
    
    if liq_price > 0:
        # Проверяем близость к ликвидации
        if side == 'Buy':
            liq_distance_pct = ((mark_price - liq_price) / mark_price) * 100
        else:
            liq_distance_pct = ((liq_price - mark_price) / mark_price) * 100
        
        if liq_distance_pct < 5:
            dangers.append(f"CLOSE TO LIQUIDATION! Only {liq_distance_pct:.1f}% away")
        elif liq_distance_pct < 10:
            warnings.append(f"Liquidation distance: {liq_distance_pct:.1f}%")
    
    return {
        'index': index,
        'symbol': symbol,
        'side': side,
        'size': size,
        'leverage': leverage,
        'margin_mode': margin_mode_str,
        'entry_price': entry_price,
        'mark_price': mark_price,
        'liq_price': liq_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'unrealized_pnl': unrealized_pnl,
        'position_value': position_value,
        'position_margin': position_margin,
        'warnings': warnings,
        'dangers': dangers
    }


def print_position_report(report: dict):
    """Вывести отчёт по позиции"""
    print(f"\n{Colors.BOLD}{'─' * 70}{Colors.END}")
    print(f"{Colors.BOLD}#{report['index']} {report['symbol']}{Colors.END}")
    print(f"{'─' * 70}")
    
    # Side с цветом
    side_color = Colors.GREEN if report['side'] == 'Buy' else Colors.RED
    side_label = "LONG 📈" if report['side'] == 'Buy' else "SHORT 📉"
    print(f"   Side:           {side_color}{side_label}{Colors.END}")
    
    # Size
    print(f"   Size:           {report['size']}")
    
    # Leverage
    lev = report['leverage']
    if lev > 7:
        print(f"   Leverage:       {Colors.YELLOW}{lev}x ⚠️{Colors.END}")
    else:
        print(f"   Leverage:       {lev}x")
    
    # Margin Mode
    if report['margin_mode'] == 'CROSS':
        print(f"   Margin Mode:    {Colors.RED}{Colors.BOLD}CROSS 🚨{Colors.END}")
    else:
        print(f"   Margin Mode:    {Colors.GREEN}ISOLATED ✅{Colors.END}")
    
    # Prices
    print(f"   Entry Price:    {format_price(report['entry_price'])}")
    print(f"   Mark Price:     {format_price(report['mark_price'])}")
    
    if report['liq_price'] > 0:
        print(f"   Liq. Price:     {Colors.YELLOW}{format_price(report['liq_price'])}{Colors.END}")
    
    # Stop Loss
    if report['stop_loss'] == 0:
        print(f"   Stop Loss:      {Colors.RED}{Colors.BOLD}NOT SET 🚨{Colors.END}")
    else:
        print(f"   Stop Loss:      {format_price(report['stop_loss'])}")
    
    # Take Profit
    if report['take_profit'] == 0:
        print(f"   Take Profit:    Not set")
    else:
        print(f"   Take Profit:    {format_price(report['take_profit'])}")
    
    # Margin & PnL
    print(f"   Position Value: {format_price(report['position_value'])}")
    print(f"   Margin Used:    {format_price(report['position_margin'])}")
    print(f"   Unrealized PnL: {format_pnl(report['unrealized_pnl'])}")
    
    # Warnings
    for warning in report['warnings']:
        print_warning(warning)
    
    # Dangers
    for danger in report['dangers']:
        print_danger(danger)


def print_summary(reports: list, balance: dict):
    """Вывести итоговую сводку"""
    print(f"\n{'=' * 80}")
    print(f"{Colors.BOLD}{Colors.CYAN}📊 SUMMARY{Colors.END}")
    print(f"{'=' * 80}")
    
    total_positions = len(reports)
    total_margin = sum(r['position_margin'] for r in reports)
    total_pnl = sum(r['unrealized_pnl'] for r in reports)
    total_dangers = sum(len(r['dangers']) for r in reports)
    total_warnings = sum(len(r['warnings']) for r in reports)
    
    longs = len([r for r in reports if r['side'] == 'Buy'])
    shorts = len([r for r in reports if r['side'] == 'Sell'])
    
    print(f"\n   Total Positions:    {total_positions}")
    print(f"   LONGs:              {Colors.GREEN}{longs}{Colors.END}")
    print(f"   SHORTs:             {Colors.RED}{shorts}{Colors.END}")
    print(f"   Total Margin Used:  {format_price(total_margin)}")
    print(f"   Total Unrealized:   {format_pnl(total_pnl)}")
    
    if balance:
        print(f"\n   {Colors.BOLD}Wallet Balance:{Colors.END}")
        print(f"   Total USDT:         {format_price(balance['total'])}")
        print(f"   Available:          {format_price(balance['available'])}")
        margin_pct = (total_margin / balance['total'] * 100) if balance['total'] > 0 else 0
        print(f"   Margin Usage:       {margin_pct:.1f}%")
    
    # Risk Assessment
    print(f"\n   {Colors.BOLD}Risk Assessment:{Colors.END}")
    
    if total_dangers > 0:
        print(f"   {Colors.RED}{Colors.BOLD}🚨 CRITICAL ISSUES: {total_dangers}{Colors.END}")
    else:
        print(f"   {Colors.GREEN}✅ No critical issues{Colors.END}")
    
    if total_warnings > 0:
        print(f"   {Colors.YELLOW}⚠️  Warnings: {total_warnings}{Colors.END}")
    else:
        print(f"   {Colors.GREEN}✅ No warnings{Colors.END}")
    
    # Positions without SL
    no_sl = len([r for r in reports if r['stop_loss'] == 0])
    if no_sl > 0:
        print(f"   {Colors.RED}🚨 Positions without Stop Loss: {no_sl}{Colors.END}")
    
    # Cross margin positions
    cross = len([r for r in reports if r['margin_mode'] == 'CROSS'])
    if cross > 0:
        print(f"   {Colors.RED}🚨 Cross Margin Positions: {cross}{Colors.END}")
    
    print(f"\n{'=' * 80}\n")


async def main():
    """Главная функция"""
    print_header()
    
    # Получаем позиции
    print(f"\n{Colors.CYAN}Fetching positions from Bybit API...{Colors.END}")
    positions = await get_positions()
    
    if not positions:
        print(f"\n{Colors.GREEN}✅ No open futures positions found.{Colors.END}")
        print(f"{'=' * 80}\n")
        return
    
    print(f"\n{Colors.YELLOW}Found {len(positions)} open position(s){Colors.END}")
    
    # Получаем баланс
    balance = await get_wallet_balance()
    
    # Анализируем каждую позицию
    reports = []
    for i, pos in enumerate(positions, 1):
        report = audit_position(pos, i)
        reports.append(report)
        print_position_report(report)
    
    # Выводим сводку
    print_summary(reports, balance)


if __name__ == "__main__":
    asyncio.run(main())
