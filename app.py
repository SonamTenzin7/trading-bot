import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.data_loader import BinanceLoader
from src.features import FeatureEngineer
from src.model import SignalModel
from src.trader import Trader
import time

# Page config
st.set_page_config(page_title="Crypto Bot AI", layout="wide")

# Force Primary Color to Green via CSS
st.markdown("""
<style>
    /* 1. Force Green on all Primary Buttons */
    button[kind="primary"], .stButton button[kind="primary"] {
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #45a049 !important;
    }


    /* 3. Handle Sliders (Neutral track, Green handle/progress) */
    
    /* Filled part of the track */
    [data-baseweb="slider"] div[style*="left: 0%"] {
        background-color: #4CAF50 !important;
    }
    
    /* Slider Handle (Knob) */
    [role="slider"] {
        background-color: #4CAF50 !important;
        border: 2px solid #4CAF50 !important;
    }

    /* Unfilled part of the track (Gray) */
    [data-baseweb="slider"] {
        background-color: transparent !important;
    }
    [data-baseweb="slider"] > div > div {
        background-color: #f0f2f6 !important;
    }

    /* 4. Other UI Accents */
    div[data-baseweb="checkbox"] > div:first-child {
        background-color: #4CAF50 !important;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50 !important;
    }
    
    /* Secondary buttons */
    button[kind="secondary"] {
        border-color: #4CAF50 !important;
        color: #4CAF50 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("AI Crypto Trading Bot - High Risk/Reward")

# --- DISCOVERY & WATCHLIST (Main Page) ---
if 'loader' not in st.session_state:
    st.session_state['loader'] = BinanceLoader()
if 'all_symbols' not in st.session_state:
    st.session_state['all_symbols'] = st.session_state['loader'].get_all_symbols()
if 'watchlist' not in st.session_state:
    st.session_state['watchlist'] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

# Top Row: Discovery
col_d1, col_d2 = st.columns(2)
with col_d1:
    with st.expander("🔥 Discover Trending Coins", expanded=False):
        if 'trending_list' not in st.session_state:
            st.session_state['trending_list'] = st.session_state['loader'].get_top_symbols(limit=10)
        
        st.write("Top Volume (24h):")
        for symbol_name in st.session_state['trending_list']:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{symbol_name}**")
            if symbol_name not in st.session_state['watchlist']:
                if c2.button("Add", key=f"main_add_trending_{symbol_name}"):
                    st.session_state['watchlist'].append(symbol_name)
                    st.rerun()
            else:
                c2.write("✅")
        
        if st.button("Refresh Trending",type="primary"):
            st.session_state['trending_list'] = st.session_state['loader'].get_top_symbols(limit=10)
            st.rerun()

with col_d2:
    with st.expander("🔍 Search & Add Any Coin", expanded=False):
        search_selection = st.selectbox(
            "Search Binance Symbols", 
            st.session_state['all_symbols'], 
            key="main_search_box",
            index=None,
            placeholder="Type e.g. PEPE, DOGE..."
        )
        if search_selection and search_selection not in st.session_state['watchlist']:
            if st.button(f"Add {search_selection} to Watchlist", key="main_add_custom"):
                st.session_state['watchlist'].append(search_selection)
                st.success(f"Added {search_selection}!")
                st.rerun()

st.markdown("---")

# Main Settings Section
st.subheader("Analysis & Risk Configuration")
col_c1, col_c2 = st.columns(2)

with col_c1:
    st.markdown("### Market Analysis")
    symbol = st.selectbox("Target Coin for Analysis", st.session_state['watchlist'])
    interval = st.selectbox("Time Interval", ["1h", "4h", "1d", "15m"])
    lookback = st.slider("Training Days Lookback", 10, 365, 30)
    sensitivity = st.slider("Signal Sensitivity (%)", 0.1, 5.0, 0.5) / 100

with col_c2:
    st.markdown("### Risk Management")
    risk_size = st.slider("Position Size (%)", 1, 100, 10) / 100
    sl_pct = st.slider("Stop Loss (%)", 0.5, 10.0, 2.0) / 100
    tp_pct = st.slider("Take Profit (%)", 1.0, 20.0, 5.0) / 100

# Action Button
if st.button("Fetch Data & Run AI Prediction", use_container_width=True, type="primary"):
    with st.spinner(f"Analyzing {symbol}..."):
        loader = st.session_state['loader']
        df = loader.get_data(symbol, interval, lookback)
        
        if df is None or df.empty:
            st.error("Failed to fetch data.")
            st.stop()
        
    with st.spinner("Calculating indicators..."):
        fe = FeatureEngineer()
        df = fe.add_technical_indicators(df)
        df = fe.create_labels(df, threshold=sensitivity)
        df.dropna(inplace=True)
        
    with st.spinner("Generating AI Signals..."):
        try:
            model = SignalModel()
            acc = model.train(df)
            st.session_state['model'] = model
            st.session_state['data'] = df
            st.session_state['accuracy'] = acc
        except ValueError as e:
            st.error(str(e))
            st.stop()

# Sidebar (Minimalist)
import os
import base64

logo_path = "src/image/logo.jpg"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()
    
    st.sidebar.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: flex-start; margin-bottom: 20px; gap: 12px;">
            <img src="data:image/jpeg;base64,{encoded}" 
                 style="width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 2px solid #4CAF50;">
            <div style="display: flex; flex-direction: column; line-height: 1.1;">
                <span style="font-size: 1.8rem; font-weight: 900; color: #4CAF50; letter-spacing: 1px;">GREEN</span>
                <span style="font-size: 0.9rem; font-weight: bold; color: #000000; text-transform: uppercase; opacity: 0.8;">Surge Bolt</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.sidebar.header("Data Management")
if st.sidebar.button("Move data to trash"):
    loader = st.session_state['loader']
    if loader.clear_cache():
        st.sidebar.success("Cache Cleared!")
    else:
        st.sidebar.error("Failed to clear cache.")

# Main Display
if 'data' in st.session_state:
    df = st.session_state['data']
    model = st.session_state['model']
    
    # Run prediction
    df_pred = model.predict(df)
    last_row = df_pred.iloc[-1]
    
    # ADVICE SECTION
    st.markdown("---")
    st.subheader("🤖 AI Advisor Recommendation")
    
    signal = last_row['signal']
    conf = last_row['confidence']
    
    if signal == "BUY":
        color = "green"
        action_text = "BUY NOW"
        advice = "Strong upward momentum detected. Market conditions are favorable."
    elif signal == "SELL":
        color = "red"
        action_text = "SELL / SHORT"
        advice = "Bearish reversal or overbought conditions detected. Consider exiting positions."
    else:
        color = "orange"
        action_text = "HOLD / WAIT"
        advice = "Market is choppy or undecided. No strong signal found."

    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; border: 2px solid {color}; text-align: center; background-color: rgba(0,0,0,0.2);">
        <h2 style="color: {color}; margin:0;">{action_text}</h2>
        <p style="font-size: 1.2em; margin-top: 10px;"><b>Confidence:</b> {conf*100:.1f}%</p>
        <p style="font-style: italic;">"{advice}"</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)

    col1.metric("Current Price", f"${last_row['close']:.2f}")
    col1.metric("RSI", f"{last_row['rsi']:.1f}")
    col2.metric("MACD", f"{last_row['macd']:.2f}")
    
    # Chart
    st.subheader("Price Action & Signals")
    
    # Create valid indices for markers
    buy_signals = df_pred[df_pred['signal'] == 'BUY']
    sell_signals = df_pred[df_pred['signal'] == 'SELL']
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'], name='OHLC'))
    
    # Add simple moving averages
    fig.add_trace(go.Scatter(x=df.index, y=df['sma_20'], line=dict(color='blue', width=1), name='SMA 20'))
    
    # Add Markers
    fig.add_trace(go.Scatter(mode='markers', x=buy_signals.index, y=buy_signals['close'], 
                             marker=dict(symbol='triangle-up', color='green', size=10), name='Buy Signal'))
    fig.add_trace(go.Scatter(mode='markers', x=sell_signals.index, y=sell_signals['close'], 
                             marker=dict(symbol='triangle-down', color='red', size=10), name='Sell Signal'))
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Simulation / Backtest View
    st.subheader("Paper Performance (Backtest)")
    trader = Trader(initial_capital=10000)
    trader.set_risk_params(risk_size, sl_pct, tp_pct)
    
    # Simple loop simulation
    for time, row in df_pred.iterrows():
        trader.execute_trade(row['signal'], symbol, row['close'], time)
        
    final_val = trader.get_portfolio_value({symbol: df_pred.iloc[-1]['close']})
    st.metric("Final Portfolio Value", f"${final_val:.2f}", delta=f"{final_val-10000:.2f}")
    
    if trader.trades:
        st.write("Recent Trades:")
        st.dataframe(pd.DataFrame(trader.trades))
    else:
        st.info("No trades executed in this period based on signals/risk.")

else:
    st.info("Please click 'Fetch Data & Run AI Prediction' above to start.")
