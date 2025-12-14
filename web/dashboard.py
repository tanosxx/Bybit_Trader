"""
Dashboard для Bybit Trading Bot
Данные НАПРЯМУЮ с Bybit API
"""
import streamlit as st
import pandas as pd
import asyncio
import os
from datetime import datetime
import sys
sys.path.insert(0, '/app')

from core.bybit_api import BybitAPI

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

# Получаем данные с Bybit API
@st.cache_data(ttl=10)
def get_bybit_data():
    """Получить данные напрямую с Bybit API"""
    try:
        api = BybitAPI()
        
        # Запускаем async функции
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Получаем балансы
        balances = loop.run_until_complete(api.get_wallet_balance())
        
        # Получаем открытые ордера
        open_orders = loop.run_until_complete(api.get_open_orders())
        
        loop.close()
        
        return {
            'balances': balances or {},
            'open_orders': open_orders or []
        }
    except Exception as e:
        st.error(f"❌ Ошибка получения данных: {e}")
        return None

# Получаем данные
data = get_bybit_data()

if data:
    balances = data['balances']
    open_orders = data['open_orders']
    
    # Считаем общий equity
    total_equity = 0.0
    total_available = 0.0
    
    for coin, balance in balances.items():
        total_val = balance.get('total', 0.0)
        avail_val = balance.get('available', 0.0)
        
        # Для USDT/USDC считаем напрямую
        if coin in ['USDT', 'USDC']:
            total_equity += total_val
            total_available += avail_val
    
    # Метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total Equity", f"${total_equity:,.2f}")
    
    with col2:
        st.metric("💵 Available", f"${total_available:,.2f}")
    
    with col3:
        initial_balance = 100000.0  # 50k USDT + 50k USDC
        total_pnl = total_equity - initial_balance
        st.metric("📈 Total PnL", f"${total_pnl:+,.2f}")
    
    with col4:
        st.metric("📊 Open Orders", len(open_orders))
    
    st.markdown("---")
    
    # Балансы по монетам
    st.subheader("💼 Балансы по монетам")
    
    balance_data = []
    for coin, balance in balances.items():
        total_val = balance.get('total', 0.0)
        avail_val = balance.get('available', 0.0)
        
        if total_val > 0:
            balance_data.append({
                'Монета': coin,
                'Всего': f"{total_val:,.8f}",
                'Доступно': f"{avail_val:,.8f}",
                'В USD': f"${total_val:,.2f}" if coin in ['USDT', 'USDC'] else '-'
            })
    
    if balance_data:
        df_balances = pd.DataFrame(balance_data)
        st.dataframe(df_balances, use_container_width=True, hide_index=True)
    else:
        st.info("Нет балансов")
    
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
    
    # Информация
    st.subheader("ℹ️ Информация")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Режим:** {mode_badge}  
        **API URL:** {base_url}  
        **Тип аккаунта:** Unified Trading Account
        """)
    
    with col2:
        st.info(f"""
        **Начальный баланс:**  
        - USDT: $50,000  
        - USDC: $50,000  
        - BTC: 1.0  
        - ETH: 1.0
        """)
    
    st.caption(f"Обновлено: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Кнопка обновления
    if st.button("🔄 Обновить данные"):
        st.cache_data.clear()
        st.rerun()

else:
    st.error("⚠️ Не удалось загрузить данные с Bybit API")
    st.info("Проверьте логи: `docker logs bybit_dashboard`")
