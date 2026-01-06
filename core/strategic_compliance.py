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
        self.last_closed_positions = set()  # Отслеживаем закрытые позиции
        self.notification_sent_for_regime = None  # Режим для которого отправили уведомление
    
    def enforce_strategic_compliance(
        self, 
        active_positions: List[Dict], 
        current_regime: str
    ) -> tuple[List[Dict], bool]:
        """
        Определяет какие позиции нужно закрыть для соблюдения стратегии
        
        Args:
            active_positions: Список открытых позиций
                [{'symbol': 'BTCUSDT', 'side': 'BUY', 'entry_price': 50000, ...}, ...]
            current_regime: Текущий режим Strategic Brain
                'UNCERTAIN', 'BEAR_CRASH', 'BULL_RUSH', 'SIDEWAYS'
        
        Returns:
            Tuple: (positions_to_close, should_notify)
            - positions_to_close: Список позиций на закрытие с причинами
            - should_notify: True если нужно отправить уведомление
        """
        # Отслеживаем изменение режима
        regime_changed = False
        if self.last_regime != current_regime:
            print(f"🔄 Strategic Regime changed: {self.last_regime} → {current_regime}")
            self.last_regime = current_regime
            self.regime_change_time = datetime.now()
            self.notification_sent_for_regime = None  # Сбрасываем флаг уведомления
            self.last_closed_positions.clear()  # Очищаем список закрытых позиций
            regime_changed = True
        
        positions_to_close = []
        
        if not active_positions:
            return positions_to_close, False
        
        # Логика закрытия по режимам
        if current_regime == "UNCERTAIN":
            # UNCERTAIN: Закрыть ВСЕ позиции (Cash is King)
            for pos in active_positions:
                pos_key = f"{pos['symbol']}_{pos['side']}"
                if pos_key not in self.last_closed_positions:
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
                    pos_key = f"{pos['symbol']}_{pos['side']}"
                    if pos_key not in self.last_closed_positions:
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
                    pos_key = f"{pos['symbol']}_{pos['side']}"
                    if pos_key not in self.last_closed_positions:
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
        
        # Определяем нужно ли отправлять уведомление
        should_notify = False
        if positions_to_close:
            # Отправляем уведомление только если:
            # 1. Режим изменился (первый раз для нового режима)
            # 2. ИЛИ появились новые несоответствующие позиции
            if regime_changed or self.notification_sent_for_regime != current_regime:
                should_notify = True
                self.notification_sent_for_regime = current_regime
                
                # Запоминаем закрытые позиции
                for pos in positions_to_close:
                    pos_key = f"{pos['symbol']}_{pos['side']}"
                    self.last_closed_positions.add(pos_key)
        
        return positions_to_close, should_notify
    
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
        positions_to_close, _ = self.enforce_strategic_compliance(active_positions, current_regime)
        
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
