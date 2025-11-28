"""
News Brain v2.0 - Фундаментальный анализ через CryptoPanic + VADER Sentiment
С расширенным крипто-словарём для корректного определения EXTREME_FEAR/GREED

МОДУЛЬ 3: "Крипто-Словарь" для Новостей
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


# ========== МОДУЛЬ 3: Крипто-словарь для VADER ==========
CRYPTO_LEXICON = {
    # Bullish terms (позитивные)
    "bullish": 2.0,
    "moon": 2.0,
    "mooning": 2.5,
    "gem": 1.5,
    "pump": 1.5,
    "pumping": 1.8,
    "breakout": 1.5,
    "ath": 2.0,  # All-Time High
    "hodl": 1.0,
    "hodling": 1.0,
    "lambo": 1.5,
    "wagmi": 1.5,  # We're All Gonna Make It
    "dyor": 0.5,  # Do Your Own Research (нейтрально-позитивный)
    "accumulate": 1.2,
    "accumulating": 1.2,
    "rally": 1.5,
    "surge": 1.8,
    "surging": 2.0,
    "soaring": 2.0,
    "skyrocket": 2.5,
    "parabolic": 2.0,
    "bullrun": 2.5,
    "adoption": 1.5,
    "institutional": 1.2,
    "etf": 1.5,
    "approved": 1.8,
    "partnership": 1.2,
    "upgrade": 1.0,
    "mainnet": 1.2,
    "launch": 1.0,
    "airdrop": 0.8,
    
    # Bearish terms (негативные)
    "bearish": -2.0,
    "rekt": -2.0,
    "rekted": -2.5,
    "dump": -2.0,
    "dumping": -2.5,
    "fud": -1.5,  # Fear, Uncertainty, Doubt
    "crash": -2.5,
    "crashing": -3.0,
    "scam": -3.0,
    "scammer": -3.0,
    "hack": -3.0,
    "hacked": -3.5,
    "exploit": -2.5,
    "exploited": -3.0,
    "rug": -3.5,  # Rug pull
    "rugpull": -3.5,
    "rugged": -3.5,
    "ponzi": -3.0,
    "fraud": -3.0,
    "sec": -1.0,  # SEC обычно негатив для крипты
    "lawsuit": -2.0,
    "investigation": -1.5,
    "ban": -2.5,
    "banned": -2.5,
    "regulation": -1.0,
    "crackdown": -2.0,
    "selloff": -2.0,
    "capitulation": -2.5,
    "bloodbath": -3.0,
    "plunge": -2.5,
    "plunging": -2.5,
    "tank": -2.0,
    "tanking": -2.5,
    "collapse": -3.0,
    "collapsed": -3.0,
    "bankruptcy": -3.5,
    "bankrupt": -3.5,
    "insolvent": -3.0,
    "liquidation": -2.0,
    "liquidated": -2.5,
    "ngmi": -1.5,  # Not Gonna Make It
    "exit": -1.0,
    "withdraw": -0.8,
    "withdrawal": -0.5,
    "delay": -1.0,
    "delayed": -1.2,
    "bug": -1.5,
    "vulnerability": -2.0,
    "attack": -2.5,
    "stolen": -3.0,
    "theft": -3.0,
    "lost": -1.5,
    "missing": -1.5,
    "warning": -1.5,
    "caution": -1.0,
    "risk": -0.8,
    "risky": -1.0,
    "volatile": -0.5,
    "volatility": -0.3,
    "uncertainty": -1.0,
    "fear": -1.5,
    "panic": -2.5,
    "worried": -1.2,
    "concern": -1.0,
    "concerned": -1.2,
}


class NewsBrain:
    """
    Анализатор новостного фона для криптовалют v2.0
    
    Использует:
    - CryptoPanic API (бесплатный) для получения новостей
    - VADER Sentiment с расширенным крипто-словарём
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
        
        # VADER Sentiment Analyzer с крипто-словарём
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self._update_lexicon_with_crypto_terms()
        
        # Кэш новостей (КРИТИЧНО: 100 req/month = ~3 req/day на ключ!)
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 28800  # 8 часов (экономим запросы!)
        
        # Статистика
        self.stats = {
            'total_analyses': 0,
            'api_calls': 0,
            'cache_hits': 0,
            'api_errors': 0,
            'key_rotations': 0,
            'extreme_fear_count': 0,
            'extreme_greed_count': 0
        }
        
        print(f"📰 NewsBrain v2.0 initialized with {len(self.api_keys)} API key(s)")
        print(f"   📚 Crypto lexicon: {len(CRYPTO_LEXICON)} terms added to VADER")
    
    def _update_lexicon_with_crypto_terms(self):
        """
        МОДУЛЬ 3: Обновить лексикон VADER крипто-терминами
        Критично для корректного определения EXTREME_FEAR/GREED
        """
        try:
            self.sentiment_analyzer.lexicon.update(CRYPTO_LEXICON)
            print(f"✅ VADER lexicon updated with {len(CRYPTO_LEXICON)} crypto terms")
        except Exception as e:
            print(f"⚠️  Failed to update VADER lexicon: {e}")
    
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
            }
            
            if currencies:
                params['currencies'] = ','.join(currencies)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
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
                    
                    news = []
                    for coin in coins[:10]:
                        item = coin.get('item', {})
                        name = item.get('name', '')
                        symbol = item.get('symbol', '')
                        score = item.get('score', 0)
                        
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
        Анализ тональности текста через VADER с крипто-словарём
        
        Returns:
            {
                'compound': -1.0 to 1.0 (общий score),
                'positive': 0.0 to 1.0,
                'negative': 0.0 to 1.0,
                'neutral': 0.0 to 1.0
            }
        """
        # Приводим к нижнему регистру для лучшего матчинга
        text_lower = text.lower()
        scores = self.sentiment_analyzer.polarity_scores(text_lower)
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
            # Анализируем заголовок с крипто-словарём
            sentiment = self.analyze_sentiment(item['title'])
            compound = sentiment['compound']
            
            # Вес по времени (новее = важнее)
            age_hours = (now - item['published_at']).total_seconds() / 3600
            time_weight = max(0.1, 1.0 - (age_hours / 24))
            
            # Вес по голосам
            votes = item.get('votes', {})
            positive_votes = votes.get('positive', 0)
            negative_votes = votes.get('negative', 0)
            vote_weight = 1.0 + (positive_votes - negative_votes) * 0.1
            vote_weight = max(0.5, min(2.0, vote_weight))
            
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
            self.stats['extreme_fear_count'] += 1
            return MarketSentiment.EXTREME_FEAR
        elif score <= -0.2:
            return MarketSentiment.FEAR
        elif score <= 0.2:
            return MarketSentiment.NEUTRAL
        elif score <= 0.5:
            return MarketSentiment.GREED
        else:
            self.stats['extreme_greed_count'] += 1
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
            currencies = [base, 'BTC']
        
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
        
        # Рассчитываем взвешенный sentiment с крипто-словарём
        score = self._calculate_weighted_sentiment(news)
        sentiment = self._score_to_sentiment(score)
        
        # Определяем рекомендацию
        trading_allowed = True
        recommendation = ''
        
        if sentiment == MarketSentiment.EXTREME_FEAR:
            trading_allowed = False
            recommendation = '🚨 PANIC SELL / CLOSE ALL - Extreme negative news detected!'
        elif sentiment == MarketSentiment.FEAR:
            recommendation = '⚠️ Caution - Negative sentiment, reduce position sizes by 50%'
        elif sentiment == MarketSentiment.NEUTRAL:
            recommendation = '✅ Normal conditions - Follow technical signals'
        elif sentiment == MarketSentiment.GREED:
            recommendation = '📈 Positive sentiment - Good for LONG positions'
        else:  # EXTREME_GREED
            recommendation = '🚀 Strong bullish sentiment - Consider aggressive LONGs'
        
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
        print(f"📰 News Brain v2.0 Statistics:")
        print(f"   API Keys: {len(self.api_keys)} (current: #{self.current_key_index + 1})")
        print(f"   Total Analyses: {self.stats['total_analyses']}")
        print(f"   API Calls: {self.stats['api_calls']}")
        print(f"   Cache Hits: {self.stats['cache_hits']}")
        print(f"   API Errors: {self.stats['api_errors']}")
        print(f"   Key Rotations: {self.stats['key_rotations']}")
        print(f"   EXTREME_FEAR detected: {self.stats['extreme_fear_count']}")
        print(f"   EXTREME_GREED detected: {self.stats['extreme_greed_count']}")


# Singleton
_news_brain = None

def get_news_brain() -> NewsBrain:
    """Получить singleton instance"""
    global _news_brain
    if _news_brain is None:
        _news_brain = NewsBrain()
    return _news_brain
