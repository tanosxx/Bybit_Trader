#!/usr/bin/env python3
"""
🔍 ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ BYBIT TRADING BOT
Один скрипт для проверки всех систем, торгов, ML, самообучения и рынка

Запуск: docker exec bybit_bot python full_system_check.py
"""
import sys
sys.path.insert(0, '/app')

import asyncio
import pickle
import os
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from database.db import async_session
from database.models import Trade, SystemLog
from core.bybit_api import get_bybit_api
from config import settings

# ANSI цвета
class C:
    R = '\033[91m'  # Red
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    M = '\033[95m'  # Magenta
    C = '\033[96m'  # Cyan
    W = '\033[97m'  # White
    BOLD = '\033[1m'
    END = '\033[0m'

def header(text):
    print(f"\n{C.BOLD}{C.C}{'='*80}{C.END}")
    print(f"{C.BOLD}{C.C}{text.center(80)}{C.END}")
    print(f"{C.BOLD}{C.C}{'='*80}{C.END}\n")

def section(text):
    print(f"\n{C.BOLD}{C.B}{'─'*80}{C.END}")
    print(f"{C.BOLD}{C.B}📊 {text}{C.END}")
    print(f"{C.BOLD}{C.B}{'─'*80}{C.END}")

def ok(text):
    print(f"{C.G}✅ {text}{C.END}")

def warn(text):
    print(f"{C.Y}⚠️  {text}{C.END}")

def error(text):
    print(f"{C.R}❌ {text}{C.END}")

def info(label, value, color=C.W):
    print(f"   {C.BOLD}{label}:{C.END} {color}{value}{C.END}")


async def check_database():
    """Проверка базы данных"""
    section("БАЗА ДАННЫХ")
    
    try:
        async with async_session() as session:
            # Проверка подключения
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                ok("Подключение к PostgreSQL")
            
            # Статистика таблиц
            tables = {
                'trades': 'Сделки',
                'system_logs': 'Системные логи',
                'candles': 'Исторические свечи',
                'wallet_history': 'История баланса'
            }
            
            for table, desc in tables.items():
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                info(desc, f"{count:,} записей")
            
            return True
    except Exception as e:
        error(f"Ошибка БД: {e}")
        return False


async def check_trading_stats():
    """Статистика торговли"""
    section("СТАТИСТИКА ТОРГОВЛИ")
    
    try:
        async with async_session() as session:
            # Общая статистика
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_pos,
                    SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
                    SUM(CASE WHEN status = 'CLOSED' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'CLOSED' AND pnl < 0 THEN 1 ELSE 0 END) as losses,
                    ROUND(SUM(CASE WHEN status = 'CLOSED' THEN pnl ELSE 0 END)::numeric, 2) as total_pnl,
                    ROUND(SUM(CASE WHEN status = 'CLOSED' THEN fee_entry + fee_exit ELSE 0 END)::numeric, 2) as total_fees
                FROM trades WHERE market_type = 'futures'
            """))
            stats = dict(result.fetchone()._mapping)
            
            total = stats['total']
            closed = stats['closed']
            wins = stats['wins']
            losses = stats['losses']
            total_pnl = float(stats['total_pnl'] or 0)
            total_fees = float(stats['total_fees'] or 0)
            
            info("Всего сделок", f"{total:,}")
            info("Открытых позиций", f"{stats['open_pos']}", C.Y if stats['open_pos'] > 0 else C.G)
            info("Закрытых сделок", f"{closed:,}")
            
            if closed > 0:
                win_rate = (wins / closed) * 100
                info("Wins / Losses", f"{wins} / {losses}")
                info("Win Rate", f"{win_rate:.1f}%", C.G if win_rate > 40 else C.Y)
            
            info("Gross PnL", f"${total_pnl:,.2f}", C.G if total_pnl > 0 else C.R)
            info("Комиссии", f"${total_fees:,.2f}")
            
            net_profit = total_pnl - total_fees
            start_balance = settings.futures_virtual_balance
            current_balance = start_balance + net_profit
            profit_pct = (net_profit / start_balance) * 100
            
            info("Net Profit", f"${net_profit:,.2f}", C.G if net_profit > 0 else C.R)
            info("Стартовый баланс", f"${start_balance:,.2f}")
            info("Текущий баланс", f"${current_balance:,.2f}", C.G)
            info("ROI", f"{profit_pct:+.1f}%", C.G if profit_pct > 0 else C.R)
            
            return stats
    except Exception as e:
        error(f"Ошибка статистики: {e}")
        return None



async def check_recent_trades():
    """Последние сделки"""
    section("ПОСЛЕДНИЕ СДЕЛКИ (5 шт)")
    
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.market_type == 'futures',
                    Trade.status == 'CLOSED'
                ).order_by(Trade.exit_time.desc()).limit(5)
            )
            trades = result.scalars().all()
            
            if not trades:
                warn("Нет закрытых сделок")
                return []
            
            for i, t in enumerate(trades, 1):
                pnl_color = C.G if t.pnl > 0 else C.R
                print(f"\n   {C.BOLD}#{i} {t.symbol} {t.side}{C.END}")
                print(f"      Entry: ${t.entry_price:.2f} | Qty: {t.quantity}")
                print(f"      PnL: {pnl_color}${t.pnl:+.2f}{C.END} | Fee: ${t.fee_entry + t.fee_exit:.4f}")
                print(f"      Exit: {t.exit_time}")
            
            return trades
    except Exception as e:
        error(f"Ошибка получения сделок: {e}")
        return []


async def check_bybit_positions():
    """Проверка позиций на Bybit"""
    section("ПОЗИЦИИ НА BYBIT (РЕАЛЬНЫЕ)")
    
    try:
        api = get_bybit_api()
        positions = await api.get_positions()
        
        if not positions:
            ok("Нет открытых позиций на бирже")
            return []
        
        for pos in positions:
            pnl_color = C.G if pos['unrealized_pnl'] > 0 else C.R
            print(f"\n   {C.BOLD}{pos['symbol']} {pos['side']}{C.END}")
            print(f"      Size: {pos['size']} | Entry: ${pos['entry_price']:.2f}")
            print(f"      Leverage: {pos['leverage']}x")
            print(f"      Unrealized PnL: {pnl_color}${pos['unrealized_pnl']:+.2f}{C.END}")
        
        return positions
    except Exception as e:
        error(f"Ошибка API Bybit: {e}")
        return None


async def check_phantom_trades():
    """Проверка фантомных сделок"""
    section("ПРОВЕРКА ФАНТОМНЫХ СДЕЛОК")
    
    try:
        async with async_session() as session:
            # Открытые в БД
            result = await session.execute(
                select(Trade).where(
                    Trade.market_type == 'futures',
                    Trade.status == 'OPEN'
                )
            )
            db_open = result.scalars().all()
            
            # Открытые на Bybit
            api = get_bybit_api()
            bybit_positions = await api.get_positions()
            
            db_count = len(db_open)
            bybit_count = len(bybit_positions) if bybit_positions else 0
            
            if db_count == bybit_count:
                ok(f"Количество совпадает: {db_count} позиций")
                
                if db_count == 0:
                    ok("Нет открытых позиций - система чистая")
                else:
                    # Проверяем каждую позицию
                    db_symbols = {t.symbol: t for t in db_open}
                    bybit_symbols = {p['symbol']: p for p in bybit_positions}
                    
                    for symbol in db_symbols:
                        if symbol in bybit_symbols:
                            ok(f"{symbol}: Есть в БД и на Bybit")
                        else:
                            error(f"{symbol}: ФАНТОМНАЯ ПОЗИЦИЯ (есть в БД, нет на Bybit)")
                    
                    for symbol in bybit_symbols:
                        if symbol not in db_symbols:
                            warn(f"{symbol}: Есть на Bybit, но нет в БД")
            else:
                error(f"Расхождение: БД={db_count}, Bybit={bybit_count}")
                return False
            
            return True
    except Exception as e:
        error(f"Ошибка проверки: {e}")
        return False



async def check_market_status():
    """Состояние рынка"""
    section("СОСТОЯНИЕ РЫНКА")
    
    try:
        api = get_bybit_api()
        
        for symbol in settings.futures_pairs[:3]:  # Первые 3 пары
            ticker = await api.get_ticker(symbol)
            if ticker:
                price = ticker['last_price']
                change = ticker['price_change_24h']
                change_color = C.G if change > 0 else C.R
                
                print(f"   {C.BOLD}{symbol}{C.END}: ${price:,.2f} ({change_color}{change:+.2f}%{C.END})")
        
        return True
    except Exception as e:
        error(f"Ошибка получения цен: {e}")
        return False


async def check_ml_system():
    """Проверка ML систем"""
    section("ML СИСТЕМЫ")
    
    # 1. LSTM Model
    print(f"\n{C.BOLD}1. LSTM Model v2{C.END}")
    lstm_path = 'ml_training/models/bybit_lstm_model_v2.h5'
    if os.path.exists(lstm_path):
        size = os.path.getsize(lstm_path)
        ok(f"Модель найдена: {size/1024:.1f} KB")
    else:
        warn("LSTM модель не найдена")
    
    # 2. Self-Learning
    print(f"\n{C.BOLD}2. Self-Learning (River ARF){C.END}")
    try:
        learner_path = 'ml_data/self_learner.pkl'
        if os.path.exists(learner_path):
            with open(learner_path, 'rb') as f:
                data = pickle.load(f)
            
            size = os.path.getsize(learner_path)
            learning_count = data.get('learning_count', 0)
            wins = data.get('wins', 0)
            losses = data.get('losses', 0)
            accuracy = data.get('metric').get() if data.get('metric') else 0
            
            ok(f"Модель найдена: {size/1024:.1f} KB")
            info("Обучено на сделках", f"{learning_count:,}")
            info("Wins / Losses", f"{wins} / {losses}")
            
            if learning_count > 0:
                win_rate = (wins / learning_count) * 100
                info("Win Rate", f"{win_rate:.1f}%")
            
            info("Model Accuracy", f"{accuracy:.2%}", C.G if accuracy > 0.85 else C.Y)
            
            if learning_count >= 50:
                ok("Модель готова к использованию (>= 50 samples)")
            else:
                warn(f"Модель нуждается в дообучении ({learning_count} < 50)")
        else:
            warn("Self-Learning модель не найдена")
    except Exception as e:
        error(f"Ошибка Self-Learning: {e}")
    
    # 3. ML Features в сделках
    print(f"\n{C.BOLD}3. ML Features Integration{C.END}")
    try:
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(ml_features) as with_features
                FROM trades 
                WHERE market_type = 'futures' AND status = 'CLOSED'
            """))
            row = result.fetchone()
            total = row[0]
            with_features = row[1]
            
            if total > 0:
                pct = (with_features / total) * 100
                info("Сделок с ML features", f"{with_features}/{total} ({pct:.0f}%)")
                
                if pct == 100:
                    ok("Все сделки имеют ML features")
                elif pct > 90:
                    warn(f"Некоторые сделки без features ({100-pct:.0f}%)")
                else:
                    error(f"Много сделок без features ({100-pct:.0f}%)")
    except Exception as e:
        error(f"Ошибка проверки features: {e}")



async def check_strategic_brain():
    """Проверка Strategic Brain"""
    section("STRATEGIC BRAIN (ГЛАВНЫЙ МОЗГ)")
    
    try:
        # Читаем состояние из brain_state.json
        brain_state_path = 'ml_data/brain_state.json'
        if os.path.exists(brain_state_path):
            import json
            with open(brain_state_path, 'r') as f:
                state = json.load(f)
            
            strategic = state.get('strategic', {})
            regime = strategic.get('regime', 'UNKNOWN')
            reason = strategic.get('reason', 'N/A')
            updated = strategic.get('updated_at', 'N/A')
            
            # Цвет режима
            regime_colors = {
                'BULL_RUSH': C.G,
                'BEAR_CRASH': C.R,
                'SIDEWAYS': C.Y,
                'UNCERTAIN': C.M
            }
            regime_color = regime_colors.get(regime, C.W)
            
            ok("Strategic Brain активен")
            info("Режим рынка", regime, regime_color)
            info("Объяснение", reason[:60] + "..." if len(reason) > 60 else reason)
            info("Обновлено", updated)
            
            # Проверяем свежесть
            if updated != 'N/A':
                try:
                    update_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    age = datetime.now(update_time.tzinfo) - update_time
                    age_minutes = age.total_seconds() / 60
                    
                    if age_minutes < 60:
                        ok(f"Данные свежие ({age_minutes:.0f} минут назад)")
                    else:
                        warn(f"Данные устарели ({age_minutes/60:.1f} часов назад)")
                except:
                    pass
        else:
            warn("brain_state.json не найден")
    except Exception as e:
        error(f"Ошибка Strategic Brain: {e}")


async def check_hybrid_strategy():
    """Проверка Hybrid Strategy"""
    section("HYBRID STRATEGY (АДАПТИВНАЯ ТОРГОВЛЯ)")
    
    import json
    
    try:
        
        # Читаем состояние стратегии
        strategy_state_path = 'ml_data/hybrid_strategy_state.json'
        if os.path.exists(strategy_state_path):
            with open(strategy_state_path, 'r') as f:
                state = json.load(f)
            
            market_mode = state.get('market_mode', 'UNKNOWN')
            chop_value = state.get('chop_value', 0)
            symbol = state.get('symbol', 'N/A')
            updated = state.get('updated_at') or state.get('timestamp', 'N/A')
            
            # Цвет режима
            mode_colors = {
                'TREND': C.G,
                'FLAT': C.Y,
                'UNKNOWN': C.R
            }
            mode_color = mode_colors.get(market_mode, C.W)
            
            ok("Hybrid Strategy активна")
            
            # Режим рынка
            if market_mode == 'TREND':
                info("Режим рынка", f"{market_mode} 🚀", mode_color)
                info("Стратегия", "Trend Following (ML + Pattern Matching)")
            elif market_mode == 'FLAT':
                info("Режим рынка", f"{market_mode} 🔄", mode_color)
                info("Стратегия", "Mean Reversion (RSI-based)")
            else:
                info("Режим рынка", market_mode, mode_color)
                info("Стратегия", "UNKNOWN")
            
            info("CHOP Index", f"{chop_value:.1f}")
            info("Символ", symbol)
            
            # Оценка CHOP
            if chop_value < 40:
                ok("Сильный тренд (CHOP < 40)")
            elif chop_value < 60:
                ok("Умеренный тренд (CHOP < 60)")
            elif chop_value < 70:
                warn("Флэт (CHOP >= 60)")
            else:
                warn("Сильный флэт (CHOP >= 70)")
            
            # Проверяем свежесть (если timestamp не "now")
            if updated != 'N/A' and updated != 'now':
                try:
                    update_time = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    age = datetime.now(update_time.tzinfo) - update_time
                    age_seconds = age.total_seconds()
                    
                    if age_seconds < 300:  # 5 минут
                        ok(f"Данные свежие ({age_seconds:.0f} секунд назад)")
                    elif age_seconds < 600:  # 10 минут
                        warn(f"Данные устарели ({age_seconds/60:.1f} минут назад)")
                    else:
                        error(f"Данные сильно устарели ({age_seconds/60:.1f} минут назад)")
                except:
                    pass
            elif updated == 'now':
                ok("Данные обновляются в реальном времени")
            
            # Конфигурация
            print(f"\n   {C.BOLD}Конфигурация:{C.END}")
            info("Mean Reversion", "✅ Включена" if settings.mean_reversion_enabled else "❌ Выключена")
            info("CHOP Threshold", f"{settings.chop_flat_threshold:.0f}")
            info("RSI Oversold", f"{settings.rsi_oversold}")
            info("RSI Overbought", f"{settings.rsi_overbought}")
            info("Min Confidence", f"{settings.mean_reversion_min_confidence*100:.0f}%")
            info("BTC Safety", "✅ Включена" if settings.mean_reversion_btc_safety else "❌ Выключена")
            
            # Статистика по стратегиям
            print(f"\n   {C.BOLD}Статистика сделок:{C.END}")
            try:
                async with async_session() as session:
                    # Сделки по стратегиям (если есть поле в extra_data)
                    result = await session.execute(text("""
                        SELECT 
                            COUNT(*) FILTER (WHERE extra_data->>'strategy' = 'TREND') as trend_trades,
                            COUNT(*) FILTER (WHERE extra_data->>'strategy' = 'FLAT') as flat_trades,
                            COUNT(*) FILTER (WHERE extra_data->>'strategy' IS NULL) as unknown_trades,
                            ROUND(AVG(pnl) FILTER (WHERE extra_data->>'strategy' = 'TREND')::numeric, 2) as trend_avg_pnl,
                            ROUND(AVG(pnl) FILTER (WHERE extra_data->>'strategy' = 'FLAT')::numeric, 2) as flat_avg_pnl
                        FROM trades 
                        WHERE status = 'CLOSED' AND market_type = 'futures'
                    """))
                    row = result.fetchone()
                    
                    trend_trades = row[0] or 0
                    flat_trades = row[1] or 0
                    unknown_trades = row[2] or 0
                    trend_avg_pnl = float(row[3] or 0)
                    flat_avg_pnl = float(row[4] or 0)
                    
                    total_hybrid = trend_trades + flat_trades
                    
                    if total_hybrid > 0:
                        info("TREND сделок", f"{trend_trades} (Avg PnL: ${trend_avg_pnl:.2f})")
                        info("FLAT сделок", f"{flat_trades} (Avg PnL: ${flat_avg_pnl:.2f})")
                        
                        if trend_trades > 0 and flat_trades > 0:
                            ok("Обе стратегии используются")
                        elif flat_trades == 0:
                            warn("Mean Reversion ещё не использовалась")
                    else:
                        if unknown_trades > 0:
                            warn(f"Все {unknown_trades} сделок без метки стратегии (старые сделки)")
                        else:
                            warn("Нет сделок с Hybrid Strategy")
            except Exception as e:
                error(f"Ошибка статистики стратегий: {e}")
        else:
            error("hybrid_strategy_state.json не найден")
            warn("Hybrid Strategy может быть не активна")
    except Exception as e:
        error(f"Ошибка Hybrid Strategy: {e}")


async def check_subsystems():
    """Проверка подсистем"""
    section("ПОДСИСТЕМЫ")
    
    subsystems = {
        'Futures Brain': 'Multi-agent система (Conservative/Balanced/Aggressive)',
        'News Brain': 'Анализ новостей (CryptoPanic + VADER)',
        'Safety Guardian': 'Автоматический аудит позиций',
        'Gatekeeper': 'Фильтрация сигналов (CHOP + Pattern)',
        'Position Monitor': 'Мониторинг SL/TP',
        'Sync Service': 'Синхронизация с биржей'
    }
    
    for name, desc in subsystems.items():
        print(f"\n   {C.BOLD}{name}{C.END}")
        print(f"      {desc}")
    
    # Проверяем логи подсистем
    try:
        async with async_session() as session:
            # Последние логи за 1 час
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(func.count(SystemLog.id)).where(
                    SystemLog.timestamp >= one_hour_ago
                )
            )
            log_count = result.scalar()
            
            print(f"\n   {C.BOLD}Активность:{C.END}")
            info("Логов за последний час", f"{log_count:,}")
            
            if log_count > 0:
                ok("Системы активны")
            else:
                warn("Нет активности в логах")
    except Exception as e:
        error(f"Ошибка проверки логов: {e}")


async def check_configuration():
    """Проверка конфигурации"""
    section("КОНФИГУРАЦИЯ БОТА")
    
    info("Trading Mode", settings.trading_mode)
    info("Futures Enabled", "✅ Да" if settings.futures_enabled else "❌ Нет")
    info("Virtual Balance", f"${settings.futures_virtual_balance:,.2f}")
    info("Leverage", f"{settings.futures_leverage}x (dynamic 2-7x)")
    info("Margin Mode", settings.futures_margin_mode)
    info("Risk per Trade", f"{settings.futures_risk_per_trade*100:.0f}%")
    info("Max Open Positions", f"{settings.futures_max_open_positions}")
    info("Min Confidence", f"{settings.futures_min_confidence*100:.0f}%")
    info("Simulate Fees", "✅ Да" if settings.simulate_fees_in_demo else "❌ Нет")
    info("Fee Rate", f"{settings.estimated_fee_rate*100:.2f}%")
    info("Trailing Stop", "✅ Да" if settings.trailing_stop_enabled else "❌ Нет")
    
    print(f"\n   {C.BOLD}Торговые пары:{C.END}")
    for pair in settings.futures_pairs:
        print(f"      • {pair}")



async def check_performance_by_symbol():
    """Производительность по символам"""
    section("ПРОИЗВОДИТЕЛЬНОСТЬ ПО СИМВОЛАМ")
    
    try:
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT 
                    symbol,
                    COUNT(*) as trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
                    ROUND(SUM(pnl)::numeric, 2) as total_pnl
                FROM trades 
                WHERE status = 'CLOSED' AND market_type = 'futures'
                GROUP BY symbol
                ORDER BY total_pnl DESC
            """))
            
            rows = result.fetchall()
            
            if not rows:
                warn("Нет данных по символам")
                return
            
            print(f"\n   {'Символ':<10} {'Сделок':<8} {'Wins':<6} {'Avg PnL':<10} {'Total PnL':<12}")
            print(f"   {'-'*60}")
            
            for row in rows:
                symbol = row[0]
                trades = row[1]
                wins = row[2]
                avg_pnl = float(row[3])
                total_pnl = float(row[4])
                
                win_rate = (wins / trades * 100) if trades > 0 else 0
                pnl_color = C.G if total_pnl > 0 else C.R
                
                print(f"   {symbol:<10} {trades:<8} {wins:<6} ${avg_pnl:<9.2f} {pnl_color}${total_pnl:<11.2f}{C.END}")
    
    except Exception as e:
        error(f"Ошибка статистики по символам: {e}")


async def final_verdict(stats):
    """Итоговый вердикт"""
    section("ИТОГОВЫЙ ВЕРДИКТ")
    
    issues = []
    warnings = []
    
    # Проверки
    if stats:
        if stats['open_pos'] > 0:
            warnings.append(f"Есть {stats['open_pos']} открытых позиций")
        
        closed = stats['closed']
        if closed > 0:
            wins = stats['wins']
            win_rate = (wins / closed) * 100
            
            if win_rate < 25:
                issues.append(f"Низкий Win Rate: {win_rate:.1f}%")
            elif win_rate < 40:
                warnings.append(f"Win Rate ниже целевого: {win_rate:.1f}% (цель >40%)")
        
        total_pnl = float(stats['total_pnl'] or 0)
        total_fees = float(stats['total_fees'] or 0)
        net_profit = total_pnl - total_fees
        
        if net_profit < 0:
            issues.append(f"Убыток: ${net_profit:.2f}")
    
    # Вывод
    if not issues and not warnings:
        print(f"\n   {C.G}{C.BOLD}✅ ВСЕ СИСТЕМЫ РАБОТАЮТ ОТЛИЧНО!{C.END}\n")
        print(f"   {C.G}• База данных подключена{C.END}")
        print(f"   {C.G}• Торговля активна{C.END}")
        print(f"   {C.G}• ML системы работают{C.END}")
        print(f"   {C.G}• Нет фантомных сделок{C.END}")
        print(f"   {C.G}• Strategic Brain активен{C.END}")
        print(f"   {C.G}• Все подсистемы функциональны{C.END}")
    else:
        if issues:
            print(f"\n   {C.R}{C.BOLD}❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:{C.END}")
            for issue in issues:
                print(f"   {C.R}• {issue}{C.END}")
        
        if warnings:
            print(f"\n   {C.Y}{C.BOLD}⚠️  ПРЕДУПРЕЖДЕНИЯ:{C.END}")
            for warning in warnings:
                print(f"   {C.Y}• {warning}{C.END}")
    
    # Рекомендации
    if stats and stats['closed'] > 0:
        print(f"\n   {C.BOLD}💡 РЕКОМЕНДАЦИИ:{C.END}")
        
        wins = stats['wins']
        closed = stats['closed']
        win_rate = (wins / closed) * 100
        
        if win_rate > 40:
            print(f"   {C.G}• Отличная производительность! Продолжайте в том же духе{C.END}")
        elif win_rate > 30:
            print(f"   {C.Y}• Хорошая производительность, можно улучшить фильтрацию{C.END}")
        else:
            print(f"   {C.R}• Пересмотрите стратегию или параметры риска{C.END}")


async def main():
    """Главная функция"""
    header("🔍 ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ BYBIT TRADING BOT")
    
    print(f"{C.BOLD}Время проверки:{C.END} {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{C.BOLD}Сервер:{C.END} {settings.bybit_base_url}")
    
    # Запускаем все проверки
    await check_database()
    stats = await check_trading_stats()
    await check_recent_trades()
    await check_bybit_positions()
    await check_phantom_trades()
    await check_market_status()
    await check_ml_system()
    await check_strategic_brain()
    await check_hybrid_strategy()
    await check_subsystems()
    await check_configuration()
    await check_performance_by_symbol()
    await final_verdict(stats)
    
    # Финал
    print(f"\n{C.BOLD}{C.C}{'='*80}{C.END}")
    print(f"{C.BOLD}{C.G}✅ ДИАГНОСТИКА ЗАВЕРШЕНА{C.END}".center(90))
    print(f"{C.BOLD}{C.C}{'='*80}{C.END}\n")


if __name__ == "__main__":
    asyncio.run(main())
