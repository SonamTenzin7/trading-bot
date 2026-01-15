import pandas as pd
from binance.client import Client
import os
import time
from datetime import datetime, timedelta
from src.database import DatabaseManager

class BinanceLoader:
    def __init__(self, api_key=None, api_secret=None):
        # Load from env if not provided
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.tld = os.getenv("BINANCE_TLD", "com")
        
        self.connected = False
        self.error_message = None
        
        try:
            # Initialize client with optional TLD (e.g., 'us' for binance.us)
            self.client = Client(self.api_key, self.api_secret, tld=self.tld)
            # Test connection with a simple ping
            self.client.ping()
            self.connected = True
        except Exception as e:
            self.connected = False
            self.error_message = str(e)
            print(f"FAILED to initialize Binance Client (TLD: {self.tld}): {e}")
            self.client = None

        self.db = DatabaseManager()

    def get_data(self, symbol: str, interval: str, lookback_days: int) -> pd.DataFrame:
        """
        Fetches historical data from Database or Binance.
        Implements incremental fetching.
        """
        # 1. Check DB for existing data
        df_db = self.db.get_ohlcv(symbol, interval)
        last_ts = self.db.get_last_timestamp(symbol, interval)
        
        start_str = f"{lookback_days} days ago UTC"
        
        # 2. Determine if we have "Enough" data
        # If DB has significantly fewer days than requested, do a full fetch
        has_enough = False
        if not df_db.empty:
            earliest_ts = df_db.index[0]
            days_available = (datetime.utcnow() - earliest_ts).days
            # If we have at least 80% of what was requested, we consider it "Incremental"
            if days_available >= (lookback_days * 0.8):
                has_enough = True
        
        if not has_enough:
            try:
                klines = self.client.get_historical_klines(symbol, interval, start_str)
                df = self._process_candles(klines)
                if not df.empty:
                    self.db.save_ohlcv(symbol, interval, df)
                    return df
            except Exception as e:
                print(f"Error fetching full data: {e}")
                if df_db.empty: return pd.DataFrame()

        # 3. If we have enough but it's old, do incremental update
        if last_ts:
            now = datetime.utcnow()
            # If last candle is older than the interval, fetch more
            fetch_start = last_ts + timedelta(minutes=1) 
            
            if (now - last_ts).total_seconds() > 60: # Simple freshness check
                try:
                    new_candles = self.client.get_historical_klines(symbol, interval, fetch_start.strftime("%d %b, %Y %H:%M:%S"))
                    if new_candles:
                        df_new = self._process_candles(new_candles)
                        self.db.save_ohlcv(symbol, interval, df_new)
                        # Refresh from DB
                        df_db = self.db.get_ohlcv(symbol, interval, limit=2000)
                except Exception as e:
                    print(f"Error fetching incremental data: {e}")
        
        # Return DB data filtered by lookback
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        return df_db[df_db.index >= cutoff]

    def _process_candles(self, klines) -> pd.DataFrame:
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        cols = ['open', 'high', 'low', 'close', 'volume']
        df[cols] = df[cols].astype(float)
        return df[cols]

    def get_top_symbols(self, limit=10, quote_asset="USDT"):
        """
        Fetches top symbols by 24h quote volume.
        """
        try:
            tickers = self.client.get_ticker()
            # Filter for USDT pairs and exclude leveraged tokens (UP/DOWN)
            usdt_pairs = [
                t for t in tickers 
                if t['symbol'].endswith(quote_asset) 
                and "UP" not in t['symbol'] 
                and "DOWN" not in t['symbol']
            ]
            
            # Sort by volume (float)
            usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
            
            return [t['symbol'] for t in usdt_pairs[:limit]]
        except Exception as e:
            print(f"Error fetching top symbols: {e}")
            return ["BTCUSDT", "ETHUSDT", "XRPUSDT"] # Fallback

    def get_all_symbols(self, quote_asset="USDT"):
        """
        Fetches all symbols ending with quote_asset.
        """
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = [
                s['symbol'] for s in exchange_info['symbols']
                if s['symbol'].endswith(quote_asset)
                and s['status'] == 'TRADING'
                and "UP" not in s['symbol']
                and "DOWN" not in s['symbol']
            ]
            symbols.sort()
            return symbols
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return ["BTCUSDT", "ETHUSDT", "XRPUSDT"] # Fallback


    def clear_cache(self):
        """
        Removes all OHLCV data from the database.
        """
        return self.db.clear_ohlcv()
