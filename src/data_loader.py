import pandas as pd
from binance.client import Client
from binance.enums import *
import os
from datetime import datetime
import time

class BinanceLoader:
    def __init__(self, api_key=None, api_secret=None):
        self.client = Client(api_key, api_secret)
        self.cache_dir = "data_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def fetch_data(self, symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1HOUR, limit=1000):
        """
        Fetches historical klines from Binance.
        """
        print(f"Fetching {limit} records for {symbol} at {interval} interval...")
        
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

        # Create DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df.set_index('timestamp', inplace=True)
        
        return df

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

    def get_data(self, symbol="BTCUSDT", interval="1h", lookback_days=30):
        # Convert lookback to limit (approx)
        # 1h = 24 records per day
        limit = lookback_days * 24 
        if interval == '1d':
            limit = lookback_days
        elif interval == '15m':
            limit = lookback_days * 24 * 4

        # Basic filename safe string
        filename = f"{self.cache_dir}/{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Check cache first (simple daily cache)
        # For a real app, we might want fresher data, but for dev/demo caching is good.
        # Here we just fetch fresh for simplicity of "Real-Time" aspect unless explicit offline mode.
        
        df = self.fetch_data(symbol, interval, limit=limit)
        if df is not None:
             df.to_csv(filename)
        return df

    def clear_cache(self):
        """
        Removes all files from the cache directory.
        """
        import shutil
        try:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir)
                return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
        return False
