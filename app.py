import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.data_loader import BinanceLoader
from src.features import FeatureEngineer
from src.model import SignalModel
from src.trader import Trader
import time
import os
import base64

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
    st.session_state['db'] = st.session_state['loader'].db

if 'all_symbols' not in st.session_state:
    st.session_state['all_symbols'] = st.session_state['loader'].get_all_symbols()

if 'watchlist' not in st.session_state:
    saved_watchlist = st.session_state['db'].get_watchlist()
    st.session_state['watchlist'] = saved_watchlist if saved_watchlist else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

# Load saved settings
if 'settings_loaded' not in st.session_state:
    saved_settings = st.session_state['db'].get_settings()
    st.session_state['saved_params'] = saved_settings
    st.session_state['settings_loaded'] = True
else:
    saved_settings = st.session_state['saved_params']

# --- NAVIGATION ---
with st.sidebar:
    # Branding
    logo_path = "src/image/logo.jpg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        st.markdown(
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

    st.header("Navigation")
    page = st.radio("Go to", ["Analysis", "Performance"])
    
    st.markdown("---")
    # st.header("System Status")
    
    # Automatic Self-Healing Connection Check
    if 'db' in st.session_state:
        if st.session_state['db'].check_and_upgrade_connection():
            st.toast("🚀 MySQL Connection Restored!", icon="✅")
            # Refresh data that might have changed since fallback
            st.session_state['watchlist'] = st.session_state['db'].get_watchlist()
            st.session_state['saved_params'] = st.session_state['db'].get_settings()
            st.rerun()

    db_type = st.session_state['db'].connection_type if 'db' in st.session_state else "Unknown"
    binance_connected = st.session_state['loader'].connected
    
    # st.header("Connection Status")
    # c_db, c_api = st.columns(2)
    # with c_db:
    #     st.metric("DB", db_type, delta=None)
    # with c_api:
    #     api_status = "Connected" if binance_connected else "Disconnected"
    #     st.metric("Binance API", api_status, delta=None, delta_color="normal" if binance_connected else "inverse")

    if not binance_connected:
        st.error(f"Binance API is not connected.")
        if st.session_state['loader'].error_message:
            st.warning(f"Error: {st.session_state['loader'].error_message}")
        
        with st.expander("How to fix this?"):
            st.markdown("""
            1. **Check Secrets**: Ensure `BINANCE_API_KEY` and `BINANCE_API_SECRET` are set in Streamlit Secrets.
            2. **Regional Block**: If you are deploying on Streamlit Cloud (US servers), Binance.com may block the connection. Try setting `BINANCE_TLD=us` in your secrets if you have a Binance.US account.
            3. **API Keys**: Make sure your API keys have 'Read' permissions enabled.
            """)
    
    # st.markdown("---")
    st.header("Data Management")
    if st.button("Move data to trash"):
        if st.session_state['loader'].clear_cache():
            st.success("Database cache cleared!")
        else:
            st.error("Failed to clear database cache.")

# --- PAGE: ANALYSIS ---
if page == "Analysis":
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
                        st.session_state['db'].update_watchlist(st.session_state['watchlist'])
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
                if st.button(f"Add {search_selection} to Watchlist", type="primary"):
                    st.session_state['watchlist'].append(search_selection)
                    st.session_state['db'].update_watchlist(st.session_state['watchlist'])
                    st.rerun()

    # Main Settings Section
    st.subheader("Analysis & Risk Configuration")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("### Market Analysis")
        symbol = st.selectbox("Target Coin for Analysis", st.session_state['watchlist'])
        interval = st.selectbox("Time Interval", ["1h", "4h", "1d", "15m"])
        
        # Use saved settings if available
        def_lookback = int(saved_settings.get('lookback', 30))
        def_sensitivity = saved_settings.get('sensitivity', 0.5)
        
        lookback = st.slider("Training Days Lookback", 10, 365, def_lookback)
        sensitivity = st.slider("Signal Sensitivity (%)", 0.1, 5.0, def_sensitivity) / 100
        
        if lookback != def_lookback: st.session_state['db'].save_setting('lookback', lookback)
        if sensitivity * 100 != def_sensitivity: st.session_state['db'].save_setting('sensitivity', sensitivity * 100)

    with col_c2:
        st.markdown("### Risk Management")
        
        def_risk = saved_settings.get('risk_size', 10.0) / 100
        def_sl = saved_settings.get('sl_pct', 2.0) / 100
        def_tp = saved_settings.get('tp_pct', 5.0) / 100
        
        risk_size = st.slider("Position Size (%)", 1, 100, int(def_risk * 100)) / 100
        sl_pct = st.slider("Stop Loss (%)", 0.5, 10.0, def_sl * 100) / 100
        tp_pct = st.slider("Take Profit (%)", 1.0, 20.0, def_tp * 100) / 100
        
        if risk_size * 100 != def_risk * 100: st.session_state['db'].save_setting('risk_size', risk_size * 100)
        if sl_pct * 100 != def_sl * 100: st.session_state['db'].save_setting('sl_pct', sl_pct * 100)
        if tp_pct * 100 != def_tp * 100: st.session_state['db'].save_setting('tp_pct', tp_pct * 100)

    # Action Button
    if st.button("Fetch Data & Run AI Prediction", use_container_width=True, type="primary"):
        with st.spinner(f"Analyzing {symbol}..."):
            loader = st.session_state['loader']
            
            if not loader.connected:
                st.error("Cannot fetch data: Binance API is not connected. See sidebar for details.")
                st.stop()

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
                st.session_state['last_symbol'] = symbol
                st.session_state['last_interval'] = interval
            except ValueError as e:
                st.error(str(e))
                st.stop()

    # Main Display (Analysis Results)
    if 'data' in st.session_state:
        df = st.session_state['data']
        model = st.session_state['model']
        current_symbol = st.session_state.get('last_symbol', symbol)
        current_interval = st.session_state.get('last_interval', interval)
        
        # Run prediction
        df_pred = model.predict(df)
        last_row = df_pred.iloc[-1]
        
        # Log signal to DB
        st.session_state['db'].log_signal(
            symbol=current_symbol,
            signal=last_row['signal'],
            confidence=last_row['confidence'],
            price=last_row['close'],
            interval=current_interval
        )
        
        # ADVICE SECTION
        st.markdown("---")
        st.subheader(f"🤖 AI Advisor Recommendation for {current_symbol}")
        
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
        
        res_col1, res_col2, res_col3 = st.columns(3)

        res_col1.metric("Current Price", f"${last_row['close']:.2f}")
        res_col1.metric("RSI", f"{last_row['rsi']:.1f}")
        res_col2.metric("MACD", f"{last_row['macd']:.2f}")
        
        # Chart
        st.subheader(f"Price Action & Signals: {current_symbol}")
        
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
        trade_count = 0
        wins = 0
        pnl_total = 0.0
        
        for time_idx, row in df_pred.iterrows():
            result = trader.execute_trade(row['signal'], current_symbol, row['close'], time_idx)
            if result:
                trade_count += 1
                pnl_total += result['pnl']
                is_win = result['pnl'] > 0
                if is_win:
                    wins += 1
                # Save each trade result to database
                st.session_state['db'].update_performance(current_symbol, is_win, result['pnl'])
            
        final_val = trader.get_portfolio_value({current_symbol: df_pred.iloc[-1]['close']})
        st.metric("Final Portfolio Value", f"${final_val:.2f}", delta=f"{final_val-10000:.2f}")
        
        if trader.trades:
            st.write("Recent Trades:")
            st.dataframe(pd.DataFrame(trader.trades))
        else:
            st.info("No trades executed in this period based on signals/risk.")

    else:
        st.info("Please click 'Fetch Data & Run AI Prediction' above to start.")

# --- PAGE: PERFORMANCE ---
else:
    st.header("Global Model Performance")
    
    if st.button("Reset Performance Stats"):
        if st.session_state['db'].clear_performance():
            st.success("Performance stats cleared!")
            st.rerun()
        else:
            st.error("Failed to clear stats.")

    perf_df = st.session_state['db'].get_performance()
    if not perf_df.empty:
        st.dataframe(perf_df, use_container_width=True, hide_index=True)
    else:
        st.info("No performance data yet. Run analysis to build stats.")

    st.markdown("---")
    st.header("Signal History Audit")
    # Query last 20 signals from DB
    session = st.session_state['db'].get_session()
    try:
        from src.database import SignalLog
        history = session.query(SignalLog).order_by(SignalLog.timestamp.desc()).limit(20).all()
        if history:
            h_df = pd.DataFrame([{
                'Time': history_log.timestamp.strftime("%Y-%m-%d %H:%M"),
                'Symbol': history_log.symbol,
                'Interval': history_log.interval,
                'Signal': history_log.signal,
                'Price': f"${history_log.price:.4f}",
                'Confidence': f"{history_log.confidence*100:.1f}%"
            } for history_log in history])
            st.dataframe(h_df, use_container_width=True, hide_index=True)
        else:
            st.info("No signal history found in database.")
    finally:
        session.close()
