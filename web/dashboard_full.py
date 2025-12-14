"""
Полноценный Dashboard для Bybit Trading Bot
- Все балансы с конвертацией в USD
- Графики изменения баланса
- История сделок
- Движение средств
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import asyncio
import os
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/app')

from core.bybit_api import BybitAPI

# Конфигурация
st.set_page_config(
    page_title="Bybit Trading Bot - Full Dashboard",
    page_icon="🤖",
    layout="wide"
)

# Начальный баланс
INITIAL_BALANCES = {
    'USDT': 50000.0,
    'USDC': 50000.0,
    'BTC': 1.0,
    'ETH': 1.0
}

# Определяем режим
base_url = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com")
is_demo = "demo" in base_url.lower()
mode_badge = "🎮 DEMO" if is_demo else "💰 LIVE"

st.title(f"🤖 Bybit Trading Bot - Full Dashboard {mode_badge}")

# Получаем данные с Bybit API
@st.cache_data(ttl=10)
def get_bybit_data():
    """Получить данные с Bybit API"""
    try:
        api = BybitAPI()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Получаем балансы
        balances = loop.run_until_complete(api.get_wallet_balance())
        
        # Получаем текущие цены
        btc_ticker = loop.run_until_complete(api.get_ticker('BTCUSDT'))
        eth_ticker = loop.run_until_complete(api.get_ticker('ETHUSDT'))
        
        # Получаем открытые ордера
        open_orders = loop.run_until_complete(api.get_open_orders())
        
        # Получаем историю сделок
        trade_history = loop.run_until_complete(api.get_trade_history(limit=50))
        
        loop.close()
        
        btc_price = float(btc_ticker['last_price']) if btc_ticker else 87000.0
        eth_price = float(eth_ticker['last_price']) if eth_ticker else 2900.0
        
        return {
            'balances': balances or {},
            'btc_price': btc_price,
            'eth_price': eth_price,
            'open_orders': open_orders or [],
            'trade_history': trade_history or []
        }
    except Exception as e:
        st.error(f"❌ Ошибка: {e}")
        return None

# Получаем данные
data = get_bybit_data()

if data:
    balances = data['balances']
    btc_price = data['btc_price']
    eth_price = data['eth_price']
    open_orders = data['open_orders']
    trade_history = data['trade_history']
    
    # Конвертируем все в USD
    current_balances_usd = {}
    initial_balances_usd = {}
    
    for coin, balance in balances.items():
        amount = balance.get('total', 0.0)
        
        if coin == 'USDT' or coin == 'USDC':
            current_balances_usd[coin] = amount
        elif coin == 'BTC':
            current_balances_usd[coin] = amount * btc_price
        elif coin == 'ETH':
            current_balances_usd[coin] = amount * eth_price
    
    # Начальные балансы в USD
    initial_balances_usd['USDT'] = INITIAL_BALANCES['USDT']
    initial_balances_usd['USDC'] = INITIAL_BALANCES['USDC']
    initial_balances_usd['BTC'] = INITIAL_BALANCES['BTC'] * btc_price
    initial_balances_usd['ETH'] = INITIAL_BALANCES['ETH'] * eth_price
    
    total_current_usd = sum(current_balances_usd.values())
    total_initial_usd = sum(initial_balances_usd.values())
    total_pnl_usd = total_current_usd - total_initial_usd
    pnl_pct = (total_pnl_usd / total_initial_usd * 100) if total_initial_usd > 0 else 0.0
    
    # Метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total Equity", f"${total_current_usd:,.2f}")
    
    with col2:
        st.metric("📊 Initial Balance", f"${total_initial_usd:,.2f}")
    
    with col3:
        delta_color = "normal" if total_pnl_usd >= 0 else "inverse"
        st.metric("📈 Total PnL", f"${total_pnl_usd:+,.2f}", f"{pnl_pct:+.2f}%", delta_color=delta_color)
    
    with col4:
        st.metric("📊 Open Orders", len(open_orders))
    
    st.markdown("---")
    
    # Текущие цены
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**BTC Price:** ${btc_price:,.2f}")
    with col2:
        st.info(f"**ETH Price:** ${eth_price:,.2f}")
    
    st.markdown("---")
    
    # Балансы по монетам
    st.subheader("💼 Балансы по монетам")
    
    balance_data = []
    for coin in ['USDT', 'USDC', 'BTC', 'ETH']:
        if coin in balances:
            balance = balances[coin]
            amount = balance.get('total', 0.0)
            available = balance.get('available', 0.0)
            
            initial_amount = INITIAL_BALANCES.get(coin, 0.0)
            change_amount = amount - initial_amount
            
            if coin == 'USDT' or coin == 'USDC':
                usd_value = amount
                initial_usd = initial_amount
            elif coin == 'BTC':
                usd_value = amount * btc_price
                initial_usd = initial_amount * btc_price
            elif coin == 'ETH':
                usd_value = amount * eth_price
                initial_usd = initial_amount * eth_price
            
            change_usd = usd_value - initial_usd
            change_pct = (change_usd / initial_usd * 100) if initial_usd > 0 else 0.0
            
            balance_data.append({
                'Монета': coin,
                'Начальный': f"{initial_amount:,.8f}",
                'Текущий': f"{amount:,.8f}",
                'Изменение': f"{change_amount:+,.8f}",
                'USD Начальный': f"${initial_usd:,.2f}",
                'USD Текущий': f"${usd_value:,.2f}",
                'USD Изменение': f"${change_usd:+,.2f}",
                'Изменение %': f"{change_pct:+.2f}%"
            })
    
    df_balances = pd.DataFrame(balance_data)
    st.dataframe(df_balances, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # График изменения баланса
    st.subheader("📈 Изменение баланса")
    
    fig = go.Figure()
    
    coins = ['USDT', 'USDC', 'BTC', 'ETH']
    colors = ['#26a69a', '#ef5350', '#ffa726', '#42a5f5']
    
    for i, coin in enumerate(coins):
        if coin in current_balances_usd:
            fig.add_trace(go.Bar(
                name=coin,
                x=['Начальный', 'Текущий'],
                y=[initial_balances_usd.get(coin, 0), current_balances_usd.get(coin, 0)],
                marker_color=colors[i]
            ))
    
    fig.update_layout(
        barmode='group',
        title='Сравнение балансов (USD)',
        yaxis_title='USD',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Открытые ордера
    st.subheader("📊 Открытые ордера")
    
    if open_orders:
        orders_data = []
        for order in open_orders:
            side = order.get('side', '')
            side_emoji = "🟢" if side == 'Buy' else "🔴"
            side_text = "LONG" if side == 'Buy' else "SHORT"
            
            orders_data.append({
                'Тип': f"{side_emoji} {side_text}",
                'Пара': order.get('symbol', ''),
                'Цена': f"${float(order.get('price', 0)):,.2f}",
                'Количество': f"{float(order.get('qty', 0)):,.8f}",
                'Статус': order.get('orderStatus', ''),
                'Время': order.get('createdTime', '')
            })
        
        df_orders = pd.DataFrame(orders_data)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.info("✅ Нет открытых ордеров")
    
    st.markdown("---")
    
    # История сделок
    st.subheader("📜 История сделок (последние 50)")
    
    if trade_history:
        history_data = []
        for trade in trade_history:
            side = trade.get('side', '')
            side_emoji = "🟢" if side == 'Buy' else "🔴"
            
            exec_price = float(trade.get('execPrice', 0))
            exec_qty = float(trade.get('execQty', 0))
            exec_value = float(trade.get('execValue', 0))
            fee = float(trade.get('execFee', 0))
            
            history_data.append({
                'Время': trade.get('execTime', ''),
                'Пара': trade.get('symbol', ''),
                'Тип': f"{side_emoji} {side}",
                'Цена': f"${exec_price:,.2f}",
                'Количество': f"{exec_qty:,.8f}",
                'Сумма': f"${exec_value:,.2f}",
                'Комиссия': f"${fee:,.4f}",
                'ID': trade.get('execId', '')[:10]
            })
        
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.info("Нет истории сделок")
    
    st.markdown("---")
    
    # Детальная информация
    with st.expander("📊 Детальная информация"):
        st.json({
            'Начальный баланс': INITIAL_BALANCES,
            'Текущий баланс': {k: v.get('total', 0) for k, v in balances.items()},
            'Цены': {
                'BTC': btc_price,
                'ETH': eth_price
            },
            'PnL': {
                'USD': total_pnl_usd,
                'Процент': pnl_pct
            }
        })
    
    st.caption(f"Обновлено: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Кнопка обновления
    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()

else:
    st.error("⚠️ Не удалось загрузить данные")
