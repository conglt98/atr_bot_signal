"""
Data Pulling Script for BTCUSDT
================================

This script fetches historical OHLCV data from the exchange and saves it
to a CSV file. This allows you to:
- Download data once and reuse it for multiple backtests
- Work offline after initial data download
- Share data files with others
- Avoid rate limits by not fetching repeatedly

Usage
-----
    python pull_data.py

The script will fetch data and save it to 'btcusdt_ohlcv.csv' by default.
You can modify the configuration at the top of the file.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from utils import fetch_historical_ohlcv


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Exchange and symbol configuration
EXCHANGE_ID: str = "binance"  # e.g. "binance" or "bybit"
SYMBOL: str = "BTC/USDT:USDT"  # perpetual futures pair (BTCUSDT.P) recognised by ccxt
TIMEFRAME: str = "1m"          # 1‑minute candles

# Data pulling parameters
LOOKBACK_DAYS: int = 30        # number of days of data to fetch (1 month)
OUTPUT_FILE: str = "data/btcusdt_ohlcv.csv"  # output CSV file name (relative to project root)


# ----------------------------------------------------------------------
# Main data pulling logic
# ----------------------------------------------------------------------

def pull_and_save_data() -> None:
    """
    Fetch historical data and save to CSV file.
    """
    print(f"Fetching {LOOKBACK_DAYS} days of {TIMEFRAME} data for {SYMBOL} from {EXCHANGE_ID}...")
    print("This may take a few minutes depending on the amount of data...")
    
    try:
        # Fetch data
        df = fetch_historical_ohlcv(EXCHANGE_ID, SYMBOL, TIMEFRAME, LOOKBACK_DAYS)
        
        # Sort by datetime
        df = df.sort_values("datetime").reset_index(drop=True)
        
        # Ensure data directory exists
        output_path = Path(OUTPUT_FILE)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(OUTPUT_FILE, index=False)
        
        # Print summary
        print("\n" + "="*60)
        print("Data Pull Summary")
        print("="*60)
        print(f"Total candles: {len(df)}")
        print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"Output file: {OUTPUT_FILE}")
        print(f"File size: {os.path.getsize(OUTPUT_FILE) / 1024:.2f} KB")
        print("="*60)
        print(f"\nData saved successfully to '{OUTPUT_FILE}'")
        print("You can now use this file for backtesting without fetching data again.")
        
    except Exception as e:
        print(f"\nError fetching data: {e}")
        print("Please check your internet connection and exchange configuration.")
        raise


if __name__ == "__main__":  # pragma: no cover
    pull_and_save_data()

