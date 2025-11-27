"""
Простой Dashboard для Bybit Trading Bot
"""
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

# Конфигурация
st.set_page_config(
    page_title="Bybit Trading Bot",
    page_icon="🤖",
    layout="wide"
)

# Определяем режим
base_url = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com")
is_demo = "demo" in base_url.lower()
mode_badge = "🎮 DEMO" if is_demo else "💰 LIVE"

st.title(f"🤖 Bybit Trading Bot {mode_badge}")

# Подключение к БД
def get_data():
    try:
        conn = psycopg2.connect(
            host="postgres_bybit",
            port=5432,
            database="bybit_trader",
            user="bybit_user",
            password="bybit_secure_pass_2024",
            cursor_factory=RealDictCursor
        )
        cur = conn.cursor()
        
        # Баланс
        cur.execute("SELECT equity, balance_usdt FROM wallet_history ORDER BY time DESC LIMIT 1")
        wallet = cur.fetchone()
        
        # Сделки
        cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins FROM trades WHERE status = 'CLOSED'")
        stats = cur.fetchone()
        
        # Открытые позиции
        cur.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time DESC")
        open_trades = cur.fetchall()
        
        # История
        cur.execute("SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY exit_time DESC LIMIT 20")
        closed_trades = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            'wallet': wallet,
            'stats': stats,
            'open_trades': open_trades,
            'closed_trades': closed_trades
        }
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
        return None

# Получаем данные
data = get_data()

if data:
    wallet = data['wallet']
    stats = data['stats']
    
    # Метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        equity = wallet['equity'] if wallet else 10000.0
        st.metric("💰 Equity", f"${equity:,.2f}")
    
    with col2:
        balance = wallet['balance_usdt'] if wallet else 10000.0
        st.metric("💵 Balance", f"${balance:,.2f}")
    
    with col3:
        total_pnl = equity - 10000.0
        st.metric("📈 Total PnL", f"${total_pnl:+,.2f}")
    
    with col4:
        total = stats['total'] or 0
        wins = stats['wins'] or 0
        winrate = (wins / total * 100) if total > 0 else 0
        st.metric("🎯 Winrate", f"{winrate:.1f}%", f"{total} trades")
    
    st.markdown("---")
    
    # Открытые позиции
    st.subheader("📊 Открытые позиции")
    if data['open_trades']:
        for trade in data['open_trades']:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                side = "🟢 LONG" if trade['side'] == 'BUY' else "🔴 SHORT"
                st.write(f"**{side} {trade['symbol']}**")
            with col2:
                st.write(f"Entry: ${trade['entry_price']:.2f}")
            with col3:
                st.write(f"Qty: {trade['quantity']:.4f}")
    else:
        st.info("Нет открытых позиций")
    
    st.markdown("---")
    
    # История
    st.subheader("📜 История сделок")
    if data['closed_trades']:
        trades_data = []
        for trade in data['closed_trades']:
            trades_data.append({
                'Time': trade['exit_time'].strftime('%Y-%m-%d %H:%M'),
                'Symbol': trade['symbol'],
                'Side': 'LONG' if trade['side'] == 'BUY' else 'SHORT',
                'Entry': f"${trade['entry_price']:.2f}",
                'Exit': f"${trade['exit_price']:.2f}",
                'PnL': f"${trade['pnl']:+.2f}",
                'PnL %': f"{trade['pnl_pct']:+.2f}%"
            })
        
        df = pd.DataFrame(trades_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Пока нет закрытых сделок")
    
    st.caption(f"Обновлено: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
else:
    st.error("⚠️ Не удалось загрузить данные")
