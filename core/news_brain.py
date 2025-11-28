"""
News Brain - Фундаментальный анализ через CryptoPanic + VADER Sentiment
Легковесный NLP без тяжелых нейросетей
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import aiohttp
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import settings


class MarketSentiment(Enum):
    """Рыночный сентимент"""
    EXTREME_FEAR = "EXTREME_FEAR"      # < -0.5 - PANIC SELL
    FEAR = "FEAR"                       # -0.5 to -0.2
    NEUTRAL = "NEUTRAL"                 # -0.2 to 0.2
    GREED = "GREED"                     # 0.2 to 0.5
    EXTREME_GREED = "EXTREME_GREED"    # > 0.5 - Strong BUY signal


class NewsBrain:
    """
    Анализатор новостного фона для криптовалют
    
    Использует:
    - CryptoPanic API (бесплатный) для получения новостей
    - VADER Sentiment для анализа тональности
    """
    
    def __init__(self):
        # CryptoPanic API - несколько ключей для ротации (100 req/month каждый)
        self.api_keys = []
        if getattr(settings, 'cryptopanic_api_key', None):
            self.api_keys.append(settings.cryptopanic_api_key)
        if getattr(settings, 'cryptopanic_api_key_2', None):
            self.api_keys.append(settings.cryptopanic_api_key_2)
        if getattr(settings, 'cryptopanic_api_key_3', None):
            self.api_keys.append(settings.cryptopanic_api_key_3)
        
        self.current_key_index = 0
        self.base_url = "https://cryptopanic.com/api/v1/posts/"
        self.coingecko_url = "https://api.coingecko.com/api/v3/search/trending"
        
        # VADER Sentiment Analyzer (легковесный, работает локально)
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Кэш новостей (КРИТИЧНО: 100 req/month = ~3 req/day на ключ!)
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 28800  # 8 часов (экономим запросы!)
        
        # Статистика
        self.stats = {
            'total_analyses': 0,
            'api_calls': 0,
            'cache_hits': 0,
            'api_errors': 0,
            'key_rotations': 0
        }
        
        print(f"📰 NewsBrain initialized with {len(self.api_keys)} API key(s)")
    
    def _rotate_key(self):
        """Ротация на следующий API ключ"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.stats['key_rotations'] += 1
            print(f"🔄 Rotated to CryptoPanic API key #{self.current_key_index + 1}")
    
    async def fetch_latest_news(
        self, 
        currencies: List[str] = None,
        hours_back: int = 1
    ) -> List[Dict]:
        """
        Получить последние новости из CryptoPanic
        
        Args:
            currencies: Список валют (BTC, ETH, etc.)
            hours_back: За сколько часов брать новости
        
        Returns:
            Список новостей с заголовками
        """
        if not self.api_keys:
            print("⚠️  CryptoPanic API keys not configured, using fallback")
            return []
        
        # Ротация ключей
        api_key = self.api_keys[self.current_key_index]
        
        # Проверяем кэш
        cache_key = f"news_{'-'.join(currencies or ['all'])}_{hours_back}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached['timestamp'] < timedelta(seconds=self._cache_ttl):
                self.stats['cache_hits'] += 1
                return cached['data']
        
        try:
            # Формируем URL (Developer plan: 24h delay, 100 req/mo)
            params = {
                'auth_token': api_key,
                'public': 'true',
                'kind': 'news'
                # Убрали filter - берём все новости для лучшего анализа
            }
            
            if currencies:
                params['currencies'] = ','.join(currencies)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)  # Увеличен таймаут
                ) as response:
                    
                    if response.status == 429:
                        print(f"⚠️  CryptoPanic rate limit, rotating key...")
                        self._rotate_key()
                        self.stats['api_errors'] += 1
                        return []
                    
                    if response.status != 200:
                        print(f"❌ CryptoPanic API error: {response.status}")
                        self.stats['api_errors'] += 1
                        self._rotate_key()
                        return []
                    
                    data = await response.json()
                    self.stats['api_calls'] += 1
                    print(f"✅ CryptoPanic: got {len(data.get('results', []))} news items")
            
            # Фильтруем по времени
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            news = []
            
            for item in data.get('results', []):
                # Парсим время публикации
                published_at = item.get('published_at', '')
                try:
                    pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    pub_time = pub_time.replace(tzinfo=None)
                    
                    if pub_time >= cutoff_time:
                        news.append({
                            'title': item.get('title', ''),
                            'source': item.get('source', {}).get('title', 'Unknown'),
                            'published_at': pub_time,
                            'votes': item.get('votes', {}),
                            'currencies': [c.get('code') for c in item.get('currencies', [])]
                        })
                except:
                    continue
            
            # Кэшируем
            self._cache[cache_key] = {
                'timestamp': datetime.utcnow(),
                'data': news
            }
            
            return news
        
        except asyncio.TimeoutError:
            print("❌ CryptoPanic API timeout, trying CoinGecko...")
            self.stats['api_errors'] += 1
            return await self._fetch_coingecko_fallback()
        except Exception as e:
            print(f"❌ CryptoPanic API error: {e}, trying CoinGecko...")
            self.stats['api_errors'] += 1
            return await self._fetch_coingecko_fallback()
    
    async def _fetch_coingecko_fallback(self) -> List[Dict]:
        """Fallback на CoinGecko trending (бесплатно, без ключа)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.coingecko_url,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    coins = data.get('coins', [])
                    
                    # Конвертируем в формат новостей
                    news = []
                    for coin in coins[:10]:
                        item = coin.get('item', {})
                        name = item.get('name', '')
                        symbol = item.get('symbol', '')
                        score = item.get('score', 0)
                        
                        # Trending = позитивный сентимент
                        news.append({
                            'title': f"{name} ({symbol}) is trending on CoinGecko",
                            'source': 'CoinGecko',
                            'published_at': datetime.utcnow(),
                            'votes': {'positive': score, 'negative': 0},
                            'currencies': [symbol]
                        })
                    
                    if news:
                        print(f"✅ CoinGecko fallback: got {len(news)} trending coins")
                    return news
        except Exception as e:
            print(f"❌ CoinGecko fallback error: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Анализ тональности текста через VADER
        
        Returns:
            {
                'compound': -1.0 to 1.0 (общий score),
                'positive': 0.0 to 1.0,
                'negative': 0.0 to 1.0,
                'neutral': 0.0 to 1.0
            }
        """
        scores = self.sentiment_analyzer.polarity_scores(text)
        return {
            'compound': scores['compound'],
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu']
        }
    
    def _calculate_weighted_sentiment(self, news: List[Dict]) -> float:
        """
        Рассчитать средневзвешенный sentiment score
        
        Веса:
        - Более свежие новости имеют больший вес
        - Новости с большим количеством голосов имеют больший вес
        """
        if not news:
            return 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        now = datetime.utcnow()
        
        for item in news:
            # Анализируем заголовок
            sentiment = self.analyze_sentiment(item['title'])
            compound = sentiment['compound']
            
            # Вес по времени (новее = важнее)
            age_hours = (now - item['published_at']).total_seconds() / 3600
            time_weight = max(0.1, 1.0 - (age_hours / 24))  # Decay за 24 часа
            
            # Вес по голосам
            votes = item.get('votes', {})
            positive_votes = votes.get('positive', 0)
            negative_votes = votes.get('negative', 0)
            vote_weight = 1.0 + (positive_votes - negative_votes) * 0.1
            vote_weight = max(0.5, min(2.0, vote_weight))  # Ограничиваем 0.5-2.0
            
            # Итоговый вес
            weight = time_weight * vote_weight
            
            weighted_sum += compound * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _score_to_sentiment(self, score: float) -> MarketSentiment:
        """Конвертировать score в категорию сентимента"""
        if score <= -0.5:
            return MarketSentiment.EXTREME_FEAR
        elif score <= -0.2:
            return MarketSentiment.FEAR
        elif score <= 0.2:
            return MarketSentiment.NEUTRAL
        elif score <= 0.5:
            return MarketSentiment.GREED
        else:
            return MarketSentiment.EXTREME_GREED

    async def get_market_sentiment(
        self, 
        symbol: str = None,
        hours_back: int = 1
    ) -> Dict:
        """
        Главный метод - получить текущий сентимент рынка
        
        Args:
            symbol: Торговая пара (BTCUSDT -> BTC)
            hours_back: За сколько часов анализировать
        
        Returns:
            {
                'sentiment': MarketSentiment,
                'score': -1.0 to 1.0,
                'news_count': int,
                'top_headlines': [...],
                'trading_allowed': bool,
                'recommendation': str
            }
        """
        self.stats['total_analyses'] += 1
        
        # Извлекаем базовую валюту из символа
        currencies = None
        if symbol:
            base = symbol.replace('USDT', '').replace('USD', '')
            currencies = [base, 'BTC']  # Всегда добавляем BTC как индикатор рынка
        
        # Получаем новости
        news = await self.fetch_latest_news(currencies, hours_back)
        
        # Если новостей нет - возвращаем NEUTRAL
        if not news:
            return {
                'sentiment': MarketSentiment.NEUTRAL,
                'score': 0.0,
                'news_count': 0,
                'top_headlines': [],
                'trading_allowed': True,
                'recommendation': 'No news data - proceed with caution'
            }
        
        # Рассчитываем взвешенный sentiment
        score = self._calculate_weighted_sentiment(news)
        sentiment = self._score_to_sentiment(score)
        
        # Определяем рекомендацию
        trading_allowed = True
        recommendation = ''
        
        if sentiment == MarketSentiment.EXTREME_FEAR:
            trading_allowed = False
            recommendation = 'PANIC SELL / CLOSE ALL - Extreme negative news!'
        elif sentiment == MarketSentiment.FEAR:
            recommendation = 'Caution - Negative sentiment, reduce position sizes'
        elif sentiment == MarketSentiment.NEUTRAL:
            recommendation = 'Normal conditions - Follow technical signals'
        elif sentiment == MarketSentiment.GREED:
            recommendation = 'Positive sentiment - Good for long positions'
        else:  # EXTREME_GREED
            recommendation = 'Strong bullish sentiment - Consider aggressive longs'
        
        # Топ заголовки для отчета
        top_headlines = [
            {
                'title': n['title'],
                'source': n['source'],
                'sentiment': self.analyze_sentiment(n['title'])['compound']
            }
            for n in news[:5]
        ]
        
        return {
            'sentiment': sentiment,
            'score': score,
            'news_count': len(news),
            'top_headlines': top_headlines,
            'trading_allowed': trading_allowed,
            'recommendation': recommendation
        }
    
    def print_stats(self):
        """Вывести статистику"""
        print(f"📰 News Brain Statistics:")
        print(f"   API Keys: {len(self.api_keys)} (current: #{self.current_key_index + 1})")
        print(f"   Total Analyses: {self.stats['total_analyses']}")
        print(f"   API Calls: {self.stats['api_calls']}")
        print(f"   Cache Hits: {self.stats['cache_hits']}")
        print(f"   API Errors: {self.stats['api_errors']}")
        print(f"   Key Rotations: {self.stats['key_rotations']}")


# Singleton
_news_brain = None

def get_news_brain() -> NewsBrain:
    """Получить singleton instance"""
    global _news_brain
    if _news_brain is None:
        _news_brain = NewsBrain()
    return _news_brain
