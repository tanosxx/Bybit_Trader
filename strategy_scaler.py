"""
Dynamic Strategy Scaler - Автоматическое масштабирование стратегии

Система Tier-based управления:
- Tier 1 (Survival Mode): $0-200 - Консервативная стратегия (SOL, ETH)
- Tier 2 (Growth Mode): $200-600 - Сбалансированная стратегия (SOL, ETH, BNB)
- Tier 3 (Dominion Mode): $600+ - Агрессивная стратегия (SOL, ETH, BNB, AVAX, DOGE)

Автоматически:
- Переключает торговые пары
- Изменяет риск на сделку
- Обновляет лимиты позиций
- Уведомляет в Telegram
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class StrategyScaler:
    """
    Динамическое масштабирование торговой стратегии
    
    Управляет переключением между Tier-ами в зависимости от баланса.
    """
    
    def __init__(self, settings_path: str = "settings.json"):
        self.settings_path = settings_path
        self.tiers = {}
        self.current_tier = None
        self.excluded_pairs = []
        self.scan_pairs = []
        
        # Загружаем конфигурацию
        self._load_settings()
        
        print(f"🎯 Strategy Scaler initialized")
        print(f"   Tiers loaded: {len(self.tiers)}")
        print(f"   Excluded pairs: {', '.join(self.excluded_pairs)}")
    
    def _load_settings(self):
        """Загрузить настройки из JSON"""
        try:
            settings_file = Path(self.settings_path)
            
            if not settings_file.exists():
                print(f"⚠️ Settings file not found: {self.settings_path}")
                print(f"   Using default tier configuration")
                self._create_default_settings()
                return
            
            with open(settings_file, 'r') as f:
                data = json.load(f)
            
            # Загружаем Tier-ы
            self.tiers = data.get('strategy_tiers', {})
            
            # Загружаем исключённые пары
            excluded = data.get('excluded_pairs', {})
            self.excluded_pairs = list(excluded.keys())
            
            # Загружаем пары для сканирования
            scan_config = data.get('scan_pairs', {})
            self.scan_pairs = scan_config.get('pairs', [])
            
            print(f"✅ Settings loaded from {self.settings_path}")
            
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
            self._create_default_settings()
    
    def _create_default_settings(self):
        """Создать настройки по умолчанию"""
        self.tiers = {
            'tier_1': {
                'name': 'Survival Mode',
                'min_balance': 0,
                'max_balance': 200,
                'active_pairs': ['SOLUSDT', 'ETHUSDT'],
                'max_open_positions': 3,
                'risk_per_trade': 0.12,
                'min_confidence': 0.65
            },
            'tier_2': {
                'name': 'Growth Mode',
                'min_balance': 200,
                'max_balance': 600,
                'active_pairs': ['SOLUSDT', 'ETHUSDT', 'BNBUSDT'],
                'max_open_positions': 5,
                'risk_per_trade': 0.10,
                'min_confidence': 0.60
            },
            'tier_3': {
                'name': 'Dominion Mode',
                'min_balance': 600,
                'max_balance': 999999,
                'active_pairs': ['SOLUSDT', 'ETHUSDT', 'BNBUSDT', 'AVAXUSDT', 'DOGEUSDT'],
                'max_open_positions': 7,
                'risk_per_trade': 0.08,
                'min_confidence': 0.55
            }
        }
        self.excluded_pairs = ['XRPUSDT', 'BTCUSDT']
        self.scan_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'AVAXUSDT', 'DOGEUSDT']
    
    def get_tier_for_balance(self, balance: float) -> Optional[Dict]:
        """
        Определить Tier для текущего баланса
        
        Args:
            balance: Текущий баланс в USDT
        
        Returns:
            Dict с настройками Tier или None
        """
        for tier_id, tier_config in self.tiers.items():
            min_bal = tier_config.get('min_balance', 0)
            max_bal = tier_config.get('max_balance', 999999)
            
            if min_bal <= balance < max_bal:
                return {
                    'id': tier_id,
                    **tier_config
                }
        
        # Если не нашли - возвращаем последний (самый высокий)
        last_tier_id = list(self.tiers.keys())[-1]
        return {
            'id': last_tier_id,
            **self.tiers[last_tier_id]
        }
    
    def get_symbols_to_scan(self, active_pairs: List[str]) -> List[str]:
        """
        Получить список символов для сканирования
        
        ВАЖНО: Всегда включает BTCUSDT для BTC Correlation Filter,
        даже если он не в active_pairs!
        
        Args:
            active_pairs: Активные торговые пары
        
        Returns:
            List символов для сканирования (уникальные)
        """
        # Начинаем с активных пар
        symbols = set(active_pairs)
        
        # ОБЯЗАТЕЛЬНО добавляем BTCUSDT для корреляционного фильтра
        symbols.add('BTCUSDT')
        
        # Добавляем остальные пары из scan_pairs (если есть)
        if self.scan_pairs:
            symbols.update(self.scan_pairs)
        
        return sorted(list(symbols))
    
    def update_strategy(self, current_balance: float) -> Dict:
        """
        Обновить стратегию на основе текущего баланса
        
        Args:
            current_balance: Текущий баланс в USDT
        
        Returns:
            Dict с результатами обновления:
            {
                'tier_changed': bool,
                'tier': Dict,
                'active_pairs': List[str],
                'symbols_to_scan': List[str],
                'max_open_positions': int,
                'risk_per_trade': float,
                'min_confidence': float
            }
        """
        # Определяем новый Tier
        new_tier = self.get_tier_for_balance(current_balance)
        
        if not new_tier:
            print(f"⚠️ Could not determine tier for balance ${current_balance:.2f}")
            return {'tier_changed': False}
        
        # Проверяем изменился ли Tier
        tier_changed = False
        if self.current_tier is None or self.current_tier['id'] != new_tier['id']:
            tier_changed = True
            old_tier_name = self.current_tier['name'] if self.current_tier else 'None'
            
            print(f"\n{'='*80}")
            print(f"🚀 STRATEGY UPGRADE: Tier Change Detected!")
            print(f"{'='*80}")
            print(f"   Balance: ${current_balance:.2f}")
            print(f"   Old Tier: {old_tier_name}")
            print(f"   New Tier: {new_tier['name']} ({new_tier['id']})")
            print(f"   Active Pairs: {', '.join(new_tier['active_pairs'])}")
            print(f"   Max Positions: {new_tier['max_open_positions']}")
            print(f"   Risk per Trade: {new_tier['risk_per_trade']*100:.0f}%")
            print(f"   Min Confidence: {new_tier['min_confidence']*100:.0f}%")
            print(f"{'='*80}\n")
            
            self.current_tier = new_tier
        
        # Получаем символы для сканирования
        symbols_to_scan = self.get_symbols_to_scan(new_tier['active_pairs'])
        
        return {
            'tier_changed': tier_changed,
            'tier': new_tier,
            'tier_id': new_tier['id'],
            'tier_name': new_tier['name'],
            'active_pairs': new_tier['active_pairs'],
            'symbols_to_scan': symbols_to_scan,
            'max_open_positions': new_tier['max_open_positions'],
            'risk_per_trade': new_tier['risk_per_trade'],
            'min_confidence': new_tier['min_confidence']
        }
    
    def get_current_tier_info(self) -> Optional[Dict]:
        """Получить информацию о текущем Tier"""
        return self.current_tier
    
    def is_pair_allowed(self, symbol: str) -> bool:
        """
        Проверить разрешена ли пара для торговли
        
        Args:
            symbol: Символ пары (например, 'BTCUSDT')
        
        Returns:
            True если пара разрешена, False если исключена
        """
        # Проверяем исключённые пары
        if symbol in self.excluded_pairs:
            return False
        
        # Проверяем активные пары текущего Tier
        if self.current_tier:
            return symbol in self.current_tier.get('active_pairs', [])
        
        return False
    
    def get_tier_stats(self) -> Dict:
        """Получить статистику по всем Tier-ам"""
        stats = {
            'total_tiers': len(self.tiers),
            'current_tier': self.current_tier['name'] if self.current_tier else 'None',
            'excluded_pairs': self.excluded_pairs,
            'tiers': {}
        }
        
        for tier_id, tier_config in self.tiers.items():
            stats['tiers'][tier_id] = {
                'name': tier_config['name'],
                'balance_range': f"${tier_config['min_balance']}-${tier_config['max_balance']}",
                'pairs': tier_config['active_pairs'],
                'max_positions': tier_config['max_open_positions'],
                'risk': f"{tier_config['risk_per_trade']*100:.0f}%"
            }
        
        return stats


# Singleton
_strategy_scaler = None

def get_strategy_scaler() -> StrategyScaler:
    """Получить singleton экземпляр StrategyScaler"""
    global _strategy_scaler
    if _strategy_scaler is None:
        _strategy_scaler = StrategyScaler()
    return _strategy_scaler


# Пример использования
if __name__ == "__main__":
    scaler = get_strategy_scaler()
    
    # Тест с разными балансами
    test_balances = [50, 150, 250, 400, 700]
    
    for balance in test_balances:
        print(f"\n{'='*80}")
        print(f"Testing balance: ${balance}")
        print(f"{'='*80}")
        
        result = scaler.update_strategy(balance)
        
        print(f"Tier Changed: {result['tier_changed']}")
        print(f"Tier: {result['tier_name']}")
        print(f"Active Pairs: {result['active_pairs']}")
        print(f"Symbols to Scan: {result['symbols_to_scan']}")
        print(f"Max Positions: {result['max_open_positions']}")
        print(f"Risk: {result['risk_per_trade']*100:.0f}%")
    
    # Статистика
    print(f"\n{'='*80}")
    print(f"TIER STATISTICS")
    print(f"{'='*80}")
    stats = scaler.get_tier_stats()
    print(json.dumps(stats, indent=2))
