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
st.title("AI Crypto Trading Bot - High Risk/Reward")

# Sidebar
st.sidebar.header("Configuration")

# Coin Selection Logic
base_coins = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
use_trending = st.sidebar.checkbox("Include Top Trending Coins (by Volume)")

if use_trending:
    with st.spinner("Fetching top coins..."):
        loader = BinanceLoader()
        trending_coins = loader.get_top_symbols(limit=10)
        # Merge and dedup
        coin_options = list(set(base_coins + trending_coins))
else:
    coin_options = base_coins

symbol = st.sidebar.selectbox("Select Coin", coin_options)
interval = st.sidebar.selectbox("Interval", ["1h", "4h", "1d", "15m"])
lookback = st.sidebar.slider("Training Days Lookback", 10, 365, 30)

st.sidebar.header("Risk Management")
risk_size = st.sidebar.slider("Position Size (%)", 1, 100, 10) / 100
sl_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 10.0, 2.0) / 100
tp_pct = st.sidebar.slider("Take Profit (%)", 1.0, 20.0, 5.0) / 100

st.sidebar.header("Data Management")
if st.sidebar.button("Move data to trash"):
    loader = BinanceLoader()
    if loader.clear_cache():
        st.sidebar.success("Cache Cleared!")
    else:
        st.sidebar.error("Failed to clear cache.")

if st.sidebar.button("Fetch Data & Analyze"):
    with st.spinner(f"Analyzing {symbol}..."):
        loader = BinanceLoader()
        df = loader.get_data(symbol, interval, lookback)
        
        if df is None or df.empty:
            st.error("Failed to fetch data.")
            st.stop()
        
        # st.success(f"Fetched {len(df)} candles.") # quiet success
        
    with st.spinner("Calculating indicators..."):
        fe = FeatureEngineer()
        df = fe.add_technical_indicators(df)
        df = fe.create_labels(df)
        df.dropna(inplace=True)
        
    with st.spinner("Generating AI Signals..."):
        model = SignalModel()
        acc = model.train(df)
        st.session_state['model'] = model
        st.session_state['data'] = df
        st.session_state['accuracy'] = acc

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
    st.info("Please Click 'Fetch Data & Train Model' to start.")
