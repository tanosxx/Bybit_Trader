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
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'total_pnl': float(total_pnl),
            'winrate': (wins / total_trades * 100) if total_trades > 0 else 0,
            'open_trades': open_trades
        }

async def get_open_trades():
    """Получить открытые сделки из БД"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN).order_by(desc(Trade.entry_time))
        )
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
            'cost': float(t.entry_price * t.quantity)
        } for t in trades]

async def get_recent_trades(limit=20):
    """Получить последние закрытые сделки"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from config import settings
    
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED).order_by(desc(Trade.exit_time)).limit(limit)
        )
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
            'exit_time': t.exit_time.strftime('%Y-%m-%d %H:%M:%S') if t.exit_time else None
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
    """Главная страница"""
    return render_template('dashboard.html')

@app.route('/api/data')
def get_data():
    """API для получения всех данных"""
    try:
        # Используем asyncio.run() вместо ручного управления loop
        async def fetch_all_data():
            balance_data = await get_real_balance()
            stats = await get_stats()
            closed_trades = await get_recent_trades()
            balance_history = await get_balance_history()
            logs = await get_recent_logs()
            
            return {
                'balance': balance_data,
                'stats': stats,
                'closed_trades': closed_trades,
                'balance_history': balance_history,
                'logs': logs,
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
