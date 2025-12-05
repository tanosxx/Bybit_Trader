"""
Strategic Compliance Enforcer
Принудительное соблюдение стратегии Strategic Brain

Закрывает позиции, которые противоречат текущему режиму рынка:
- UNCERTAIN → Закрыть ВСЕ (Cash is King)
- BEAR_CRASH → Закрыть все LONG (только SHORT разрешены)
- BULL_RUSH → Закрыть все SHORT (только LONG разрешены)
- SIDEWAYS → Всё разрешено (ничего не закрывать)
"""

from typing import List, Dict
from datetime import datetime


class StrategicComplianceEnforcer:
    """
    Проверяет соответствие открытых позиций текущему режиму Strategic Brain
    """
    
    def __init__(self):
        self.last_regime = None
        self.regime_change_time = None
    
    def enforce_strategic_compliance(
        self, 
        active_positions: List[Dict], 
        current_regime: str
    ) -> List[Dict]:
        """
        Определяет какие позиции нужно закрыть для соблюдения стратегии
        
        Args:
            active_positions: Список открытых позиций
                [{'symbol': 'BTCUSDT', 'side': 'BUY', 'entry_price': 50000, ...}, ...]
            current_regime: Текущий режим Strategic Brain
                'UNCERTAIN', 'BEAR_CRASH', 'BULL_RUSH', 'SIDEWAYS'
        
        Returns:
            Список позиций на закрытие с причинами
            [{'symbol': 'BTCUSDT', 'side': 'BUY', 'reason': '...'}, ...]
        """
        # Отслеживаем изменение режима
        if self.last_regime != current_regime:
            print(f"🔄 Strategic Regime changed: {self.last_regime} → {current_regime}")
            self.last_regime = current_regime
            self.regime_change_time = datetime.now()
        
        positions_to_close = []
        
        if not active_positions:
            return positions_to_close
        
        # Логика закрытия по режимам
        if current_regime == "UNCERTAIN":
            # UNCERTAIN: Закрыть ВСЕ позиции (Cash is King)
            for pos in active_positions:
                positions_to_close.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'reason': 'Strategic Compliance: UNCERTAIN regime (Cash is King)',
                    'regime': current_regime
                })
            
            if positions_to_close:
                print(f"⚠️  UNCERTAIN Regime: Closing ALL {len(positions_to_close)} positions")
        
        elif current_regime == "BEAR_CRASH":
            # BEAR_CRASH: Закрыть все LONG позиции (только SHORT разрешены)
            for pos in active_positions:
                if pos['side'] in ['BUY', 'LONG']:
                    positions_to_close.append({
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'reason': 'Strategic Compliance: BEAR_CRASH regime (LONG not allowed)',
                        'regime': current_regime
                    })
            
            if positions_to_close:
                print(f"🐻 BEAR_CRASH Regime: Closing {len(positions_to_close)} LONG positions")
        
        elif current_regime == "BULL_RUSH":
            # BULL_RUSH: Закрыть все SHORT позиции (только LONG разрешены)
            for pos in active_positions:
                if pos['side'] in ['SELL', 'SHORT']:
                    positions_to_close.append({
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'reason': 'Strategic Compliance: BULL_RUSH regime (SHORT not allowed)',
                        'regime': current_regime
                    })
            
            if positions_to_close:
                print(f"🚀 BULL_RUSH Regime: Closing {len(positions_to_close)} SHORT positions")
        
        elif current_regime == "SIDEWAYS":
            # SIDEWAYS: Всё разрешено, ничего не закрывать
            pass
        
        return positions_to_close
    
    def get_compliance_status(
        self, 
        active_positions: List[Dict], 
        current_regime: str
    ) -> Dict:
        """
        Возвращает статус соответствия позиций стратегии
        
        Returns:
            {
                'compliant': True/False,
                'total_positions': 5,
                'non_compliant_positions': 2,
                'regime': 'UNCERTAIN',
                'action_required': 'Close 2 positions'
            }
        """
        positions_to_close = self.enforce_strategic_compliance(active_positions, current_regime)
        
        return {
            'compliant': len(positions_to_close) == 0,
            'total_positions': len(active_positions),
            'non_compliant_positions': len(positions_to_close),
            'regime': current_regime,
            'action_required': f'Close {len(positions_to_close)} positions' if positions_to_close else 'None'
        }


# Singleton
_enforcer_instance = None

def get_compliance_enforcer() -> StrategicComplianceEnforcer:
    """Получить singleton instance"""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = StrategicComplianceEnforcer()
    return _enforcer_instance
