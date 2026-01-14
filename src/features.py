import pandas as pd
import ta
import numpy as np

class FeatureEngineer:
    def __init__(self):
        pass

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds RSI, MACD, Bollinger Bands, etc.
        """
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        
        # MACD
        macd = ta.trend.MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        
        # SMA / EMA
        df['sma_20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
        
        # Volume Change
        df['volume_change'] = df['volume'].pct_change()

        # Drop NaN caused by indicators
        # df.dropna(inplace=True) 
        # Don't drop immediately if we are inferencing on latest candle
        return df

    def create_labels(self, df: pd.DataFrame, horizon=1, threshold=0.005):
        """
        Create target labels for training.
        Target: 1 (Buy) if price increases by threshold in 'horizon' steps.
               -1 (Sell) if price decreases by threshold.
                0 (Hold) otherwise.
        """
        # Future close price
        df['future_close'] = df['close'].shift(-horizon)
        df['return'] = (df['future_close'] - df['close']) / df['close']
        
        conditions = [
            (df['return'] > threshold),
            (df['return'] < -threshold)
        ]
        choices = [1, -1] # 1=Buy, -1=Sell
        
        df['target'] = np.select(conditions, choices, default=0)
        return df
