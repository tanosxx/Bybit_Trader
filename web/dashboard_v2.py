"""
Улучшенный Dashboard для Bybit Trading Bot
Показывает реальную активность: сделки, AI решения, ML статистику
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/app')

from database.db import async_session
from database.models import Trade, SystemLog, TradeStatus, TradeSide, LogLevel
from sqlalchemy import select, desc, func
import asyncio

# Конфигурация
st.set_page_config(
    page_title="Bybit Trading Bot - Live",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стили
st.markdown("""
<style>
    .big-metric {
        font-size: 2rem;
        font-weight: bold;
    }
    .positive {
        color: #00ff00;
    }
    .negative {
        color: #ff0000;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Bybit Trading Bot - Live Dashboard")
st.caption(f"🕐 Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Функции для получения данных из БД
async def get_trades_data():
    """Получить все сделки"""
    async with async_session() as session:
        result = await session.execute(
            select(Trade).order_by(desc(Trade.entry_time)).limit(100)
        )
        return result.scalars().all()

async def get_open_trades():
    """Получить открытые сделки"""
    async with async_session() as session:
        result = await session.execute(
            select(Trade).where(Trade.status == TradeStatus.OPEN)
        )
        return result.scalars().all()

async def get_recent_logs(limit=50):
    """Получить последние логи"""
    async with async_session() as session:
        result = await session.execute(
            select(SystemLog).order_by(desc(SystemLog.time)).limit(limit)
        )
        return result.scalars().all()

async def get_statistics():
    """Получить статистику"""
    async with async_session() as session:
        # Всего сделок
        total_result = await session.execute(
            select(func.count(Trade.id)).where(Trade.status != TradeStatus.OPEN)
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
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'total_pnl': float(total_pnl),
            'winrate': (wins / total_trades * 100) if total_trades > 0 else 0
        }

# Получаем данные
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

trades = loop.run_until_complete(get_trades_data())
open_trades = loop.run_until_complete(get_open_trades())
logs = loop.run_until_complete(get_recent_logs())
stats = loop.run_until_complete(get_statistics())

loop.close()

# Метрики
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📊 Всего сделок", stats['total_trades'])

with col2:
    st.metric("✅ Прибыльных", stats['wins'], 
              delta=f"{stats['winrate']:.1f}%" if stats['total_trades'] > 0 else None)

with col3:
    st.metric("❌ Убыточных", stats['losses'])

with col4:
    pnl_color = "normal" if stats['total_pnl'] >= 0 else "inverse"
    st.metric("💰 Общий PnL", f"${stats['total_pnl']:+,.2f}", 
              delta_color=pnl_color)

with col5:
    st.metric("🔓 Открытых", len(open_trades))

st.markdown("---")

# Табы
tab1, tab2, tab3, tab4 = st.tabs(["📈 Открытые позиции", "📜 История сделок", "📊 Графики", "🤖 AI Логи"])

with tab1:
    st.subheader("🔓 Открытые позиции")
    
    if open_trades:
        for trade in open_trades:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
            
            with col1:
                side_emoji = "🟢" if trade.side == TradeSide.BUY else "🔴"
                st.write(f"{side_emoji} **{trade.symbol}** ({trade.side.value})")
            
            with col2:
                st.write(f"Вход: ${trade.entry_price:.2f}")
            
            with col3:
                st.write(f"Кол-во: {trade.quantity:.4f}")
            
            with col4:
                if trade.current_pnl:
                    pnl_emoji = "📈" if trade.current_pnl > 0 else "📉"
                    st.write(f"{pnl_emoji} ${trade.current_pnl:+.2f}")
                else:
                    st.write("—")
            
            with col5:
                st.caption(f"Открыта: {trade.entry_time.strftime('%Y-%m-%d %H:%M')}")
            
            st.markdown("---")
    else:
        st.info("Нет открытых позиций")

with tab2:
    st.subheader("📜 История сделок (последние 50)")
    
    if trades:
        df_trades = pd.DataFrame([{
            'Время': t.entry_time.strftime('%Y-%m-%d %H:%M'),
            'Символ': t.symbol,
            'Сторона': '🟢 BUY' if t.side == TradeSide.BUY else '🔴 SELL',
            'Вход': f"${t.entry_price:.2f}",
            'Выход': f"${t.exit_price:.2f}" if t.exit_price else "—",
            'Кол-во': f"{t.quantity:.4f}",
            'PnL': f"${t.pnl:+.2f}" if t.pnl else "—",
            'Статус': t.status.value,
            'AI Риск': f"{t.ai_risk_score}/10" if t.ai_risk_score else "—"
        } for t in trades[:50]])
        
        st.dataframe(df_trades, use_container_width=True, height=400)
    else:
        st.info("Нет сделок")

with tab3:
    st.subheader("📊 Графики производительности")
    
    if trades and len([t for t in trades if t.pnl is not None]) > 0:
        # График PnL по времени
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED and t.pnl is not None]
        
        if closed_trades:
            df_pnl = pd.DataFrame([{
                'Время': t.exit_time or t.entry_time,
                'PnL': t.pnl,
                'Накопленный PnL': sum([tr.pnl for tr in closed_trades[:i+1]])
            } for i, t in enumerate(closed_trades)])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_pnl['Время'],
                y=df_pnl['Накопленный PnL'],
                mode='lines+markers',
                name='Накопленный PnL',
                line=dict(color='green' if df_pnl['Накопленный PnL'].iloc[-1] > 0 else 'red', width=2)
            ))
            
            fig.update_layout(
                title="Накопленный PnL по времени",
                xaxis_title="Время",
                yaxis_title="PnL ($)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Распределение PnL
            col1, col2 = st.columns(2)
            
            with col1:
                fig2 = px.histogram(
                    df_pnl, 
                    x='PnL',
                    nbins=20,
                    title="Распределение PnL",
                    labels={'PnL': 'PnL ($)'}
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            with col2:
                # Статистика по символам
                symbol_stats = {}
                for t in closed_trades:
                    if t.symbol not in symbol_stats:
                        symbol_stats[t.symbol] = {'pnl': 0, 'count': 0}
                    symbol_stats[t.symbol]['pnl'] += t.pnl
                    symbol_stats[t.symbol]['count'] += 1
                
                df_symbols = pd.DataFrame([
                    {'Символ': symbol, 'PnL': data['pnl'], 'Сделок': data['count']}
                    for symbol, data in symbol_stats.items()
                ])
                
                fig3 = px.bar(
                    df_symbols,
                    x='Символ',
                    y='PnL',
                    title="PnL по символам",
                    color='PnL',
                    color_continuous_scale=['red', 'yellow', 'green']
                )
                st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Недостаточно данных для графиков")

with tab4:
    st.subheader("🤖 AI & ML Логи (последние 50)")
    
    if logs:
        for log in logs:
            level_emoji = {
                LogLevel.INFO: "ℹ️",
                LogLevel.BUY: "🟢",
                LogLevel.SELL: "🔴",
                LogLevel.ERROR: "❌",
                LogLevel.WARNING: "⚠️"
            }.get(log.level, "📝")
            
            with st.expander(f"{level_emoji} [{log.time.strftime('%H:%M:%S')}] {log.component}: {log.message}"):
                if log.extra_data:
                    st.json(log.extra_data)
    else:
        st.info("Нет логов")

# Автообновление
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Настройки")

auto_refresh = st.sidebar.checkbox("🔄 Автообновление", value=True)
if auto_refresh:
    refresh_interval = st.sidebar.slider("Интервал (сек)", 5, 60, 10)
    st.sidebar.caption(f"Обновление каждые {refresh_interval} сек")
    
    import time
    time.sleep(refresh_interval)
    st.rerun()

# Информация
st.sidebar.markdown("---")
st.sidebar.info(f"""
**Статистика:**
- Всего сделок: {stats['total_trades']}
- Winrate: {stats['winrate']:.1f}%
- Total PnL: ${stats['total_pnl']:+,.2f}
- Открытых: {len(open_trades)}
""")
