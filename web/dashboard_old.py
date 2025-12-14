"""
Streamlit Dashboard для Bybit Trading Bot
Современный интерфейс с реальными данными
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import os


# Конфигурация страницы
st.set_page_config(
    page_title="Bybit Trading Bot - AI Crypto Trader",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .position-card {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid;
    }
    .long-position {
        border-left-color: #10b981;
    }
    .short-position {
        border-left-color: #ef4444;
    }
    .profit {
        color: #10b981;
        font-weight: bold;
    }
    .loss {
        color: #ef4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Подключение к БД
def get_db_connection():
    """Подключение к PostgreSQL (создаем новое каждый раз)"""
    try:
        conn = psycopg2.connect(
            host="postgres_bybit",
            port=5432,
            database="bybit_trader",
            user="bybit_user",
            password="bybit_secure_pass_2024",
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        st.error(f"❌ Ошибка подключения к БД: {e}")
        return None


def get_data():
    """Получить данные из БД"""
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cur = conn.cursor()
        
        # Текущий баланс
        cur.execute("""
            SELECT equity, balance_usdt
            FROM wallet_history 
            ORDER BY time DESC 
            LIMIT 1
        """)
        wallet_row = cur.fetchone()
        
        # Вычисляем PnL
        initial_balance = 10000.0  # Из .env
        wallet = {
            'equity': wallet_row['equity'] if wallet_row else initial_balance,
            'available_balance': wallet_row['balance_usdt'] if wallet_row else initial_balance,
            'total_pnl': (wallet_row['equity'] - initial_balance) if wallet_row else 0.0,
            'daily_pnl': 0.0  # Вычислим позже
        }
        
        # Открытые позиции
        cur.execute("""
            SELECT * FROM trades 
            WHERE status = 'OPEN' 
            ORDER BY entry_time DESC
        """)
        open_trades = cur.fetchall()
        
        # Закрытые позиции (последние 100)
        cur.execute("""
            SELECT * FROM trades 
            WHERE status = 'CLOSED' 
            ORDER BY exit_time DESC 
            LIMIT 100
        """)
        closed_trades = cur.fetchall()
        
        # Статистика
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade,
                AVG(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as avg_win,
                AVG(CASE WHEN pnl <= 0 THEN pnl ELSE 0 END) as avg_loss
            FROM trades 
            WHERE status = 'CLOSED'
        """)
        stats = cur.fetchone()
        
        # История баланса (последние 7 дней)
        cur.execute("""
            SELECT time, equity, balance_usdt
            FROM wallet_history 
            WHERE time >= NOW() - INTERVAL '7 days'
            ORDER BY time ASC
        """)
        history = cur.fetchall()
        
        # Статистика по парам
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl
            FROM trades 
            WHERE status = 'CLOSED'
            GROUP BY symbol
            ORDER BY total_pnl DESC
        """)
        pair_stats = cur.fetchall()
        
        # Статистика по AI моделям
        cur.execute("""
            SELECT 
                ai_model,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                AVG(pnl) as avg_pnl,
                AVG(ai_confidence) as avg_confidence
            FROM trades 
            WHERE status = 'CLOSED' AND ai_model IS NOT NULL
            GROUP BY ai_model
            ORDER BY avg_pnl DESC
        """)
        ai_stats = cur.fetchall()
        
        # Последние логи
        cur.execute("""
            SELECT time, level, component, message 
            FROM system_logs 
            ORDER BY time DESC 
            LIMIT 50
        """)
        logs = cur.fetchall()
        
        result = {
            'wallet': wallet,
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'stats': stats,
            'history': history,
            'pair_stats': pair_stats,
            'ai_stats': ai_stats,
            'logs': logs
        }
        
        return result
    
    except Exception as e:
        st.error(f"❌ Ошибка получения данных: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None
    
    finally:
        # Всегда закрываем соединение
        if cur:
            try:
                cur.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


def render_header(data):
    """Рендер заголовка"""
    # Определяем режим
    base_url = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com")
    is_demo = "demo" in base_url.lower()
    
    mode_badge = "🎮 DEMO TRADING" if is_demo else "💰 LIVE TRADING"
    mode_color = "#FFA500" if is_demo else "#10b981"
    
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="color: white; margin: 0; font-size: 2.5em;">🤖 Bybit Trading Bot</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 1.2em;">
                    AI-Powered Crypto Trading • Real-time Analytics
                </p>
            </div>
            <div style="background: {mode_color}; padding: 15px 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <h2 style="color: white; margin: 0; font-size: 1.5em;">{mode_badge}</h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metrics(data):
    """Рендер основных метрик"""
    wallet = data['wallet']
    stats = data['stats']
    
    if not wallet:
        st.warning("⚠️ Нет данных о балансе")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Баланс
    with col1:
        equity = wallet.get('equity', 0.0) or 0.0
        st.metric(
            "💰 Equity",
            f"${equity:.2f}",
            delta=None,
            help="Общая стоимость портфеля"
        )
    
    # Доступный баланс
    with col2:
        available = wallet.get('available_balance', equity) or equity
        st.metric(
            "💵 Доступно",
            f"${available:.2f}",
            delta=None,
            help="Доступно для торговли"
        )
    
    # Общий PnL
    with col3:
        total_pnl = wallet.get('total_pnl', 0.0) or 0.0
        initial_balance = 10000.0
        pnl_pct = (total_pnl / initial_balance * 100) if equity > 0 else 0.0
        st.metric(
            "📈 Total PnL",
            f"${total_pnl:+.2f}",
            delta=f"{pnl_pct:+.1f}%",
            help="Общая прибыль/убыток"
        )
    
    # Дневной PnL
    with col4:
        daily_pnl = wallet.get('daily_pnl', 0.0) or 0.0
        st.metric(
            "📊 Сегодня",
            f"${daily_pnl:+.2f}",
            delta=None,
            help="PnL за сегодня"
        )
    
    # Винрейт
    with col5:
        total_trades = stats.get('total', 0) or 0
        wins = stats.get('wins', 0) or 0
        winrate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        st.metric(
            "🎯 Винрейт",
            f"{winrate:.1f}%",
            delta=f"{total_trades} сделок",
            help="Процент прибыльных сделок"
        )


def render_open_positions(data):
    """Рендер открытых позиций"""
    st.subheader("📊 Открытые позиции")
    
    open_trades = data['open_trades']
    
    if not open_trades:
        st.info("✅ Нет открытых позиций")
        return
    
    for trade in open_trades:
        side = trade['side']
        is_long = side == 'BUY'
        
        side_emoji = "🟢" if is_long else "🔴"
        side_text = "LONG" if is_long else "SHORT"
        card_class = "long-position" if is_long else "short-position"
        
        # Вычисляем текущий PnL (если есть current_price)
        entry_price = trade['entry_price']
        current_price = trade.get('current_price', entry_price)
        quantity = trade['quantity']
        
        if is_long:
            unrealized_pnl = (current_price - entry_price) * quantity
        else:
            unrealized_pnl = (entry_price - current_price) * quantity
        
        pnl_pct = (unrealized_pnl / (entry_price * quantity) * 100) if entry_price > 0 else 0.0
        pnl_class = "profit" if unrealized_pnl > 0 else "loss"
        
        st.markdown(f"""
        <div class="position-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0;">{side_emoji} {trade['symbol']} ({side_text})</h3>
                    <p style="margin: 5px 0; color: #666;">
                        Вход: ${entry_price:.2f} • Количество: {quantity:.4f} • 
                        Открыто: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')}
                    </p>
                </div>
                <div style="text-align: right;">
                    <h3 class="{pnl_class}" style="margin: 0;">${unrealized_pnl:+.2f}</h3>
                    <p style="margin: 5px 0; color: #666;">{pnl_pct:+.2f}%</p>
                </div>
            </div>
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd;">
                <span style="color: #666;">SL: ${trade['stop_loss']:.2f}</span> • 
                <span style="color: #666;">TP: ${trade['take_profit']:.2f}</span> • 
                <span style="color: #666;">AI Risk: {trade['ai_risk_score']}/10</span> • 
                <span style="color: #666;">Confidence: {trade['ai_confidence']*100:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI Reasoning
        if trade.get('ai_reasoning'):
            with st.expander("🤖 AI Analysis"):
                st.write(trade['ai_reasoning'])
                if trade.get('ai_key_factors'):
                    st.write("**Key Factors:**")
                    for factor in trade['ai_key_factors']:
                        st.write(f"• {factor}")


def render_balance_chart(data):
    """Рендер графика баланса"""
    st.subheader("📈 График баланса (7 дней)")
    
    history = data['history']
    
    if not history or len(history) < 2:
        st.info("Недостаточно данных для графика")
        return
    
    df = pd.DataFrame(history)
    
    # График equity
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='#667eea', width=3),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)'
    ))
    
    # Добавляем линию начального баланса
    fig.add_hline(
        y=10000.0,
        line_dash="dash",
        line_color="gray",
        annotation_text="Начальный баланс ($10,000)",
        annotation_position="right"
    )
    
    fig.update_layout(
        template='plotly_white',
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title=None,
        yaxis_title="Баланс (USDT)",
        hovermode='x unified',
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_statistics(data):
    """Рендер детальной статистики"""
    stats = data['stats']
    
    if not stats or stats.get('total', 0) == 0:
        st.info("Пока нет статистики")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Общая статистика")
        
        total = stats['total'] or 0
        wins = stats['wins'] or 0
        losses = stats['losses'] or 0
        winrate = (wins / total * 100) if total > 0 else 0.0
        
        total_pnl = stats['total_pnl'] or 0.0
        avg_pnl = stats['avg_pnl'] or 0.0
        best_trade = stats['best_trade'] or 0.0
        worst_trade = stats['worst_trade'] or 0.0
        
        avg_win = stats.get('avg_win', 0.0) or 0.0
        avg_loss = stats.get('avg_loss', 0.0) or 0.0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        st.markdown(f"""
        **Всего сделок:** {total}  
        **Прибыльных:** {wins} 🟢 ({winrate:.1f}%)  
        **Убыточных:** {losses} 🔴 ({100-winrate:.1f}%)  
        
        ---
        
        **Общий PnL:** ${total_pnl:+.2f}  
        **Средний PnL:** ${avg_pnl:+.2f}  
        **Лучшая сделка:** ${best_trade:+.2f}  
        **Худшая сделка:** ${worst_trade:+.2f}  
        
        ---
        
        **Средний выигрыш:** ${avg_win:.2f}  
        **Средний проигрыш:** ${avg_loss:.2f}  
        **Profit Factor:** {profit_factor:.2f}  
        """)
    
    with col2:
        st.subheader("💹 Статистика по парам")
        
        pair_stats = data['pair_stats']
        
        if pair_stats:
            for pair in pair_stats:
                symbol = pair['symbol']
                trades = pair['trades']
                wins = pair['wins']
                total_pnl = pair['total_pnl']
                winrate = (wins / trades * 100) if trades > 0 else 0.0
                
                pnl_color = "green" if total_pnl > 0 else "red"
                
                st.markdown(f"""
                **{symbol}**  
                Сделок: {trades} • Винрейт: {winrate:.1f}% • 
                PnL: <span style='color:{pnl_color}'>${total_pnl:+.2f}</span>
                """, unsafe_allow_html=True)
                st.markdown("---")


def render_ai_stats(data):
    """Рендер статистики AI моделей"""
    st.subheader("🤖 Статистика AI моделей")
    
    ai_stats = data['ai_stats']
    
    if not ai_stats:
        st.info("Пока нет данных по AI")
        return
    
    for ai in ai_stats:
        model = ai['ai_model'] or "Unknown"
        trades = ai['trades']
        wins = ai['wins']
        avg_pnl = ai['avg_pnl'] or 0.0
        avg_confidence = ai['avg_confidence'] or 0.0
        winrate = (wins / trades * 100) if trades > 0 else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Модель", model)
        
        with col2:
            st.metric("Сделок", trades)
        
        with col3:
            st.metric("Винрейт", f"{winrate:.1f}%")
        
        with col4:
            st.metric("Avg PnL", f"${avg_pnl:+.2f}")
        
        st.progress(avg_confidence, text=f"Средняя уверенность: {avg_confidence*100:.0f}%")
        st.markdown("---")


def render_trade_history(data):
    """Рендер истории сделок"""
    st.subheader("📜 История сделок")
    
    closed_trades = data['closed_trades']
    
    if not closed_trades:
        st.info("Пока нет закрытых сделок")
        return
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_symbol = st.selectbox(
            "Пара",
            ["Все"] + list(set([t['symbol'] for t in closed_trades]))
        )
    
    with col2:
        filter_side = st.selectbox(
            "Тип",
            ["Все", "LONG", "SHORT"]
        )
    
    with col3:
        filter_result = st.selectbox(
            "Результат",
            ["Все", "Прибыль", "Убыток"]
        )
    
    # Применяем фильтры
    filtered_trades = closed_trades
    
    if filter_symbol != "Все":
        filtered_trades = [t for t in filtered_trades if t['symbol'] == filter_symbol]
    
    if filter_side != "Все":
        side_value = "BUY" if filter_side == "LONG" else "SELL"
        filtered_trades = [t for t in filtered_trades if t['side'] == side_value]
    
    if filter_result == "Прибыль":
        filtered_trades = [t for t in filtered_trades if t['pnl'] > 0]
    elif filter_result == "Убыток":
        filtered_trades = [t for t in filtered_trades if t['pnl'] <= 0]
    
    # Таблица
    trades_data = []
    for trade in filtered_trades[:50]:  # Показываем последние 50
        side_text = "LONG" if trade['side'] == 'BUY' else "SHORT"
        side_emoji = "🟢" if trade['side'] == 'BUY' else "🔴"
        
        trades_data.append({
            'Время': trade['exit_time'].strftime('%Y-%m-%d %H:%M'),
            'Пара': f"{side_emoji} {trade['symbol']}",
            'Тип': side_text,
            'Вход': f"${trade['entry_price']:.2f}",
            'Выход': f"${trade['exit_price']:.2f}",
            'Кол-во': f"{trade['quantity']:.4f}",
            'PnL': f"${trade['pnl']:+.2f}",
            'PnL %': f"{trade['pnl_pct']:+.2f}%",
            'Риск': f"{trade['ai_risk_score']}/10",
            'AI': trade.get('ai_model', 'N/A')
        })
    
    df_trades = pd.DataFrame(trades_data)
    
    st.dataframe(
        df_trades,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    st.caption(f"Показано {len(filtered_trades)} из {len(closed_trades)} сделок")


def render_logs(data):
    """Рендер логов"""
    st.subheader("📋 Системные логи")
    
    logs = data['logs']
    
    if not logs:
        st.info("Нет логов")
        return
    
    # Фильтр по уровню
    log_levels = ["Все", "INFO", "WARN", "ERROR", "BUY", "SELL"]
    selected_level = st.selectbox("Уровень", log_levels)
    
    filtered_logs = logs if selected_level == "Все" else [l for l in logs if l['level'] == selected_level]
    
    for log in filtered_logs[:30]:
        level_emoji = {
            'INFO': 'ℹ️',
            'WARN': '⚠️',
            'ERROR': '❌',
            'BUY': '🟢',
            'SELL': '🔴'
        }.get(log['level'], 'ℹ️')
        
        time_str = log['time'].strftime('%H:%M:%S')
        component = log['component']
        message = log['message']
        
        st.caption(f"{level_emoji} **{time_str}** [{component}] {message}")


def main():
    """Главная функция Dashboard"""
    
    # Получаем данные
    data = get_data()
    
    if not data:
        st.error("⚠️ Не удалось загрузить данные")
        st.stop()
    
    # Рендерим компоненты
    render_header(data)
    render_metrics(data)
    
    st.markdown("---")
    
    render_open_positions(data)
    
    st.markdown("---")
    
    render_balance_chart(data)
    
    st.markdown("---")
    
    render_statistics(data)
    
    st.markdown("---")
    
    render_ai_stats(data)
    
    st.markdown("---")
    
    render_trade_history(data)
    
    st.markdown("---")
    
    render_logs(data)
    
    # Футер
    st.markdown("---")
    st.caption(f"🕐 Обновлено: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Автообновление каждые 10 секунд


if __name__ == "__main__":
    main()
