"""
Backtest Script for BTCUSDT Scalping Strategies
================================================

This script performs backtesting on historical data for multiple scalping
strategies. It evaluates EMA crossover, Bollinger Bands + RSI, and MACD
crossover strategies and reports performance metrics.

Usage
-----
    python backtest.py

The script will automatically download historical data and run backtests
on all strategies, then print a performance summary.
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import numpy as _np
import pandas as _pd
from dataclasses import dataclass, field
from typing import List, Optional

from utils import (
    fetch_historical_ohlcv,
    ema,
    rsi,
    bollinger_bands,
)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Exchange and symbol configuration
EXCHANGE_ID: str = "binance"  # e.g. "binance" or "bybit"
SYMBOL: str = "BTC/USDT:USDT"  # perpetual futures pair (BTCUSDT.P) recognised by ccxt
TIMEFRAME: str = "1m"          # 1‑minute candles

# Backtest parameters
LOOKBACK_DAYS: int = 30        # number of days of data to backtest (1 month)
RISK_PER_TRADE: float = 5.0    # risked amount per trade in USD
FEE_PER_TRADE: float = 1.4     # assumed round‑trip trading cost in USD
DATA_FILE: Optional[str] = "btcusdt_ohlcv.csv"  # CSV file to load data from (None to fetch from API)

# Strategy parameters
STOP_PCT: float = 0.0015       # stop loss distance as fraction of price (0.15 %)
RR_EMA: float = 2.0            # reward: risk ratio for EMA crossover strategy
RR_BB: float = 1.5             # reward: risk ratio for Bollinger+RSI strategy
RR_MACD: float = 2.0           # reward: risk ratio for MACD crossover strategy


# ----------------------------------------------------------------------
# Strategy definitions
# ----------------------------------------------------------------------

@dataclass
class Trade:
    entry_time: _pd.Timestamp
    entry_price: float
    exit_time: _pd.Timestamp
    exit_price: float
    direction: str  # "long" or "short"
    quantity: float
    profit: float


@dataclass
class StrategyResult:
    name: str
    trades: List[Trade] = field(default_factory=list)

    @property
    def total_profit(self) -> float:
        return sum(tr.profit for tr in self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for tr in self.trades if tr.profit > 0)
        return wins / len(self.trades)

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for tr in self.trades if tr.profit > 0)

    @property
    def losses(self) -> int:
        return sum(1 for tr in self.trades if tr.profit <= 0)


def backtest_strategy(
    df: _pd.DataFrame,
    signals: _np.ndarray,
    rr: float,
    stop_pct: float,
    name: str,
) -> StrategyResult:
    """
    Execute a backtest given entry signals, reward–risk ratio and stop percentage.

    Parameters
    ----------
    df : pandas.DataFrame
        Market data with at least a ``close`` price column.
    signals : numpy.ndarray
        Array of same length as ``df`` where ``+1`` indicates a long entry,
        ``-1`` indicates a short entry and ``0`` means no action.  Only one
        trade is open at a time; any new signal while a trade is open
        triggers an exit.
    rr : float
        Reward:Risk ratio.  A value of 2.0 means take‑profit distance is
        twice the stop‑loss distance.
    stop_pct : float
        Stop loss distance as a fraction of the entry price.  For
        example, ``0.0015`` means a 0.15 % stop loss.
    name : str
        Name of the strategy for reporting purposes.

    Returns
    -------
    StrategyResult
        Object containing trade details and summary statistics.
    """
    result = StrategyResult(name)
    in_pos = False
    direction: Optional[int] = None
    entry_price: float = 0.0
    entry_time: _pd.Timestamp
    stop: float = 0.0
    tp: float = 0.0
    quantity: float = 0.0
    for i, row in df.iterrows():
        if not in_pos:
            if signals[i] == 1:
                # open long
                direction = 1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price * (1 - stop_pct)
                tp = entry_price * (1 + stop_pct * rr)
                quantity = RISK_PER_TRADE / (entry_price - stop)
                in_pos = True
            elif signals[i] == -1:
                # open short
                direction = -1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price * (1 + stop_pct)
                tp = entry_price * (1 - stop_pct * rr)
                quantity = RISK_PER_TRADE / (stop - entry_price)
                in_pos = True
        else:
            price = row["close"]
            exit_flag = False
            profit = 0.0
            if direction == 1:
                if price <= stop:  # stop hit
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price >= tp:  # take profit
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == -1:  # opposite signal
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
            elif direction == -1:
                if price >= stop:
                    profit = (entry_price - price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price <= tp:
                    profit = (entry_price - price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == 1:
                    profit = (entry_price - price) * quantity - FEE_PER_TRADE
                    exit_flag = True
            if exit_flag:
                result.trades.append(
                    Trade(
                        entry_time=entry_time,
                        entry_price=entry_price,
                        exit_time=row["datetime"],
                        exit_price=price,
                        direction="long" if direction == 1 else "short",
                        quantity=quantity,
                        profit=profit,
                    )
                )
                in_pos = False
                direction = None
                quantity = 0.0
    return result


# ----------------------------------------------------------------------
# Strategy signal generators
# ----------------------------------------------------------------------

def generate_ema_signals(df: _pd.DataFrame) -> _np.ndarray:
    """Generate entry signals for the EMA(9/21) crossover strategy."""
    ema_fast = ema(df["close"], 9)
    ema_slow = ema(df["close"], 21)
    diff = ema_fast - ema_slow
    signals = _np.zeros(len(df), dtype=int)
    prev_diff = diff.iloc[0]
    for i in range(1, len(df)):
        if diff.iloc[i] > 0 and prev_diff <= 0:
            signals[i] = 1
        elif diff.iloc[i] < 0 and prev_diff >= 0:
            signals[i] = -1
        prev_diff = diff.iloc[i]
    return signals


def generate_bollinger_rsi_signals(df: _pd.DataFrame) -> _np.ndarray:
    """Generate entry signals for the Bollinger Bands + RSI strategy."""
    bands = bollinger_bands(df["close"], window=20, n_std=2.0)
    rsi_val = rsi(df["close"], window=14)
    signals = _np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        if df["close"].iloc[i] < bands["lower"].iloc[i] and rsi_val.iloc[i] < 30:
            signals[i] = 1
        elif df["close"].iloc[i] > bands["upper"].iloc[i] and rsi_val.iloc[i] > 70:
            signals[i] = -1
    return signals


def generate_macd_signals(df: _pd.DataFrame) -> _np.ndarray:
    """Generate entry signals for the MACD crossover strategy."""
    macd = ema(df["close"], 12) - ema(df["close"], 26)
    signal = ema(macd, 9)
    diff = macd - signal
    signals = _np.zeros(len(df), dtype=int)
    prev = diff.iloc[0]
    for i in range(1, len(df)):
        if diff.iloc[i] > 0 and prev <= 0:
            signals[i] = 1
        elif diff.iloc[i] < 0 and prev >= 0:
            signals[i] = -1
        prev = diff.iloc[i]
    return signals


# ----------------------------------------------------------------------
# Main backtesting logic
# ----------------------------------------------------------------------

def run_backtest() -> None:
    """
    Retrieve data, generate signals, run the backtests and print results.

    The function fetches ``LOOKBACK_DAYS`` worth of 1‑minute candles for
    the configured symbol and exchange.  Each strategy is then tested
    independently using the same dataset.  Results include total
    profit, win rate, number of trades and the number of winning vs
    losing trades.  Starting capital is not explicitly modelled; you
    could deduct a fixed initial capital (e.g. 100 USD) from the
    reported profit to estimate ending account value.
    """
    # Load data from file or fetch from API
    if DATA_FILE and os.path.exists(DATA_FILE):
        print(f"Loading data from file: {DATA_FILE}")
        data = _pd.read_csv(DATA_FILE)
        data["datetime"] = _pd.to_datetime(data["datetime"])
        data = data.sort_values("datetime").reset_index(drop=True)
        print(f"Loaded {len(data)} candles from file")
        print(f"Date range: {data['datetime'].min()} to {data['datetime'].max()}")
    else:
        print(f"Downloading {LOOKBACK_DAYS} days of {TIMEFRAME} data for {SYMBOL} from {EXCHANGE_ID}...")
        data = fetch_historical_ohlcv(EXCHANGE_ID, SYMBOL, TIMEFRAME, LOOKBACK_DAYS)
        data = data.sort_values("datetime").reset_index(drop=True)
        print(f"Fetched {len(data)} candles")
    
    # Generate signals
    print("Generating signals...")
    ema_signals = generate_ema_signals(data)
    bb_signals = generate_bollinger_rsi_signals(data)
    macd_signals = generate_macd_signals(data)
    
    # Backtest
    print("Running backtests...")
    res_ema = backtest_strategy(data, ema_signals, rr=RR_EMA, stop_pct=STOP_PCT, name="EMA(9,21) Crossover")
    res_bb = backtest_strategy(data, bb_signals, rr=RR_BB, stop_pct=STOP_PCT, name="Bollinger+RSI")
    res_macd = backtest_strategy(data, macd_signals, rr=RR_MACD, stop_pct=STOP_PCT, name="MACD Crossover")
    results = [res_ema, res_bb, res_macd]
    
    # Print results
    print("\n" + "="*60)
    print("Scalping Strategy Backtest Summary")
    print(f"Risk per trade: ${RISK_PER_TRADE}")
    print(f"Period: {LOOKBACK_DAYS} days")
    print("="*60)
    for res in results:
        print(f"\nStrategy: {res.name}")
        print(f"  Trades executed: {res.trade_count}")
        print(f"  Wins: {res.wins}, Losses: {res.losses}, Win rate: {res.win_rate:.2%}")
        print(f"  Total P/L (USD): {res.total_profit:.2f}")
    
    # Determine best strategy
    best = max(results, key=lambda r: r.total_profit)
    print(f"\n{'='*60}")
    print(f"Best performing strategy: {best.name}")
    print(f"Net profit: {best.total_profit:.2f} USD with win rate {best.win_rate:.2%}")
    print("="*60)


if __name__ == "__main__":  # pragma: no cover
    run_backtest()

