"""
Flask Dashboard для Bybit Trading Bot v2.0 - Simple Profit Edition

Упрощённый dashboard без ML/AI компонентов
Показывает только суть: баланс, позиции, сделки, RSI/BB
"""
from flask import Flask, render_template, jsonify
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, select, desc, func
from sqlalchemy.orm import sessionmaker
from database.models import Trade, TradeStatus, TradeSide
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Синхронный engine для Flask
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://bybit_user:bybit_secure_pass_2024@postgres_bybit:5432/bybit_trader')
# Меняем asyncpg на psycopg2
SYNC_DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


# ========== HELPER FUNCTIONS ==========

def get_balance_from_db():
    """Получить баланс из БД"""
    try:
        with SessionLocal() as session:
            # Стартовый баланс
            initial_balance = 100.0
            
            # Считаем PnL из закрытых сделок
            result = session.execute(
                select(
                    func.sum(Trade.pnl).label('total_pnl'),
                    func.sum(Trade.fee_entry + Trade.fee_exit).label('total_fees'),
                    func.count(Trade.id).label('total_trades')
                ).where(
                    Trade.status == TradeStatus.CLOSED,
                    Trade.market_type == 'futures'
                )
            )
            row = result.first()
            total_pnl = float(row.total_pnl or 0)
            total_fees = float(row.total_fees or 0)
            total_trades = int(row.total_trades or 0)
            
            # Текущий баланс = стартовый + PnL - комиссии
            current_balance = initial_balance + total_pnl - total_fees
            pnl = current_balance - initial_balance
            pnl_pct = (pnl / initial_balance * 100) if initial_balance > 0 else 0
            
            # Win rate
            wins_result = session.execute(
                select(func.count(Trade.id)).where(
                    Trade.status == TradeStatus.CLOSED,
                    Trade.market_type == 'futures',
                    Trade.pnl > 0
                )
            )
            wins = wins_result.scalar() or 0
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'initial': initial_balance,
                'current': current_balance,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'total_trades': total_trades,
                'wins': wins,
                'losses': total_trades - wins,
                'win_rate': win_rate
            }
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
        return {
            'initial': 100.0,
            'current': 100.0,
            'pnl': 0,
            'pnl_pct': 0,
            'total_pnl': 0,
            'total_fees': 0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0
        }


def get_open_positions_from_db():
    """Получить открытые позиции из БД"""
    try:
        with SessionLocal() as session:
            result = session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.OPEN,
                    Trade.market_type == 'futures'
                ).order_by(desc(Trade.entry_time))
            )
            trades = result.scalars().all()
            
            positions = []
            for trade in trades:
                positions.append({
                    'symbol': trade.symbol,
                    'side': trade.side.value,
                    'entry_price': trade.entry_price,
                    'quantity': trade.quantity,
                    'tp_price': getattr(trade, 'tp_price', None),
                    'sl_price': getattr(trade, 'sl_price', None),
                    'entry_time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else 'N/A'
                })
            
            return positions
    except Exception as e:
        print(f"❌ Error getting positions: {e}")
        return []


def get_recent_trades_from_db(limit=20):
    """Получить последние закрытые сделки"""
    try:
        with SessionLocal() as session:
            result = session.execute(
                select(Trade).where(
                    Trade.status == TradeStatus.CLOSED,
                    Trade.market_type == 'futures'
                ).order_by(desc(Trade.exit_time)).limit(limit)
            )
            trades = result.scalars().all()
            
            trades_list = []
            for trade in trades:
                net_pnl = trade.pnl - (trade.fee_entry + trade.fee_exit)
                trades_list.append({
                    'symbol': trade.symbol,
                    'side': trade.side.value,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'quantity': trade.quantity,
                    'pnl': trade.pnl,
                    'fee_entry': trade.fee_entry,
                    'fee_exit': trade.fee_exit,
                    'net_pnl': net_pnl,
                    'entry_time': trade.entry_time.strftime('%Y-%m-%d %H:%M:%S') if trade.entry_time else 'N/A',
                    'exit_time': trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else 'N/A'
                })
            
            return trades_list
    except Exception as e:
        print(f"❌ Error getting trades: {e}")
        return []


# ========== ROUTES ==========

@app.route('/')
def index():
    """Главная страница - v2.0 Dashboard"""
    return render_template('dashboard_v2_simple.html')


@app.route('/api/data')
def get_data():
    """API для получения всех данных"""
    try:
        balance = get_balance_from_db()
        positions = get_open_positions_from_db()
        trades = get_recent_trades_from_db(20)
        
        return jsonify({
            'balance': balance,
            'positions': positions,
            'trades': trades,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        })
    except Exception as e:
        print(f"❌ Error in /api/data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/balance')
def get_balance_api():
    """API для получения баланса"""
    try:
        balance = get_balance_from_db()
        return jsonify(balance)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions')
def get_positions_api():
    """API для получения открытых позиций"""
    try:
        positions = get_open_positions_from_db()
        return jsonify({'positions': positions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
def get_trades_api():
    """API для получения последних сделок"""
    try:
        trades = get_recent_trades_from_db(50)
        return jsonify({'trades': trades})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
