"""
Полная диагностика системы Bybit Trading Bot
Проверяет все модули, логи, торги, защиту, новости
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from database.db import async_session, engine
from database.models import Trade, AIDecision, SystemLog, WalletHistory, TradeStatus
from core.bybit_api import BybitAPI
from core.news_brain import get_news_brain
from core.ml_predictor_v2 import get_ml_predictor
from config import settings


class SystemDiagnostics:
    """Полная диагностика системы"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.utcnow(),
            'checks': [],
            'warnings': [],
            'errors': [],
            'score': 0,
            'max_score': 0
        }
    
    def check(self, name: str, passed: bool, details: str = ""):
        """Добавить результат проверки"""
        self.results['max_score'] += 1
        if passed:
            self.results['score'] += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")
            self.results['errors'].append(f"{name}: {details}")
        
        self.results['checks'].append({
            'name': name,
            'passed': passed,
            'details': details
        })
    
    def warn(self, message: str):
        """Добавить предупреждение"""
        print(f"⚠️  {message}")
        self.results['warnings'].append(message)
    
    async def run_all_checks(self):
        """Запустить все проверки"""
        print("\n" + "="*80)
        print("🔍 ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ")
        print("="*80 + "\n")
        
        await self.check_database()
        await self.check_api()
        await self.check_trading()
        await self.check_ml_system()
        await self.check_news_system()
        await self.check_logging()
        await self.check_safety()
        await self.check_sync()
        
        self.print_summary()
    
    async def check_database(self):
        """Проверка базы данных"""
        print("\n📊 БАЗА ДАННЫХ")
        print("-" * 40)
        
        try:
            async with async_session() as session:
                # Проверка подключения
                result = await session.execute(text("SELECT 1"))
                self.check("Подключение к БД", result.scalar() == 1)
                
                # Проверка таблиц
                tables = ['trades', 'ai_decisions', 'system_logs', 'wallet_history', 'candles']
                for table in tables:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    self.check(f"Таблица {table}", count is not None, f"{count} записей")
                
                # Проверка индексов
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE tablename IN ('trades', 'ai_decisions', 'system_logs')
                """))
                indexes = result.scalar()
                self.check("Индексы БД", indexes >= 5, f"{indexes} индексов")
                
        except Exception as e:
            self.check("База данных", False, str(e))
    
    async def check_api(self):
        """Проверка Bybit API"""
        print("\n🌐 BYBIT API")
        print("-" * 40)
        
        try:
            api = BybitAPI()
            
            # Проверка баланса
            balance = await api.get_wallet_balance()
            self.check("API: Получение баланса", balance is not None, 
                      f"Монет: {len(balance) if balance else 0}")
            
            # Проверка позиций
            positions = await api.get_positions()
            open_pos = [p for p in positions if float(p.get('size', 0)) > 0]
            self.check("API: Получение позиций", positions is not None,
                      f"Открыто: {len(open_pos)}")
            
            # Проверка тикера
            ticker = await api.get_ticker('BTCUSDT')
            self.check("API: Получение тикера", ticker is not None,
                      f"BTC: ${float(ticker.get('lastPrice', 0)):.2f}" if ticker else "")
            
        except Exception as e:
            self.check("Bybit API", False, str(e))
    
    async def check_trading(self):
        """Проверка торговой системы"""
        print("\n💹 ТОРГОВАЯ СИСТЕМА")
        print("-" * 40)
        
        try:
            async with async_session() as session:
                # Открытые позиции
                result = await session.execute(
                    select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN)
                )
                open_trades = result.scalar()
                self.check("Открытые позиции", open_trades >= 0, f"{open_trades} позиций")
                
                if open_trades > settings.futures_max_open_positions:
                    self.warn(f"Превышен лимит позиций: {open_trades}/{settings.futures_max_open_positions}")
                
                # Закрытые сделки за последние 24 часа
                yesterday = datetime.utcnow() - timedelta(hours=24)
                result = await session.execute(
                    select(func.count(Trade.id)).where(
                        Trade.status == TradeStatus.CLOSED,
                        Trade.exit_time >= yesterday
                    )
                )
                recent_trades = result.scalar()
                self.check("Сделки за 24ч", recent_trades >= 0, f"{recent_trades} сделок")
                
                # PnL
                result = await session.execute(
                    select(func.sum(Trade.pnl)).where(Trade.status == TradeStatus.CLOSED)
                )
                total_pnl = result.scalar() or 0.0
                self.check("Общий PnL", True, f"${total_pnl:.2f}")
                
                if total_pnl < -settings.max_drawdown_pct * settings.futures_virtual_balance / 100:
                    self.warn(f"Превышен max drawdown: ${total_pnl:.2f}")
                
        except Exception as e:
            self.check("Торговая система", False, str(e))
    
    async def check_ml_system(self):
        """Проверка ML системы"""
        print("\n🤖 ML СИСТЕМА")
        print("-" * 40)
        
        try:
            ml = get_ml_predictor()
            
            # Проверка загрузки моделей
            has_models = hasattr(ml, 'models') and len(ml.models) > 0
            self.check("ML модели загружены", has_models,
                      f"{len(ml.models) if has_models else 0} моделей")
            
            # Тестовое предсказание
            try:
                prediction = await ml.predict('BTCUSDT', timeframe='5m')
                self.check("ML предсказание", prediction is not None,
                          f"Signal: {prediction.get('signal', 'N/A')}")
            except Exception as e:
                self.check("ML предсказание", False, str(e))
            
        except Exception as e:
            self.check("ML система", False, str(e))
    
    async def check_news_system(self):
        """Проверка новостной системы"""
        print("\n📰 НОВОСТНАЯ СИСТЕМА")
        print("-" * 40)
        
        try:
            news = get_news_brain()
            
            # Проверка RSS источников
            self.check("News Brain инициализирован", news is not None)
            
            # Получение sentiment
            try:
                sentiment = await news.get_market_sentiment()
                self.check("News sentiment", sentiment is not None,
                          f"Sentiment: {sentiment.value if sentiment else 'N/A'}")
            except Exception as e:
                self.check("News sentiment", False, str(e))
            
            # Проверка статистики
            if hasattr(news, 'stats'):
                calls = news.stats.get('calls', 0)
                errors = news.stats.get('errors', 0)
                self.check("News статистика", errors == 0,
                          f"{calls} вызовов, {errors} ошибок")
            
        except Exception as e:
            self.check("Новостная система", False, str(e))
    
    async def check_logging(self):
        """Проверка системы логирования"""
        print("\n📝 ЛОГИРОВАНИЕ")
        print("-" * 40)
        
        try:
            async with async_session() as session:
                # AI решения за последний час
                hour_ago = datetime.utcnow() - timedelta(hours=1)
                result = await session.execute(
                    select(func.count(AIDecision.id)).where(AIDecision.time >= hour_ago)
                )
                ai_logs = result.scalar()
                self.check("AI логи (1ч)", ai_logs > 0, f"{ai_logs} записей")
                
                # Системные логи
                result = await session.execute(
                    select(func.count(SystemLog.id)).where(SystemLog.time >= hour_ago)
                )
                sys_logs = result.scalar()
                self.check("System логи (1ч)", sys_logs > 0, f"{sys_logs} записей")
                
                # Проверка полноты AI логов
                result = await session.execute(
                    select(AIDecision).order_by(AIDecision.id.desc()).limit(1)
                )
                last_log = result.scalar()
                if last_log:
                    has_data = all([
                        last_log.symbol,
                        last_log.price,
                        last_log.local_decision,
                        last_log.futures_action
                    ])
                    self.check("Полнота AI логов", has_data,
                              f"Последний: {last_log.symbol} {last_log.final_action}")
                
        except Exception as e:
            self.check("Логирование", False, str(e))
    
    async def check_safety(self):
        """Проверка системы защиты"""
        print("\n🛡️ СИСТЕМА ЗАЩИТЫ")
        print("-" * 40)
        
        try:
            async with async_session() as session:
                # Проверка лимитов
                result = await session.execute(
                    select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN)
                )
                open_count = result.scalar()
                
                within_limit = open_count <= settings.futures_max_open_positions
                self.check("Лимит позиций", within_limit,
                          f"{open_count}/{settings.futures_max_open_positions}")
                
                # Проверка SL/TP
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures'
                    )
                )
                trades = result.scalars().all()
                
                has_sl = all(t.stop_loss is not None for t in trades)
                has_tp = all(t.take_profit is not None for t in trades)
                
                self.check("Stop Loss установлен", has_sl or len(trades) == 0,
                          f"{sum(1 for t in trades if t.stop_loss)}/{len(trades)}")
                self.check("Take Profit установлен", has_tp or len(trades) == 0,
                          f"{sum(1 for t in trades if t.take_profit)}/{len(trades)}")
                
                # Проверка drawdown
                result = await session.execute(
                    select(func.sum(Trade.pnl)).where(Trade.status == TradeStatus.CLOSED)
                )
                total_pnl = result.scalar() or 0.0
                
                current_balance = settings.futures_virtual_balance + total_pnl
                drawdown_pct = (total_pnl / settings.futures_virtual_balance) * 100
                
                safe_drawdown = drawdown_pct > -settings.max_drawdown_pct
                self.check("Drawdown в норме", safe_drawdown,
                          f"{drawdown_pct:.2f}% (лимит: -{settings.max_drawdown_pct}%)")
                
        except Exception as e:
            self.check("Система защиты", False, str(e))
    
    async def check_sync(self):
        """Проверка синхронизации"""
        print("\n🔄 СИНХРОНИЗАЦИЯ")
        print("-" * 40)
        
        try:
            # Получаем позиции с биржи
            api = BybitAPI()
            exchange_positions = await api.get_positions()
            exchange_open = {p['symbol']: p for p in exchange_positions if float(p.get('size', 0)) > 0}
            
            # Получаем позиции из БД
            async with async_session() as session:
                result = await session.execute(
                    select(Trade).where(
                        Trade.status == TradeStatus.OPEN,
                        Trade.market_type == 'futures'
                    )
                )
                db_trades = result.scalars().all()
                db_open = {t.symbol: t for t in db_trades}
            
            # Сравниваем
            exchange_symbols = set(exchange_open.keys())
            db_symbols = set(db_open.keys())
            
            synced = exchange_symbols == db_symbols
            self.check("БД синхронизирована с биржей", synced,
                      f"Биржа: {len(exchange_symbols)}, БД: {len(db_symbols)}")
            
            if not synced:
                missing_in_db = exchange_symbols - db_symbols
                missing_on_exchange = db_symbols - exchange_symbols
                
                if missing_in_db:
                    self.warn(f"На бирже, но нет в БД: {missing_in_db}")
                if missing_on_exchange:
                    self.warn(f"В БД, но нет на бирже: {missing_on_exchange}")
            
        except Exception as e:
            self.check("Синхронизация", False, str(e))
    
    def print_summary(self):
        """Вывести итоговый отчёт"""
        print("\n" + "="*80)
        print("📋 ИТОГОВЫЙ ОТЧЁТ")
        print("="*80)
        
        score_pct = (self.results['score'] / self.results['max_score'] * 100) if self.results['max_score'] > 0 else 0
        
        print(f"\n🎯 Оценка: {self.results['score']}/{self.results['max_score']} ({score_pct:.1f}%)")
        
        if score_pct >= 90:
            print("✅ Система работает отлично!")
        elif score_pct >= 70:
            print("⚠️  Система работает, но есть проблемы")
        else:
            print("❌ Система требует внимания!")
        
        if self.results['warnings']:
            print(f"\n⚠️  Предупреждения ({len(self.results['warnings'])}):")
            for warn in self.results['warnings']:
                print(f"   - {warn}")
        
        if self.results['errors']:
            print(f"\n❌ Ошибки ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        print(f"\n🕐 Время проверки: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print("="*80 + "\n")


async def main():
    """Запуск диагностики"""
    diagnostics = SystemDiagnostics()
    await diagnostics.run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
