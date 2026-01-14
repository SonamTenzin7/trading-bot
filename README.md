# Binance AI Trading Bot

A high-risk/high-reward cryptocurrency trading bot powered by XGBoost/GradientBoosting and Streamlit.

## Structure
- `app.py`: Main application entry point (Streamlit).
- `src/`: Source code modules.
  - `data_loader.py`: Binance data fetching.
  - `features.py`: Technical indicator calculation.
  - `model.py`: ML model (GradientBoosting).
  - `trader.py`: Trading logic and state.
- `tests/`: Verification and test scripts.
- `data_cache/`: Local cache of downloaded historical data.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage
- Open the Streamlit dashboard in your browser.
- Select a coin and training parameters in the sidebar.
- Click **Fetch Data & Train Model**.
- View real-time signals and backtested performance.
