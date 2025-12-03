"""
Flask Dashboard для Bybit Trading Bot
Получает реальные данные с API + БД
"""
from flask import Flask, render_template, jsonify
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, SystemLog, WalletHistory, TradeStatus, TradeSide, LogLevel
from sqlalchemy import select, desc, func
from core.bybit_api import get_bybit_api
import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)

async def get_real_balance():
    """Получить реальный баланс с API (все активы в USDT эквиваленте)"""
    try:
        from core.bybit_api import BybitAPI
        api = BybitAPI()  # Создаем новый экземпляр для этого event loop
        balances = await api.get_wallet_balance()
        
        result = []
        total_usdt_value = 0
        
        # Начальный депозит (известные значения)
        initial_deposits = {
            'USDC': 50000.0,
            'USDT': 50000.0,
            'BTC': 1.0,
            'ETH': 1.0
        }
        
        if balances:
            for coin, data in balances.items():
                current = float(data['total'])
                
                if current > 0:
                    # Конвертируем в USDT
                    if coin == 'USDT':
                        usdt_value = current
                        current_price = 1.0
                    elif coin == 'USDC':
                        usdt_value = current * 0.9999
                        current_price = 0.9999
                    else:
                        # Получаем текущую цену
                        try:
                            ticker = await api.get_ticker(f"{coin}USDT")
                            if ticker:
                                price_field = ticker.get('lastPrice') or ticker.get('last_price') or ticker.get('price')
                                current_price = float(price_field) if price_field else 0
                                usdt_value = current * current_price
                            else:
                                current_price = 0
                                usdt_value = 0
                        except:
                            current_price = 0
                            usdt_value = 0
                    
                    total_usdt_value += usdt_value
                    
                    # Рассчитываем изменение от начального депозита
                    initial_amount = initial_deposits.get(coin, 0)
                    change_amount = current - initial_amount
                    
                    # Для расчета начального баланса в USDT
                    if coin in initial_deposits:
                        if coin == 'USDT':
                            initial_usdt_value = initial_amount
                        elif coin == 'USDC':
                            initial_usdt_value = initial_amount * 0.9999
                        else:
                            # Для BTC и ETH используем текущую цену (приблизительно)
                            initial_usdt_value = initial_amount * current_price
                    else:
                        initial_usdt_value = 0
                    
                    result.append({
                        'coin': coin,
                        'total': current,
                        'available': float(data.get('available', 0)),
                        'current_price': current_price,
                        'usdt_value': usdt_value,
                        'initial_amount': initial_amount,
                        'change_amount': change_amount,
                        'initial_usdt_value': initial_usdt_value
                    })
        
        # Рассчитываем начальный баланс в USDT
        initial_balance_usdt = sum(item['initial_usdt_value'] for item in result)
        
        # Рассчитываем PnL
        total_pnl = total_usdt_value - initial_balance_usdt
        total_pnl_pct = (total_pnl / initial_balance_usdt) * 100 if initial_balance_usdt > 0 else 0
        
        return {
            'balances': result,
            'total_usdt': total_usdt_value,
            'initial_balance': initial_balance_usdt,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct
        }
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
        import traceback
        traceback.print_exc()
        return {
            'balances': [], 
            'total_usdt': 0,
            'initial_balance': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0
        }

async def get_stats():
    """Получить статистику из БД"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    # Создаем новый engine для текущего event loop
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        # Всего закрытых сделок
        total_result = await session.execute(
            select(func.count(Trade.id)).where(Trade.status == TradeStatus.CLOSED)
        )
        total_trades = total_result.scalar() or 0
        
        # Прибыльные
        wins_result = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.pnl > 0
            )
        )
        wins = wins_result.scalar() or 0
        
        # Убыточные
        losses_result = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.pnl < 0
            )
        )
        losses = losses_result.scalar() or 0
        
        # Общий PnL
        pnl_result = await session.execute(
            select(func.sum(Trade.pnl)).where(Trade.status == TradeStatus.CLOSED)
        )
        total_pnl = pnl_result.scalar() or 0.0
        
        # Открытые
        open_result = await session.execute(
            select(func.count(Trade.id)).where(Trade.status == TradeStatus.OPEN)
        )
        open_trades = open_result.scalar() or 0
        
        # ========== HYBRID STATS (раздельно по market_type) ==========
        # SPOT stats
        spot_total = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'spot'
            )
        )
        spot_wins = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'spot',
                Trade.pnl > 0
            )
        )
        spot_pnl = await session.execute(
            select(func.sum(Trade.pnl)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'spot'
            )
        )
        
        # FUTURES stats - ТОЛЬКО С МОМЕНТА ПОСЛЕДНЕГО ДЕПЛОЯ
        session_start = datetime(2025, 12, 2, 16, 0, 0)  # 2025-12-02 16:00:00 UTC
        
        futures_total = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.entry_time >= session_start  # ФИЛЬТР!
            )
        )
        futures_wins = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.pnl > 0,
                Trade.entry_time >= session_start  # ФИЛЬТР!
            )
        )
        futures_pnl = await session.execute(
            select(func.sum(Trade.pnl)).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures',
                Trade.entry_time >= session_start  # ФИЛЬТР!
            )
        )
        
        spot_total_val = spot_total.scalar() or 0
        spot_wins_val = spot_wins.scalar() or 0
        spot_pnl_val = spot_pnl.scalar() or 0.0
        
        futures_total_val = futures_total.scalar() or 0
        futures_wins_val = futures_wins.scalar() or 0
        futures_pnl_val = futures_pnl.scalar() or 0.0
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'total_pnl': float(total_pnl),
            'winrate': (wins / total_trades * 100) if total_trades > 0 else 0,
            'open_trades': open_trades,
            # Раздельная статистика
            'spot': {
                'total_trades': spot_total_val,
                'wins': spot_wins_val,
                'pnl': float(spot_pnl_val),
                'winrate': (spot_wins_val / spot_total_val * 100) if spot_total_val > 0 else 0
            },
            'futures': {
                'total_trades': futures_total_val,
                'wins': futures_wins_val,
                'pnl': float(futures_pnl_val),
                'winrate': (futures_wins_val / futures_total_val * 100) if futures_total_val > 0 else 0
            }
        }

async def get_open_trades(market_type=None):
    """Получить открытые сделки из БД"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        query = select(Trade).where(Trade.status == TradeStatus.OPEN)
        if market_type:
            query = query.where(Trade.market_type == market_type)
        query = query.order_by(desc(Trade.entry_time))
        
        result = await session.execute(query)
        trades = result.scalars().all()
        
        return [{
            'id': t.id,
            'symbol': t.symbol,
            'side': t.side.value,
            'entry_price': float(t.entry_price),
            'quantity': float(t.quantity),
            'stop_loss': float(t.stop_loss) if t.stop_loss else None,
            'take_profit': float(t.take_profit) if t.take_profit else None,
            'entry_time': t.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'cost': float(t.entry_price * t.quantity),
            'market_type': t.market_type or 'spot'
        } for t in trades]

async def get_recent_trades(limit=20, market_type=None):
    """Получить последние закрытые сделки"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        query = select(Trade).where(Trade.status == TradeStatus.CLOSED)
        # Только сделки с реальным exit_time (исключаем phantom cleanup)
        query = query.where(Trade.exit_time.isnot(None))
        if market_type:
            query = query.where(Trade.market_type == market_type)
            # Для futures исключаем только phantom cleanup и технические ошибки
            if market_type == 'futures':
                from sqlalchemy import and_
                query = query.where(
                    and_(
                        Trade.exit_reason.isnot(None),
                        ~Trade.exit_reason.like('%Phantom%'),
                        ~Trade.exit_reason.like('%not found%'),
                        ~Trade.exit_reason.like('%Coins not found%')
                    )
                )
        query = query.order_by(desc(Trade.exit_time)).limit(limit)
        
        result = await session.execute(query)
        trades = result.scalars().all()
        
        return [{
            'id': t.id,
            'symbol': t.symbol,
            'side': t.side.value,
            'entry_price': float(t.entry_price),
            'exit_price': float(t.exit_price) if t.exit_price else None,
            'quantity': float(t.quantity),
            'pnl': float(t.pnl) if t.pnl else 0,
            'pnl_pct': float(t.pnl_pct) if t.pnl_pct else 0,
            'entry_time': t.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': t.exit_time.strftime('%Y-%m-%d %H:%M:%S') if t.exit_time else None,
            'market_type': t.market_type or 'spot',
            'exit_reason': t.exit_reason
        } for t in trades]

async def get_balance_history(days=7):
    """Получить историю баланса"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(WalletHistory).where(WalletHistory.time >= since).order_by(WalletHistory.time)
        )
        history = result.scalars().all()
        
        return [{
            'time': h.time.strftime('%Y-%m-%d %H:%M:%S'),
            'balance': float(h.balance_usdt),
            'equity': float(h.equity) if h.equity else float(h.balance_usdt),
            'change': float(h.change_amount) if h.change_amount else 0,
            'reason': h.change_reason or ''
        } for h in history]

async def get_recent_logs(limit=50):
    """Получить последние логи"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        result = await session.execute(
            select(SystemLog).order_by(desc(SystemLog.time)).limit(limit)
        )
        logs = result.scalars().all()
        
        return [{
            'time': l.time.strftime('%H:%M:%S'),
            'level': l.level.value,
            'component': l.component,
            'message': l.message
        } for l in logs]

@app.route('/')
def index():
    """Главная страница - FUTURES Dashboard"""
    return render_template('dashboard_futures.html')

@app.route('/futures')
def futures_dashboard():
    """FUTURES Dashboard"""
    return render_template('dashboard_futures.html')

@app.route('/hybrid')
def hybrid_dashboard():
    """Hybrid Dashboard v3"""
    return render_template('dashboard_v3.html')

@app.route('/v2')
def index_v2():
    """Dashboard v2"""
    return render_template('dashboard_v2.html')

@app.route('/v1')
def index_v1():
    """Старый Dashboard v1"""
    return render_template('dashboard.html')

async def get_futures_positions():
    """Получить открытые фьючерсные позиции с Bybit API + количество ордеров из БД"""
    try:
        from core.bybit_api import BybitAPI
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from config import settings
        
        api = BybitAPI()
        positions = await api.get_positions()
        
        # Получаем количество ордеров из БД для каждого символа
        engine = create_async_engine(settings.database_url, echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with session_maker() as session:
            orders_count_result = await session.execute(
                select(Trade.symbol, Trade.side, func.count(Trade.id).label('count'))
                .where(Trade.status == TradeStatus.OPEN, Trade.market_type == 'futures')
                .group_by(Trade.symbol, Trade.side)
            )
            orders_count = {(row.symbol, row.side.value): row.count for row in orders_count_result}
        
        result = []
        for pos in positions:
            size = float(pos.get('size', 0))
            if size > 0:
                # API возвращает entry_price (уже преобразовано в get_positions)
                entry_price = float(pos.get('entry_price', 0))
                side = pos.get('side', 'Buy')
                leverage = pos.get('leverage', '1')
                unrealized_pnl = float(pos.get('unrealized_pnl', 0))
                symbol = pos.get('symbol', '')
                
                # Получаем текущую цену для mark_price
                try:
                    ticker = await api.get_ticker(symbol)
                    if ticker:
                        mark_price = float(ticker.get('lastPrice') or ticker.get('last_price', 0))
                    else:
                        mark_price = entry_price
                except:
                    mark_price = entry_price
                
                # Рассчитываем PnL %
                if entry_price > 0:
                    if side == 'Buy':
                        pnl_pct = ((mark_price - entry_price) / entry_price * 100)
                    else:  # Sell/Short
                        pnl_pct = ((entry_price - mark_price) / entry_price * 100)
                else:
                    pnl_pct = 0
                
                # Получаем количество ордеров из БД
                side_str = 'BUY' if side == 'Buy' else 'SELL'
                orders_in_db = orders_count.get((symbol, side_str), 1)
                
                result.append({
                    'symbol': symbol,
                    'side': 'LONG' if side == 'Buy' else 'SHORT',
                    'size': size,
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'leverage': leverage,
                    'unrealized_pnl': unrealized_pnl,
                    'pnl_pct': pnl_pct,
                    'orders_count': orders_in_db
                })
        return result
    except Exception as e:
        print(f"❌ Error getting futures positions: {e}")
        import traceback
        traceback.print_exc()
        return []

async def get_futures_virtual_balance():
    """Получить виртуальный баланс фьючерсов из БД (по закрытым сделкам) с учётом комиссий"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    initial_balance = settings.futures_virtual_balance  # $100
    
    TAKER_FEE_PCT = 0.055  # 0.055% Bybit taker fee
    
    async with session_maker() as session:
        # Получаем ВСЕ закрытые сделки (без фильтра по дате)
        trades_result = await session.execute(
            select(Trade).where(
                Trade.status == TradeStatus.CLOSED,
                Trade.market_type == 'futures'
            )
        )
        closed_trades = trades_result.scalars().all()
        
        # Открытые позиции
        open_result = await session.execute(
            select(func.count(Trade.id)).where(
                Trade.status == TradeStatus.OPEN,
                Trade.market_type == 'futures'
            )
        )
        open_positions = open_result.scalar() or 0
    
    # Рассчитываем PnL и комиссии ТОЛЬКО из БД
    realized_pnl = 0.0
    total_fees = 0.0
    
    for trade in closed_trades:
        # PnL
        realized_pnl += float(trade.pnl or 0)
        
        # Комиссии - берем только записанные в БД
        entry_fee = float(trade.fee_entry or 0)
        exit_fee = float(trade.fee_exit or 0)
        total_fees += (entry_fee + exit_fee)
    
    trading_fees = total_fees
    
    # Итоговый баланс с учётом комиссий
    current_balance = initial_balance + realized_pnl - total_fees
    pnl_pct = ((current_balance - initial_balance) / initial_balance * 100)
    
    return {
        'initial_balance': initial_balance,
        'current_balance': current_balance,
        'realized_pnl': float(realized_pnl),
        'total_fees': float(total_fees),
        'trading_fees': float(trading_fees),
        'funding_fees': 0.0,  # TODO: логировать отдельно
        'net_pnl': float(realized_pnl - total_fees),
        'pnl_pct': pnl_pct,
        'total_trades': len(closed_trades),
        'open_positions': open_positions,
        'leverage': settings.futures_leverage,
        'risk_per_trade': settings.futures_risk_per_trade * 100
    }

@app.route('/api/futures/positions')
def get_futures_positions_api():
    """API для получения открытых фьючерсных позиций"""
    try:
        positions = asyncio.run(get_futures_positions())
        return jsonify(positions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/futures/trades')
def get_futures_trades_api():
    """API для получения закрытых фьючерсных сделок"""
    try:
        trades = asyncio.run(get_recent_trades(limit=50, market_type='futures'))
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/status')
def get_ml_status_api():
    """API для получения статуса Self-Learning модели"""
    try:
        from core.self_learning import SelfLearner
        # Создаем новый экземпляр чтобы загрузить свежую модель
        learner = SelfLearner()
        stats = learner.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e), 'enabled': False}), 500

@app.route('/api/data')
def get_data():
    """API для получения всех данных"""
    try:
        async def fetch_all_data():
            balance_data = await get_real_balance()
            stats = await get_stats()
            closed_trades = await get_recent_trades()
            open_trades = await get_open_trades()
            balance_history = await get_balance_history()
            logs = await get_recent_logs()
            futures_positions = await get_futures_positions()
            futures_balance = await get_futures_virtual_balance()
            
            # Раздельные сделки
            spot_trades = await get_recent_trades(limit=20, market_type='spot')
            futures_trades = await get_recent_trades(limit=20, market_type='futures')
            
            # Self-Learning статус
            try:
                from core.self_learning import get_self_learner
                learner = get_self_learner()
                ml_status = learner.get_stats()
            except Exception as e:
                ml_status = {'enabled': False, 'error': str(e)}
            
            return {
                'balance': balance_data,
                'stats': stats,
                'closed_trades': closed_trades,
                'open_trades': open_trades,
                'spot_trades': spot_trades,
                'futures_trades': futures_trades,
                'futures_positions': futures_positions,
                'futures_balance': futures_balance,
                'balance_history': balance_history,
                'logs': logs,
                'ml_status': ml_status,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        data = asyncio.run(fetch_all_data())
        return jsonify(data)
    
    except Exception as e:
        print(f"❌ Error in /api/data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
