"""
News Brain - RSS Агрегатор с продвинутым анализом тональности.

Собирает новости из проверенных крипто-источников и рассчитывает
взвешенный сентимент рынка через кастомизированный VADER.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from functools import lru_cache

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dateutil import parser as date_parser


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://beincrypto.com/feed/",
    "https://theblock.co/rss.xml"
]

# Кастомный крипто-словарь для VADER
CRYPTO_LEXICON = {
    # Бычьи сигналы (+)
    'bullish': 2.0,
    'bull': 1.5,
    'moon': 2.0,
    'mooning': 2.5,
    'pump': 1.5,
    'breakout': 1.5,
    'ath': 2.5,
    'all time high': 2.5,
    'adoption': 1.0,
    'partnership': 1.0,
    'launch': 1.0,
    'mainnet': 1.5,
    'buy the dip': 1.5,
    'long': 1.0,
    'support': 0.5,
    'rally': 1.5,
    'approval': 2.0,
    'upgrade': 1.0,
    
    # Медвежьи сигналы (-)
    'bearish': -2.0,
    'bear': -1.5,
    'dump': -2.0,
    'crash': -3.0,
    'rekt': -2.0,
    'scam': -3.5,
    'rug': -3.5,
    'rugpull': -3.5,
    'hack': -3.0,
    'exploit': -3.0,
    'stolen': -3.0,
    'ban': -2.0,
    'regulation': -1.0,
    'sec': -0.5,
    'lawsuit': -1.5,
    'delist': -2.5,
    'insolvent': -3.5,
    'bankruptcy': -3.5,
    'resistance': -0.5,
    'sell': -1.0,
    'short': -1.0
}

# Ключевые слова для повышенного веса новости
HIGH_IMPACT_KEYWORDS = ['bitcoin', 'ethereum', 'sec', 'binance', 'btc', 'eth']

# Настройки
CACHE_TTL_SECONDS = 60
NEWS_MAX_AGE_HOURS = 2


# =============================================================================
# NEWS AGGREGATOR
# =============================================================================

class NewsAggregator:
    """
    Асинхронный агрегатор крипто-новостей с анализом тональности.
    
    Использует кастомизированный VADER для понимания крипто-сленга
    и взвешивает новости по их важности.
    """
    
    def __init__(self):
        # Инициализация VADER с крипто-словарем
        self.analyzer = SentimentIntensityAnalyzer()
        self.analyzer.lexicon.update(CRYPTO_LEXICON)
        
        # Кэш для предотвращения частых запросов
        self._cache: Optional[dict] = None
        self._cache_time: float = 0
        
        # Хранилище хешей заголовков для дедупликации
        self._seen_headlines: set = set()
    
    def _get_headline_hash(self, headline: str) -> str:
        """Генерирует хеш заголовка для дедупликации."""
        normalized = headline.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _is_fresh_news(self, published_str: str) -> bool:
        """Проверяет, что новость не старше NEWS_MAX_AGE_HOURS."""
        try:
            published = date_parser.parse(published_str)
            
            # Приводим к UTC если нет timezone
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age = now - published
            
            return age < timedelta(hours=NEWS_MAX_AGE_HOURS)
        except Exception:
            # Если не можем распарсить дату - считаем новость свежей
            return True
    
    def _calculate_weight(self, headline: str) -> float:
        """Рассчитывает вес новости на основе ключевых слов."""
        headline_lower = headline.lower()
        
        for keyword in HIGH_IMPACT_KEYWORDS:
            if keyword in headline_lower:
                return 1.5
        
        return 1.0
    
    def _analyze_headline(self, headline: str) -> float:
        """Анализирует тональность заголовка через VADER."""
        scores = self.analyzer.polarity_scores(headline)
        return scores['compound']
    
    def _get_status(self, score: float) -> str:
        """Определяет статус рынка по сентименту."""
        if score <= -0.5:
            return "EXTREME_FEAR"
        elif score <= -0.15:
            return "FEAR"
        elif score <= 0.15:
            return "NEUTRAL"
        elif score <= 0.5:
            return "GREED"
        else:
            return "EXTREME_GREED"

    async def _fetch_feed(self, url: str) -> list:
        """
        Асинхронно загружает и парсит RSS-ленту.
        
        Оборачивает синхронный feedparser в executor для неблокирующей работы.
        """
        loop = asyncio.get_event_loop()
        
        try:
            # Запускаем синхронный feedparser в отдельном потоке
            feed = await loop.run_in_executor(None, feedparser.parse, url)
            
            if feed.bozo:
                # feedparser обнаружил проблему с фидом
                print(f"⚠️ RSS Warning for {url}: {feed.bozo_exception}")
            
            return feed.entries if feed.entries else []
            
        except Exception as e:
            print(f"❌ RSS Error for {url}: {e}")
            return []
    
    async def _fetch_all_feeds(self) -> list:
        """Параллельно загружает все RSS-ленты."""
        tasks = [self._fetch_feed(url) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_entries = []
        for result in results:
            if isinstance(result, list):
                all_entries.extend(result)
        
        return all_entries
    
    def _process_entries(self, entries: list) -> list:
        """
        Фильтрует и обрабатывает новостные записи.
        
        - Убирает дубликаты
        - Фильтрует старые новости
        - Рассчитывает взвешенный сентимент
        """
        processed = []
        
        for entry in entries:
            title = entry.get('title', '').strip()
            if not title:
                continue
            
            # Дедупликация по хешу заголовка
            headline_hash = self._get_headline_hash(title)
            if headline_hash in self._seen_headlines:
                continue
            self._seen_headlines.add(headline_hash)
            
            # Фильтр по свежести
            published = entry.get('published', entry.get('updated', ''))
            if published and not self._is_fresh_news(published):
                continue
            
            # Анализ тональности
            raw_score = self._analyze_headline(title)
            weight = self._calculate_weight(title)
            weighted_score = raw_score * weight
            
            processed.append({
                'title': title,
                'raw_score': raw_score,
                'weighted_score': weighted_score,
                'weight': weight
            })
        
        return processed
    
    async def get_market_sentiment(self) -> dict:
        """
        Главный метод: возвращает текущий сентимент рынка.
        
        Returns:
            dict: {
                'sentiment_score': float (-1.0 to 1.0),
                'status': str (EXTREME_FEAR/FEAR/NEUTRAL/GREED/EXTREME_GREED),
                'news_count': int,
                'top_headline': str
            }
        """
        # Проверяем кэш
        now = time.time()
        if self._cache and (now - self._cache_time) < CACHE_TTL_SECONDS:
            return self._cache
        
        # Сбрасываем seen headlines для нового цикла
        self._seen_headlines.clear()
        
        # Загружаем все фиды
        entries = await self._fetch_all_feeds()
        
        if not entries:
            result = {
                'sentiment_score': 0.0,
                'status': 'NEUTRAL',
                'news_count': 0,
                'top_headline': 'No news available'
            }
            self._cache = result
            self._cache_time = now
            return result
        
        # Обрабатываем новости
        processed = self._process_entries(entries)
        
        if not processed:
            result = {
                'sentiment_score': 0.0,
                'status': 'NEUTRAL',
                'news_count': 0,
                'top_headline': 'No fresh news'
            }
            self._cache = result
            self._cache_time = now
            return result
        
        # Рассчитываем средний взвешенный сентимент
        total_weighted_score = sum(n['weighted_score'] for n in processed)
        total_weight = sum(n['weight'] for n in processed)
        
        avg_sentiment = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Ограничиваем диапазон [-1, 1]
        avg_sentiment = max(-1.0, min(1.0, avg_sentiment))
        
        # Находим самую "сильную" новость (по абсолютному значению)
        top_news = max(processed, key=lambda x: abs(x['weighted_score']))
        
        result = {
            'sentiment_score': round(avg_sentiment, 4),
            'status': self._get_status(avg_sentiment),
            'news_count': len(processed),
            'top_headline': top_news['title']
        }
        
        # Кэшируем результат
        self._cache = result
        self._cache_time = now
        
        return result
    
    async def get_detailed_analysis(self) -> dict:
        """
        Расширенный анализ для дебага и логирования.
        
        Возвращает базовый сентимент + топ-5 бычьих и медвежьих новостей.
        """
        base = await self.get_market_sentiment()
        
        # Для детального анализа нужно перезагрузить данные
        self._seen_headlines.clear()
        entries = await self._fetch_all_feeds()
        processed = self._process_entries(entries)
        
        # Сортируем по score
        sorted_news = sorted(processed, key=lambda x: x['weighted_score'], reverse=True)
        
        bullish = [n for n in sorted_news if n['weighted_score'] > 0][:5]
        bearish = [n for n in sorted_news if n['weighted_score'] < 0][-5:]
        
        return {
            **base,
            'bullish_headlines': [n['title'] for n in bullish],
            'bearish_headlines': [n['title'] for n in bearish]
        }


# =============================================================================
# BACKWARD COMPATIBILITY - MarketSentiment Enum
# =============================================================================

from enum import Enum

class MarketSentiment(Enum):
    """Enum для совместимости со старым кодом."""
    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"


# =============================================================================
# SINGLETON
# =============================================================================

_news_aggregator: Optional[NewsAggregator] = None


def get_news_aggregator() -> NewsAggregator:
    """Возвращает singleton экземпляр NewsAggregator."""
    global _news_aggregator
    if _news_aggregator is None:
        _news_aggregator = NewsAggregator()
    return _news_aggregator


# =============================================================================
# BACKWARD COMPATIBILITY - NewsBrain wrapper
# =============================================================================

class NewsBrain:
    """
    Wrapper для совместимости со старым интерфейсом ai_brain_local.py
    
    Старый интерфейс ожидает:
    - get_market_sentiment(symbol, hours_back) -> dict с 'sentiment', 'score', 'news_count', 'recommendation'
    - print_stats()
    """
    
    def __init__(self):
        self._aggregator = get_news_aggregator()
        self._stats = {'calls': 0, 'errors': 0}
    
    async def get_market_sentiment(self, symbol: str = None, hours_back: int = 2) -> dict:
        """
        Совместимый интерфейс для ai_brain_local.py
        
        Returns:
            {
                'sentiment': MarketSentiment,
                'score': float,
                'news_count': int,
                'recommendation': str
            }
        """
        self._stats['calls'] += 1
        
        try:
            result = await self._aggregator.get_market_sentiment()
            
            # Конвертируем status string в MarketSentiment enum
            status_map = {
                'EXTREME_FEAR': MarketSentiment.EXTREME_FEAR,
                'FEAR': MarketSentiment.FEAR,
                'NEUTRAL': MarketSentiment.NEUTRAL,
                'GREED': MarketSentiment.GREED,
                'EXTREME_GREED': MarketSentiment.EXTREME_GREED
            }
            
            sentiment = status_map.get(result['status'], MarketSentiment.NEUTRAL)
            
            # Генерируем recommendation
            if sentiment == MarketSentiment.EXTREME_FEAR:
                recommendation = f"🚨 EXTREME FEAR! Consider closing positions. Top: {result['top_headline'][:50]}..."
            elif sentiment == MarketSentiment.FEAR:
                recommendation = f"⚠️ Fear in market. Be cautious with new positions."
            elif sentiment == MarketSentiment.EXTREME_GREED:
                recommendation = f"🚀 EXTREME GREED! Good for longs, avoid shorts."
            elif sentiment == MarketSentiment.GREED:
                recommendation = f"📈 Greed detected. Bullish sentiment."
            else:
                recommendation = f"😐 Neutral market. Follow technical signals."
            
            return {
                'sentiment': sentiment,
                'score': result['sentiment_score'],
                'news_count': result['news_count'],
                'recommendation': recommendation,
                'top_headline': result['top_headline']
            }
            
        except Exception as e:
            self._stats['errors'] += 1
            print(f"❌ NewsBrain error: {e}")
            return {
                'sentiment': MarketSentiment.NEUTRAL,
                'score': 0.0,
                'news_count': 0,
                'recommendation': f'Error: {e}'
            }
    
    def print_stats(self):
        """Вывести статистику."""
        print(f"📰 NewsBrain Stats: {self._stats['calls']} calls, {self._stats['errors']} errors")


_news_brain: Optional[NewsBrain] = None


def get_news_brain() -> NewsBrain:
    """Возвращает singleton экземпляр NewsBrain (для совместимости)."""
    global _news_brain
    if _news_brain is None:
        _news_brain = NewsBrain()
    return _news_brain


# =============================================================================
# QUICK TEST
# =============================================================================

async def _test():
    """Быстрый тест модуля."""
    print("🔍 Testing News Brain...")
    
    aggregator = get_news_aggregator()
    result = await aggregator.get_market_sentiment()
    
    print(f"\n📊 Market Sentiment Analysis:")
    print(f"   Score: {result['sentiment_score']}")
    print(f"   Status: {result['status']}")
    print(f"   News Count: {result['news_count']}")
    print(f"   Top Headline: {result['top_headline'][:80]}...")
    
    return result


if __name__ == "__main__":
    asyncio.run(_test())
