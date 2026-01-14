import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import BinanceLoader

def test_top_symbols():
    loader = BinanceLoader()
    symbols = loader.get_top_symbols(limit=5)
    print("Top Symbols:", symbols)
    assert len(symbols) == 5
    assert 'BTCUSDT' in symbols or 'ETHUSDT' in symbols # Usually true

if __name__ == "__main__":
    test_top_symbols()
