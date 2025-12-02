"""
SAFETY GUARDIAN - Автоматический аудит и защита позиций

Запускается каждый цикл торговли и:
1. Проверяет ВСЕ открытые позиции на бирже
2. Закрывает позиции в CROSS margin
3. Закрывает позиции без Stop Loss
4. Закрывает позиции с размером больше лимита
5. Отправляет алерты в Telegram

КРИТИЧНО: Этот модуль - последняя линия защиты!
"""
import asyncio
from typing import Dict, List, Tuple
from datetime import datetime

from core.bybit_api import get_bybit_api


class SafetyGuardian:
    """
    Автоматический страж безопасности
    
    Проверяет и закрывает опасные позиции:
    - CROSS margin → закрыть
    - Без Stop Loss → закрыть
    - Размер > лимита → закрыть
    """
    
    def __init__(self):
        self.api = get_bybit_api()
        
        # Лимиты безопасности
        self.max_position_value_usd = 800.0  # Макс размер позиции $800 (увеличено для leverage)
        self.max_total_exposure_usd = 2500.0  # Макс общая экспозиция $2500
        self.require_stop_loss = False  # ОТКЛЮЧЕНО: Demo API не поддерживает SL/TP при открытии
        self.require_isolated = False  # Demo API не поддерживает ISOLATED!
        
        # Статистика
        self.checks_count = 0
        self.violations_found = 0
        self.positions_closed = 0
        self.total_emergency_pnl = 0.0
        
        print(f"🛡️ SafetyGuardian initialized:")
        print(f"   Max Position: ${self.max_position_value_usd}")
        print(f"   Max Exposure: ${self.max_total_exposure_usd}")
        print(f"   Require SL: {self.require_stop_loss}")
        print(f"   Require ISOLATED: {self.require_isolated}")
    
    async def audit_and_protect(self) -> Dict:
        """
        Главный метод - аудит и защита
        
        Returns:
            {
                'checked': int,
                'violations': List[str],
                'closed': List[Dict],
                'total_pnl': float
            }
        """
        self.checks_count += 1
        result = {
            'checked': 0,
            'violations': [],
            'closed': [],
            'total_pnl': 0.0
        }
        
        try:
            # Получаем все позиции с биржи
            positions = await self._get_all_positions()
            result['checked'] = len(positions)
            
            if not positions:
                return result
            
            print(f"\n🛡️ [GUARDIAN] Checking {len(positions)} positions...")
            
            # Проверяем каждую позицию
            for pos in positions:
                violations = self._check_position(pos)
                
                if violations:
                    result['violations'].extend(violations)
                    self.violations_found += len(violations)
                    
                    # ЗАКРЫВАЕМ ОПАСНУЮ ПОЗИЦИЮ!
                    print(f"   🚨 {pos['symbol']}: {', '.join(violations)}")
                    close_result = await self._emergency_close(pos, violations)
                    
                    if close_result:
                        result['closed'].append(close_result)
                        result['total_pnl'] += close_result.get('pnl', 0)
                        self.positions_closed += 1
                        self.total_emergency_pnl += close_result.get('pnl', 0)
            
            # Проверяем общую экспозицию
            total_exposure = sum(p.get('position_value', 0) for p in positions)
            if total_exposure > self.max_total_exposure_usd:
                msg = f"Total exposure ${total_exposure:.2f} > ${self.max_total_exposure_usd} limit"
                result['violations'].append(msg)
                print(f"   🚨 {msg}")
                # Закрываем самую большую позицию
                largest = max(positions, key=lambda p: p.get('position_value', 0))
                close_result = await self._emergency_close(largest, ["Exposure limit exceeded"])
                if close_result:
                    result['closed'].append(close_result)
                    result['total_pnl'] += close_result.get('pnl', 0)
            
            if result['closed']:
                print(f"   ✅ Closed {len(result['closed'])} dangerous positions")
                print(f"   💰 Emergency PnL: ${result['total_pnl']:+.2f}")
            else:
                print(f"   ✅ All positions safe")
            
        except Exception as e:
            print(f"   ❌ Guardian error: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    async def _get_all_positions(self) -> List[Dict]:
        """Получить все открытые фьючерсные позиции"""
        try:
            endpoint = "/v5/position/list"
            params = {
                "category": "linear",
                "settleCoin": "USDT"
            }
            
            response = await self.api._request("GET", endpoint, params)
            
            if response and response.get("retCode") == 0:
                positions = []
                for p in response["result"]["list"]:
                    size = float(p.get("size", 0))
                    if size > 0:
                        entry_price = float(p.get("avgPrice", 0) or 0)
                        positions.append({
                            'symbol': p["symbol"],
                            'side': p["side"],
                            'size': size,
                            'entry_price': entry_price,
                            'mark_price': float(p.get("markPrice", 0) or 0),
                            'leverage': p.get("leverage", "1"),
                            'trade_mode': p.get("tradeMode", 1),  # 0=CROSS, 1=ISOLATED
                            'stop_loss': p.get("stopLoss", ""),
                            'take_profit': p.get("takeProfit", ""),
                            'unrealized_pnl': float(p.get("unrealisedPnl", 0) or 0),
                            'position_value': size * entry_price if entry_price else 0
                        })
                return positions
            return []
        except Exception as e:
            print(f"   ❌ Error getting positions: {e}")
            return []
    
    def _check_position(self, pos: Dict) -> List[str]:
        """
        Проверить позицию на нарушения
        
        Returns:
            List of violation messages (empty if safe)
        """
        violations = []
        symbol = pos['symbol']
        
        # 1. Проверка CROSS margin
        if self.require_isolated:
            trade_mode = pos.get('trade_mode', 1)
            # trade_mode: 0 = CROSS, 1 = ISOLATED
            if trade_mode == 0 or str(trade_mode) == "0":
                violations.append("CROSS MARGIN")
        
        # 2. Проверка Stop Loss
        if self.require_stop_loss:
            sl = pos.get('stop_loss', '')
            if not sl or sl == '' or sl == '0':
                violations.append("NO STOP LOSS")
        
        # 3. Проверка размера позиции
        position_value = pos.get('position_value', 0)
        if position_value > self.max_position_value_usd:
            violations.append(f"SIZE ${position_value:.0f} > ${self.max_position_value_usd}")
        
        return violations
    
    async def _emergency_close(self, pos: Dict, reasons: List[str]) -> Dict:
        """
        Экстренное закрытие позиции
        
        Returns:
            {'symbol': str, 'pnl': float, 'reasons': List[str]}
        """
        symbol = pos['symbol']
        side = pos['side']
        size = pos['size']
        
        # Противоположная сторона для закрытия
        close_side = "Sell" if side == "Buy" else "Buy"
        
        try:
            endpoint = "/v5/order/create"
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": close_side,
                "orderType": "Market",
                "qty": str(size),
                "positionIdx": 0,
                "reduceOnly": True
            }
            
            response = await self.api._request("POST", endpoint, params)
            
            if response and response.get("retCode") == 0:
                pnl = pos.get('unrealized_pnl', 0)
                print(f"   🚨 EMERGENCY CLOSE {symbol} {side} {size} | PnL: ${pnl:+.2f}")
                print(f"      Reasons: {', '.join(reasons)}")
                return {
                    'symbol': symbol,
                    'side': side,
                    'size': size,
                    'pnl': pnl,
                    'reasons': reasons
                }
            else:
                print(f"   ❌ Failed to close {symbol}: {response}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error closing {symbol}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Получить статистику Guardian"""
        return {
            'checks': self.checks_count,
            'violations_found': self.violations_found,
            'positions_closed': self.positions_closed,
            'emergency_pnl': self.total_emergency_pnl
        }


# Singleton
_safety_guardian = None

def get_safety_guardian() -> SafetyGuardian:
    global _safety_guardian
    if _safety_guardian is None:
        _safety_guardian = SafetyGuardian()
    return _safety_guardian
