#!/usr/bin/env python3
"""
System Check Script - Bybit Trading Bot
Проверяет все системы, бота и рынок, создаёт отчёт для копирования
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import get_db_manager
from config import settings


# =============================================================================
# ЦВЕТА ДЛЯ ТЕРМИНАЛА
# =============================================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Печатает заголовок секции"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_status(label, status, value=""):
    """Печатает статус с цветом"""
    if status == "OK":
        color = Colors.GREEN
        symbol = "✅"
    elif status == "WARNING":
        color = Colors.YELLOW
        symbol = "⚠️"
    else:
        color = Colors.RED
        symbol = "❌"
    
    print(f"{symbol} {Colors.BOLD}{label}:{Colors.END} {color}{status}{Colors.END} {value}")


# =============================================================================
# ПРОВЕРКИ
# =============================================================================

async def check_database():
    """Проверка подключения к БД"""
    print_header("DATABASE CHECK")
    
    try:
        db = get_db_manager()
        
        # Проверка подключения
        async with db.get_session() as session:
            result = await session.execute("SELECT 1")
            if result:
                print_status("Database Connection", "OK", "PostgreSQL connected")
            
            # Проверка таблиц
            tables = ['trades', 'candles', 'wallet_history', 'ai_decisions', 'system_logs']
            for table in tables:
                result = await session.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                print_status(f"Table '{table}'", "OK", f"{count:,} records")
        
        return True
    except Exception as e:
        print_status("Database Connection", "ERROR", str(e))
        return False


async def check_balance():
    """Проверка баланса"""
    print_header("BALANCE CHECK")
    
    try:
        db = get_db_manager()
        
        async with db.get_session() as session:
            # Futures баланс
            query = """
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                    SUM(CASE WHEN status = 'CLOSED' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'CLOSED' AND pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN status = 'CLOSED' THEN pnl ELSE 0 END) as total_pnl,
                    SUM(CASE WHEN status = 'CLOSED' THEN fee_entry + fee_exit ELSE 0 END) as total_fees
                FROM trades 
                WHERE market_type = 'futures'
            """
            result = await session.execute(query)
            row = result.fetchone()
            
            total_trades = row[0] or 0
            closed_trades = row[1] or 0
            open_trades = row[2] or 0
            wins = row[3] or 0
            losses = row[4] or 0
            total_pnl = float(row[5] or 0)
            total_fees = float(row[6] or 0)
            
            # Расчёт баланса
            starting_balance = 100.0  # Стартовый баланс
            net_pnl = total_pnl - total_fees
            current_balance = starting_balance + net_pnl
            profit_pct = (net_pnl / starting_balance) * 100
            
            # Win Rate
            win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0
            
            print_status("Starting Balance", "OK", f"${starting_balance:.2f}")
            print_status("Current Balance", "OK", f"${current_balance:.2f}")
            print_status("Net PnL", "OK" if net_pnl >= 0 else "WARNING", 
                        f"${net_pnl:+.2f} ({profit_pct:+.2f}%)")
            print_status("Gross PnL", "OK" if total_pnl >= 0 else "WARNING", f"${total_pnl:+.2f}")
            print_status("Total Fees", "OK", f"${total_fees:.2f}")
            print()
            print_status("Total Trades", "OK", f"{total_trades}")
            print_status("Closed Trades", "OK", f"{closed_trades}")
            print_status("Open Positions", "OK" if open_trades == 0 else "WARNING", f"{open_trades}")
            print_status("Wins", "OK", f"{wins}")
            print_status("Losses", "OK", f"{losses}")
            print_status("Win Rate", "OK" if win_rate >= 40 else "WARNING", f"{win_rate:.1f}%")
            
            return {
                'starting_balance': starting_balance,
                'current_balance': current_balance,
                'net_pnl': net_pnl,
                'profit_pct': profit_pct,
                'total_trades': total_trades,
                'open_positions': open_trades,
                'win_rate': win_rate
            }
            
    except Exception as e:
        print_status("Balance Check", "ERROR", str(e))
        return None


async def check_strategic_brain():
    """Проверка Strategic Brain"""
    print_header("STRATEGIC BRAIN CHECK")
    
    try:
        from core.strategic_brain import get_strategic_brain
        
        brain = get_strategic_brain()
        
        # Получаем текущий режим
        regime = brain.get_current_regime()
        
        print_status("Strategic Brain", "OK", "Initialized")
        print_status("Current Regime", "OK", regime)
        print_status("Update Interval", "OK", f"{brain.update_interval_hours}h")
        print_status("Price Trigger", "OK", f"±{brain.price_change_threshold}%")
        
        # Проверяем кэш
        if brain._last_regime:
            print_status("Cache Status", "OK", f"Last update: {brain._last_update_time}")
        else:
            print_status("Cache Status", "WARNING", "No cached data")
        
        return regime
        
    except Exception as e:
        print_status("Strategic Brain", "ERROR", str(e))
        return None


async def check_ml_systems():
    """Проверка ML систем"""
    print_header("ML SYSTEMS CHECK")
    
    try:
        # Проверка LSTM модели
        from pathlib import Path
        lstm_path = Path("ml_training/models/bybit_lstm_model_v2.h5")
        if lstm_path.exists():
            print_status("LSTM Model v2", "OK", f"Found: {lstm_path}")
        else:
            print_status("LSTM Model v2", "WARNING", "File not found")
        
        # Проверка Self-Learning
        learner_path = Path("ml_data/self_learner.pkl")
        if learner_path.exists():
            import pickle
            with open(learner_path, 'rb') as f:
                learner = pickle.load(f)
                n_samples = learner.n_samples_seen_ if hasattr(learner, 'n_samples_seen_') else 0
                print_status("Self-Learning Model", "OK", f"{n_samples:,} samples")
        else:
            print_status("Self-Learning Model", "WARNING", "File not found")
        
        # Проверка Scenario Tester (candles)
        db = get_db_manager()
        async with db.get_session() as session:
            result = await session.execute("SELECT COUNT(*) FROM candles")
            candles_count = result.scalar()
            print_status("Historical Candles", "OK", f"{candles_count:,} records")
        
        return True
        
    except Exception as e:
        print_status("ML Systems", "ERROR", str(e))
        return False


async def check_news_brain():
    """Проверка News Brain"""
    print_header("NEWS BRAIN CHECK")
    
    try:
        from core.news_brain import get_news_aggregator
        
        aggregator = get_news_aggregator()
        
        # Получаем sentiment
        result = await aggregator.get_market_sentiment()
        
        print_status("News Aggregator", "OK", "Initialized")
        print_status("Sentiment Score", "OK", f"{result['sentiment_score']:.4f}")
        print_status("Market Status", "OK", result['status'])
        print_status("News Count", "OK", f"{result['news_count']} articles")
        print_status("Top Headline", "OK", f"{result['top_headline'][:60]}...")
        
        return result
        
    except Exception as e:
        print_status("News Brain", "ERROR", str(e))
        return None


async def check_config():
    """Проверка конфигурации"""
    print_header("CONFIGURATION CHECK")
    
    try:
        print_status("Futures Balance", "OK", f"${settings.futures_virtual_balance:.2f}")
        print_status("Leverage", "OK", f"{settings.futures_leverage}x")
        print_status("Risk per Trade", "OK", f"{settings.futures_risk_per_trade*100:.0f}%")
        print_status("Margin Mode", "OK", settings.futures_margin_mode)
        print()
        print_status("Trading Pairs", "OK", f"{len(settings.futures_pairs)} pairs")
        for pair in settings.futures_pairs:
            print(f"   • {pair}")
        print()
        print_status("Max Open Positions", "OK", f"{settings.futures_max_open_positions}")
        print_status("Max Orders per Symbol", "OK", f"{settings.futures_max_orders_per_symbol}")
        print_status("Min Confidence", "OK", f"{settings.futures_min_confidence*100:.0f}%")
        print()
        print_status("Stop Loss", "OK", f"{settings.stop_loss_pct}%")
        print_status("Take Profit", "OK", f"{settings.take_profit_pct}%")
        print_status("Trailing Stop", "OK", "Enabled" if settings.trailing_stop_enabled else "Disabled")
        print()
        print_status("Fee Rate", "OK", f"{settings.estimated_fee_rate*100:.2f}%")
        print_status("Min Profit Multiplier", "OK", f"{settings.min_profit_threshold_multiplier}x")
        print_status("Simulate Fees", "OK", "Yes" if settings.simulate_fees_in_demo else "No")
        
        return True
        
    except Exception as e:
        print_status("Configuration", "ERROR", str(e))
        return False


async def check_recent_activity():
    """Проверка последней активности"""
    print_header("RECENT ACTIVITY")
    
    try:
        db = get_db_manager()
        
        async with db.get_session() as session:
            # Последние 5 сделок
            query = """
                SELECT symbol, side, entry_price, exit_price, pnl, status, 
                       COALESCE(exit_time, entry_time) as last_time
                FROM trades 
                WHERE market_type = 'futures'
                ORDER BY COALESCE(exit_time, entry_time) DESC 
                LIMIT 5
            """
            result = await session.execute(query)
            trades = result.fetchall()
            
            if trades:
                print(f"{Colors.BOLD}Last 5 Trades:{Colors.END}\n")
                for trade in trades:
                    symbol, side, entry, exit_price, pnl, status, last_time = trade
                    pnl_str = f"${pnl:+.2f}" if pnl else "N/A"
                    color = Colors.GREEN if pnl and pnl > 0 else Colors.RED if pnl and pnl < 0 else Colors.YELLOW
                    print(f"   {symbol:10} {side:5} ${entry:.2f} → ${exit_price or 0:.2f} "
                          f"{color}{pnl_str:>8}{Colors.END} [{status}] {last_time}")
            else:
                print_status("Recent Trades", "WARNING", "No trades found")
            
            # Последние AI решения
            print()
            query = """
                SELECT symbol, decision, confidence, created_at
                FROM ai_decisions 
                ORDER BY created_at DESC 
                LIMIT 5
            """
            result = await session.execute(query)
            decisions = result.fetchall()
            
            if decisions:
                print(f"\n{Colors.BOLD}Last 5 AI Decisions:{Colors.END}\n")
                for decision in decisions:
                    symbol, dec, conf, created = decision
                    print(f"   {symbol:10} {dec:5} {conf*100:5.1f}% {created}")
            
        return True
        
    except Exception as e:
        print_status("Recent Activity", "ERROR", str(e))
        return False


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

async def main():
    """Главная функция проверки"""
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║           BYBIT TRADING BOT - SYSTEM CHECK REPORT                 ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    now = datetime.now(timezone.utc)
    print(f"{Colors.BOLD}Date:{Colors.END} {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{Colors.BOLD}Server:{Colors.END} 88.210.10.145")
    print(f"{Colors.BOLD}Environment:{Colors.END} Demo Trading (Bybit Testnet)")
    
    # Запускаем проверки
    results = {}
    
    results['database'] = await check_database()
    results['balance'] = await check_balance()
    results['strategic_brain'] = await check_strategic_brain()
    results['ml_systems'] = await check_ml_systems()
    results['news_brain'] = await check_news_brain()
    results['config'] = await check_config()
    results['activity'] = await check_recent_activity()
    
    # Итоговый отчёт
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print_status("Total Checks", "OK", f"{passed}/{total} passed")
    
    if results['balance']:
        balance_data = results['balance']
        print()
        print(f"{Colors.BOLD}Key Metrics:{Colors.END}")
        print(f"   Balance: ${balance_data['current_balance']:.2f} ({balance_data['profit_pct']:+.2f}%)")
        print(f"   Open Positions: {balance_data['open_positions']}")
        print(f"   Win Rate: {balance_data['win_rate']:.1f}%")
    
    if results['strategic_brain']:
        print(f"   Strategic Regime: {results['strategic_brain']}")
    
    if results['news_brain']:
        news_data = results['news_brain']
        print(f"   News Sentiment: {news_data['status']} ({news_data['sentiment_score']:.2f})")
    
    # URLs
    print()
    print(f"{Colors.BOLD}URLs:{Colors.END}")
    print(f"   Dashboard: http://88.210.10.145:8585")
    print(f"   Neural HUD: http://88.210.10.145:8585/brain")
    print(f"   Futures: http://88.210.10.145:8585/futures")
    
    # Статус
    print()
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL SYSTEMS OPERATIONAL{Colors.END}")
    elif passed >= total * 0.8:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  SOME WARNINGS DETECTED{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ CRITICAL ISSUES DETECTED{Colors.END}")
    
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Check interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
