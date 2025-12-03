"""
Scenario Tester - Pattern Matching для поиска исторических аналогов

Модуль ищет похожие паттерны в истории и предсказывает вероятность успеха
на основе того, что происходило после этих паттернов раньше.

Алгоритм:
1. Загружаем 1000 свечей 15m для каждого символа
2. Нормализуем данные (MinMax Scaling)
3. При получении сигнала ищем топ-10 похожих паттернов (Euclidean Distance)
4. Смотрим что было после них и считаем Historical Win Rate
"""
import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time


class ScenarioTester:
    """
    Pattern Matching для поиска исторических аналогов
    
    Graceful Degradation: если история не загружена, возвращает Neutral (50%)
    """
    
    def __init__(self, api_client):
        """
        Args:
            api_client: BybitAPI instance для загрузки исторических данных
        """
        self.api = api_client
        
        # Хранилище исторических данных
        # {symbol: {'closes': np.array, 'normalized': np.array, 'timestamp': float}}
        self.history: Dict[str, Dict] = {}
        
        # Флаг готовности
        self.is_ready = False
        
        # Время последнего обновления для каждого символа
        self.last_update: Dict[str, float] = {}
        
        # Параметры
        self.history_length = 1000  # Количество свечей для загрузки
        self.pattern_length = 20  # Длина паттерна для сравнения
        self.forecast_length = 5  # Сколько свечей смотреть вперёд
        self.top_k = 10  # Топ-10 похожих паттернов
        self.success_threshold = 0.005  # 0.5% движение = успех
        
        print(f"🔍 ScenarioTester initialized:")
        print(f"   History: {self.history_length} candles")
        print(f"   Pattern: {self.pattern_length} candles")
        print(f"   Forecast: {self.forecast_length} candles ahead")
        print(f"   Top-K: {self.top_k} similar patterns")
    
    async def load_initial_history(self, symbols: List[str]):
        """
        Загрузить начальную историю для всех символов (async)
        
        Args:
            symbols: список символов для загрузки
        """
        print(f"📥 Loading history for {len(symbols)} symbols...")
        
        tasks = []
        for symbol in symbols:
            tasks.append(self._load_symbol_history(symbol))
        
        # Загружаем параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Подсчитываем успешные загрузки
        success_count = sum(1 for r in results if r is True)
        
        if success_count > 0:
            self.is_ready = True
            print(f"✅ History loaded: {success_count}/{len(symbols)} symbols ready")
        else:
            print(f"⚠️ History loading failed for all symbols")
    
    async def _load_symbol_history(self, symbol: str) -> bool:
        """
        Загрузить историю для одного символа
        
        Returns:
            True если успешно
        """
        try:
            # Загружаем свечи через API
            klines = await self.api.get_klines(
                symbol=symbol,
                interval='15',  # 15 минут
                limit=self.history_length
            )
            
            if not klines or len(klines) < self.pattern_length + self.forecast_length:
                print(f"   ⚠️ {symbol}: недостаточно данных ({len(klines) if klines else 0} свечей)")
                return False
            
            # Извлекаем Close prices
            closes = np.array([float(k['close']) for k in klines])
            
            # Нормализуем данные (MinMax Scaling)
            normalized = self._normalize(closes)
            
            # Сохраняем
            self.history[symbol] = {
                'closes': closes,
                'normalized': normalized,
                'timestamp': time.time()
            }
            
            self.last_update[symbol] = time.time()
            
            print(f"   ✅ {symbol}: {len(closes)} candles loaded")
            return True
        
        except Exception as e:
            print(f"   ❌ {symbol}: error loading history: {e}")
            return False
    
    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """
        MinMax нормализация данных
        
        Нормализуем чтобы сравнивать форму графика, а не абсолютные цены
        
        Args:
            data: массив цен
        
        Returns:
            нормализованный массив (0-1)
        """
        min_val = np.min(data)
        max_val = np.max(data)
        
        if max_val == min_val:
            return np.zeros_like(data)
        
        return (data - min_val) / (max_val - min_val)
    
    async def update_history(self, symbol: str):
        """
        Обновить историю для символа (добавить новую свечу)
        
        Lazy Loading: вызывается только если прошло >15 минут
        
        Args:
            symbol: символ для обновления
        """
        try:
            # Проверяем нужно ли обновление
            last_update_time = self.last_update.get(symbol, 0)
            if time.time() - last_update_time < 900:  # 15 минут
                return
            
            # Загружаем последнюю свечу
            klines = await self.api.get_klines(
                symbol=symbol,
                interval='15',
                limit=1
            )
            
            if not klines:
                return
            
            new_close = float(klines[0]['close'])
            
            # Обновляем массив (добавляем новую, удаляем старую)
            if symbol in self.history:
                closes = self.history[symbol]['closes']
                closes = np.append(closes[1:], new_close)  # Shift left + append
                
                # Пересчитываем нормализацию
                normalized = self._normalize(closes)
                
                self.history[symbol]['closes'] = closes
                self.history[symbol]['normalized'] = normalized
                self.history[symbol]['timestamp'] = time.time()
                
                self.last_update[symbol] = time.time()
        
        except Exception as e:
            print(f"⚠️ {symbol}: error updating history: {e}")
    
    def find_similar_patterns(self, symbol: str, current_pattern: np.ndarray) -> List[int]:
        """
        Найти топ-K похожих паттернов в истории
        
        Использует Vectorized Euclidean Distance для скорости
        
        Args:
            symbol: символ
            current_pattern: последние N свечей (Close prices)
        
        Returns:
            список индексов похожих паттернов
        """
        if symbol not in self.history:
            return []
        
        normalized_history = self.history[symbol]['normalized']
        
        # Нормализуем текущий паттерн
        current_normalized = self._normalize(current_pattern)
        
        # Исключаем последние pattern_length свечей (чтобы не найти себя)
        search_space = normalized_history[:-(self.pattern_length + self.forecast_length)]
        
        if len(search_space) < self.pattern_length:
            return []
        
        # Sliding window: создаём все возможные паттерны
        num_windows = len(search_space) - self.pattern_length + 1
        
        # Vectorized: создаём матрицу всех паттернов
        patterns = np.array([
            search_space[i:i + self.pattern_length]
            for i in range(num_windows)
        ])
        
        # Vectorized Euclidean Distance
        distances = np.linalg.norm(patterns - current_normalized, axis=1)
        
        # Топ-K минимальных дистанций
        top_k_indices = np.argsort(distances)[:self.top_k]
        
        return top_k_indices.tolist()
    
    def analyze_outcome(self, symbol: str, intended_signal: str) -> float:
        """
        Проанализировать исход похожих паттернов
        
        Смотрит что происходило после найденных паттернов и считает Win Rate
        
        Args:
            symbol: символ
            intended_signal: 'BUY' или 'SELL'
        
        Returns:
            Historical Win Rate (0-100%)
        
        Graceful: возвращает 50% если история не готова
        """
        # Graceful degradation
        if not self.is_ready or symbol not in self.history:
            return 50.0  # Neutral
        
        try:
            closes = self.history[symbol]['closes']
            
            # Берём последние pattern_length свечей как текущий паттерн
            if len(closes) < self.pattern_length:
                return 50.0
            
            current_pattern = closes[-self.pattern_length:]
            
            # Находим похожие паттерны
            similar_indices = self.find_similar_patterns(symbol, current_pattern)
            
            if not similar_indices:
                return 50.0  # Нет похожих паттернов
            
            # Анализируем что было после каждого паттерна
            successes = 0
            
            for idx in similar_indices:
                # Индекс начала паттерна
                pattern_start = idx
                pattern_end = pattern_start + self.pattern_length
                
                # Проверяем есть ли forecast_length свечей после паттерна
                if pattern_end + self.forecast_length > len(closes):
                    continue
                
                # Цена в конце паттерна
                entry_price = closes[pattern_end - 1]
                
                # Цены после паттерна
                future_prices = closes[pattern_end:pattern_end + self.forecast_length]
                
                # Определяем успех в зависимости от направления
                if intended_signal == 'BUY':
                    # Для BUY: успех = цена выросла > threshold
                    max_future_price = np.max(future_prices)
                    price_change = (max_future_price - entry_price) / entry_price
                    
                    if price_change > self.success_threshold:
                        successes += 1
                
                elif intended_signal == 'SELL':
                    # Для SELL: успех = цена упала > threshold
                    min_future_price = np.min(future_prices)
                    price_change = (entry_price - min_future_price) / entry_price
                    
                    if price_change > self.success_threshold:
                        successes += 1
            
            # Считаем Win Rate
            total_patterns = len(similar_indices)
            win_rate = (successes / total_patterns * 100) if total_patterns > 0 else 50.0
            
            return float(win_rate)
        
        except Exception as e:
            print(f"⚠️ {symbol}: error analyzing outcome: {e}")
            return 50.0  # Neutral при ошибке


# Singleton
_scenario_tester = None

def get_scenario_tester(api_client=None):
    """Получить singleton instance"""
    global _scenario_tester
    if _scenario_tester is None:
        if api_client is None:
            raise ValueError("api_client required for first initialization")
        _scenario_tester = ScenarioTester(api_client)
    return _scenario_tester
