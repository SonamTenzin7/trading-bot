import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import BinanceLoader
from src.features import FeatureEngineer
from src.model import SignalModel

def test_pipeline():
    print("Testing Data Loader...")
    loader = BinanceLoader()
    # Use small lookback for speed
    df = loader.get_data("BTCUSDT", "1h", lookback_days=10)
    assert df is not None and not df.empty, "Data loading failed"
    print(f"Data loaded: {df.shape}")

    print("Testing Feature Engineering...")
    fe = FeatureEngineer()
    df = fe.add_technical_indicators(df)
    df = fe.create_labels(df)
    df = df.dropna()
    assert 'rsi' in df.columns, "RSI missing"
    assert 'target' in df.columns, "Target missing"
    print(f"Features created: {df.shape}")

    print("Testing Model Training...")
    model = SignalModel()
    acc = model.train(df)
    assert acc is not None, "Training failed"
    print("Pipeline Verified Successfully.")

if __name__ == "__main__":
    test_pipeline()
    # Clean up dummy cache file if needed, but keeping it is fine.
