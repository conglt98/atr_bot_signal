"""
Optimized Backtest Script for BTCUSDT Scalping Strategies
==========================================================

This script contains optimized versions of scalping strategies with:
- Additional filters (volume, trend, volatility)
- Optimized parameters
- Multi-indicator confirmation
- Better risk management

Usage
-----
    python backtest_optimized.py
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
# Configuration - Import from config.py
# ----------------------------------------------------------------------

from config import (
    # Exchange config
    EXCHANGE_ID,
    SYMBOL,
    TIMEFRAME,
    # Backtest config
    LOOKBACK_DAYS,
    DATA_FILE,
    # Risk management
    RISK_PER_TRADE,
    FEE_PER_TRADE,
    # Strategy parameters
    STOP_PCT,
    RR_EMA,
    RR_BB,
    RR_MACD,
    # ATR Breakout parameters
    ATR_BREAKOUT_MULTIPLIER,
    ATR_SL_MULTIPLIER,
    ATR_TP_RR,
    # Filter parameters
    MIN_VOLUME_MULTIPLIER,
    MIN_ADX,
    MIN_ATR_PCT,
    # RSI parameters
    RSI_LONG_MIN,
    RSI_LONG_MAX,
    RSI_SHORT_MIN,
    RSI_SHORT_MAX,
    # Volume and ADX filters
    VOLUME_MULTIPLIER,
    ADX_THRESHOLD,
)


# ----------------------------------------------------------------------
# Additional indicators
# ----------------------------------------------------------------------

def adx(high: _pd.Series, low: _pd.Series, close: _pd.Series, period: int = 14) -> _pd.Series:
    """
    Calculate Average Directional Index (ADX) to measure trend strength.
    Higher ADX (>25) indicates strong trend.
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Calculate smoothed values
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    
    # Calculate ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx


def atr(high: _pd.Series, low: _pd.Series, close: _pd.Series, period: int = 14) -> _pd.Series:
    """Calculate Average True Range (ATR) for volatility measurement."""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def sma(series: _pd.Series, window: int) -> _pd.Series:
    """Simple Moving Average."""
    return series.rolling(window).mean()


# ----------------------------------------------------------------------
# Strategy definitions (same as original)
# ----------------------------------------------------------------------

@dataclass
class Trade:
    entry_time: _pd.Timestamp
    entry_price: float
    exit_time: _pd.Timestamp
    exit_price: float
    direction: str
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

    @property
    def avg_win(self) -> float:
        wins = [tr.profit for tr in self.trades if tr.profit > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def avg_loss(self) -> float:
        losses = [tr.profit for tr in self.trades if tr.profit <= 0]
        return sum(losses) / len(losses) if losses else 0.0


def backtest_strategy(
    df: _pd.DataFrame,
    signals: _np.ndarray,
    rr: float,
    stop_pct: float,
    name: str,
) -> StrategyResult:
    """Execute backtest with same logic as original."""
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
                direction = 1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price * (1 - stop_pct)
                tp = entry_price * (1 + stop_pct * rr)
                quantity = RISK_PER_TRADE / (entry_price - stop)
                in_pos = True
            elif signals[i] == -1:
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
                if price <= stop:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price >= tp:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == -1:
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
# Optimized strategy signal generators
# ----------------------------------------------------------------------

def generate_ema_signals_optimized(df: _pd.DataFrame) -> _np.ndarray:
    """
    Optimized EMA crossover with filters:
    - Volume filter (only trade when volume > average)
    - ADX filter (only trade in strong trends)
    - ATR filter (only trade when volatility is sufficient)
    """
    # Calculate indicators
    ema_fast = ema(df["close"], 8)   # Optimized: 8 instead of 9
    ema_slow = ema(df["close"], 21)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    atr_pct = atr_val / df["close"]
    
    diff = ema_fast - ema_slow
    signals = _np.zeros(len(df), dtype=int)
    prev_diff = diff.iloc[0] if len(diff) > 0 else 0
    
    for i in range(1, len(df)):
        # Check filters
        volume_ok = df["volume"].iloc[i] >= volume_sma.iloc[i] * MIN_VOLUME_MULTIPLIER
        adx_ok = adx_val.iloc[i] >= MIN_ADX if not _pd.isna(adx_val.iloc[i]) else False
        volatility_ok = atr_pct.iloc[i] >= MIN_ATR_PCT if not _pd.isna(atr_pct.iloc[i]) else False
        
        # Generate signal only if all filters pass
        if volume_ok and adx_ok and volatility_ok:
            if diff.iloc[i] > 0 and prev_diff <= 0:
                signals[i] = 1
            elif diff.iloc[i] < 0 and prev_diff >= 0:
                signals[i] = -1
        
        prev_diff = diff.iloc[i]
    
    return signals


def generate_bollinger_rsi_signals_optimized(df: _pd.DataFrame) -> _np.ndarray:
    """
    Optimized Bollinger + RSI with filters:
    - Volume filter
    - Stricter RSI levels (25/75 instead of 30/70)
    - Price must be closer to bands
    """
    bands = bollinger_bands(df["close"], window=20, n_std=2.0)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    signals = _np.zeros(len(df), dtype=int)
    
    for i in range(len(df)):
        if i < 20:  # Need enough data
            continue
            
        current_price = df["close"].iloc[i]
        lower_band = bands["lower"].iloc[i]
        upper_band = bands["upper"].iloc[i]
        rsi_current = rsi_val.iloc[i]
        volume_ok = df["volume"].iloc[i] >= volume_sma.iloc[i] * MIN_VOLUME_MULTIPLIER
        adx_ok = adx_val.iloc[i] >= MIN_ADX if not _pd.isna(adx_val.iloc[i]) else False
        
        # Very strict conditions - price must be touching bands
        price_near_lower = current_price <= lower_band * 1.0005  # Within 0.05% of lower band
        price_near_upper = current_price >= upper_band * 0.9995  # Within 0.05% of upper band
        
        if volume_ok and adx_ok:
            # Oversold: very strict RSI (20 instead of 25) and price must touch lower band
            if price_near_lower and rsi_current < 20:
                signals[i] = 1
            # Overbought: very strict RSI (80 instead of 75) and price must touch upper band
            elif price_near_upper and rsi_current > 80:
                signals[i] = -1
    
    return signals


def generate_macd_signals_optimized(df: _pd.DataFrame) -> _np.ndarray:
    """
    Optimized MACD with filters:
    - Volume filter
    - ADX filter
    - Faster MACD parameters (8,17,9 instead of 12,26,9)
    """
    # Faster MACD for scalping
    macd_line = ema(df["close"], 8) - ema(df["close"], 17)
    signal_line = ema(macd_line, 9)
    
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    atr_pct = atr_val / df["close"]
    
    diff = macd_line - signal_line
    signals = _np.zeros(len(df), dtype=int)
    prev = diff.iloc[0] if len(diff) > 0 else 0
    
    for i in range(1, len(df)):
        volume_ok = df["volume"].iloc[i] >= volume_sma.iloc[i] * MIN_VOLUME_MULTIPLIER
        adx_ok = adx_val.iloc[i] >= MIN_ADX if not _pd.isna(adx_val.iloc[i]) else False
        volatility_ok = atr_pct.iloc[i] >= MIN_ATR_PCT if not _pd.isna(atr_pct.iloc[i]) else False
        
        if volume_ok and adx_ok and volatility_ok:
            if diff.iloc[i] > 0 and prev <= 0:
                signals[i] = 1
            elif diff.iloc[i] < 0 and prev >= 0:
                signals[i] = -1
        
        prev = diff.iloc[i]
    
    return signals


def generate_atr_breakout_signals(df: _pd.DataFrame) -> _np.ndarray:
    """
    Generate ATR Breakout signals with EMA trend filter and RSI filter.
    Added volume and ADX filters for better signal quality.
    
    Strategy logic:
    - EMA20 > EMA50 → only LONG signals
    - EMA20 < EMA50 → only SHORT signals
    - LONG: Close > EMA20 + (k × ATR)
    - SHORT: Close < EMA20 - (k × ATR)
    - RSI filter: LONG (50-70), SHORT (30-50)
    - Volume filter: volume >= 1.2× average
    - ADX filter: ADX >= 25 (strong trend)
    """
    if len(df) < 50:
        return _np.zeros(len(df), dtype=int)
    
    # Calculate indicators
    ema20 = ema(df["close"], 20)
    ema50 = ema(df["close"], 50)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    signals = _np.zeros(len(df), dtype=int)
    
    for i in range(50, len(df)):  # Start from index 50 to have enough data
        if (_pd.isna(ema20.iloc[i]) or _pd.isna(ema50.iloc[i]) or 
            _pd.isna(atr_val.iloc[i]) or _pd.isna(rsi_val.iloc[i]) or
            _pd.isna(volume_sma.iloc[i]) or _pd.isna(adx_val.iloc[i])):
            continue
        
        current_price = df["close"].iloc[i]
        ema20_current = ema20.iloc[i]
        ema50_current = ema50.iloc[i]
        atr_current = atr_val.iloc[i]
        rsi_current = rsi_val.iloc[i]
        volume_current = df["volume"].iloc[i]
        adx_current = adx_val.iloc[i]
        
        # Filters - using config values
        volume_ok = volume_current >= volume_sma.iloc[i] * VOLUME_MULTIPLIER
        adx_ok = adx_current >= ADX_THRESHOLD
        
        if not (volume_ok and adx_ok):
            continue
        
        # Calculate breakout levels
        breakout_long = ema20_current + (ATR_BREAKOUT_MULTIPLIER * atr_current)
        breakout_short = ema20_current - (ATR_BREAKOUT_MULTIPLIER * atr_current)
        
        # Trend filter: EMA20 > EMA50 → uptrend (only LONG)
        if ema20_current > ema50_current:
            # LONG signal: price breaks above EMA20 + (k × ATR)
            if current_price > breakout_long:
                # RSI filter: using config values
                if RSI_LONG_MIN < rsi_current < RSI_LONG_MAX:
                    signals[i] = 1
        
        # Trend filter: EMA20 < EMA50 → downtrend (only SHORT)
        elif ema20_current < ema50_current:
            # SHORT signal: price breaks below EMA20 - (k × ATR)
            if current_price < breakout_short:
                # RSI filter: using config values
                if RSI_SHORT_MIN < rsi_current < RSI_SHORT_MAX:
                    signals[i] = -1
    
    return signals


def backtest_atr_breakout_strategy(
    df: _pd.DataFrame,
    signals: _np.ndarray,
    name: str,
) -> StrategyResult:
    """
    Execute backtest for ATR Breakout strategy.
    Uses ATR-based stop loss and take profit instead of percentage-based.
    """
    result = StrategyResult(name)
    in_pos = False
    direction: Optional[int] = None
    entry_price: float = 0.0
    entry_time: _pd.Timestamp
    stop: float = 0.0
    tp: float = 0.0
    quantity: float = 0.0
    
    # Calculate ATR for stop loss and take profit
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    
    for i, row in df.iterrows():
        if _pd.isna(atr_val.iloc[i]):
            continue
            
        current_atr = atr_val.iloc[i]
        
        if not in_pos:
            if signals[i] == 1:
                # Open long
                direction = 1
                entry_price = row["close"]
                entry_time = row["datetime"]
                # SL = Entry - (1 × ATR)
                stop = entry_price - (ATR_SL_MULTIPLIER * current_atr)
                # TP = Entry + (RR × ATR)
                tp = entry_price + (ATR_TP_RR * current_atr)
                # Calculate quantity based on risk
                risk_amount = entry_price - stop
                if risk_amount > 0:
                    quantity = RISK_PER_TRADE / risk_amount
                else:
                    continue
                in_pos = True
            elif signals[i] == -1:
                # Open short
                direction = -1
                entry_price = row["close"]
                entry_time = row["datetime"]
                # SL = Entry + (1 × ATR)
                stop = entry_price + (ATR_SL_MULTIPLIER * current_atr)
                # TP = Entry - (RR × ATR)
                tp = entry_price - (ATR_TP_RR * current_atr)
                # Calculate quantity based on risk
                risk_amount = stop - entry_price
                if risk_amount > 0:
                    quantity = RISK_PER_TRADE / risk_amount
                else:
                    continue
                in_pos = True
        else:
            price = row["close"]
            exit_flag = False
            profit = 0.0
            
            if direction == 1:  # Long position
                if price <= stop:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price >= tp:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == -1:  # Opposite signal
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
            elif direction == -1:  # Short position
                if price >= stop:
                    profit = (entry_price - price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price <= tp:
                    profit = (entry_price - price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == 1:  # Opposite signal
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
# Main backtesting logic
# ----------------------------------------------------------------------

def run_backtest() -> None:
    """Run optimized backtests."""
    # Load data
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
    
    # Generate optimized signals
    print("\nGenerating optimized signals with filters...")
    ema_signals = generate_ema_signals_optimized(data)
    bb_signals = generate_bollinger_rsi_signals_optimized(data)
    macd_signals = generate_macd_signals_optimized(data)
    atr_breakout_signals = generate_atr_breakout_signals(data)
    
    # Count signals before filtering
    print(f"EMA signals: {sum(abs(ema_signals))}")
    print(f"Bollinger+RSI signals: {sum(abs(bb_signals))}")
    print(f"MACD signals: {sum(abs(macd_signals))}")
    print(f"ATR Breakout signals: {sum(abs(atr_breakout_signals))}")
    
    # Backtest
    print("\nRunning optimized backtests...")
    res_ema = backtest_strategy(data, ema_signals, rr=RR_EMA, stop_pct=STOP_PCT, name="EMA(8,21) Optimized")
    res_bb = backtest_strategy(data, bb_signals, rr=RR_BB, stop_pct=STOP_PCT, name="Bollinger+RSI Optimized")
    res_macd = backtest_strategy(data, macd_signals, rr=RR_MACD, stop_pct=STOP_PCT, name="MACD(8,17,9) Optimized")
    res_atr = backtest_atr_breakout_strategy(data, atr_breakout_signals, name="ATR Breakout (EMA20/50 + RSI)")
    results = [res_ema, res_bb, res_macd, res_atr]
    
    # Print results
    print("\n" + "="*70)
    print("OPTIMIZED Scalping Strategy Backtest Summary")
    print(f"Risk per trade: ${RISK_PER_TRADE}")
    print(f"Period: {LOOKBACK_DAYS} days")
    print("="*70)
    for res in results:
        print(f"\nStrategy: {res.name}")
        print(f"  Trades executed: {res.trade_count}")
        print(f"  Wins: {res.wins}, Losses: {res.losses}, Win rate: {res.win_rate:.2%}")
        if res.trade_count > 0:
            print(f"  Avg Win: ${res.avg_win:.2f}, Avg Loss: ${res.avg_loss:.2f}")
        print(f"  Total P/L (USD): {res.total_profit:.2f}")
    
    # Determine best strategy
    best = max(results, key=lambda r: r.total_profit)
    print(f"\n{'='*70}")
    print(f"Best performing strategy: {best.name}")
    print(f"Net profit: {best.total_profit:.2f} USD with win rate {best.win_rate:.2%}")
    print("="*70)
    
    # Compare with original
    print("\n" + "="*70)
    print("IMPROVEMENT SUMMARY")
    print("="*70)
    print("Optimizations applied:")
    print("  - Volume filter (min 50% above average)")
    print("  - ADX filter (min 30 for trend strength)")
    print("  - ATR volatility filter (min 0.15%)")
    print("  - Increased stop loss to 0.20% (from 0.15%)")
    print("  - Increased R:R ratios (2.0-2.5:1)")
    print("  - Optimized indicator parameters")
    print("  - NEW: ATR Breakout strategy (EMA20/50 + RSI filter)")
    print("="*70)


if __name__ == "__main__":  # pragma: no cover
    run_backtest()

