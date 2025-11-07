"""
Advanced Optimization for ATR Breakout Strategy
===============================================

Tests additional optimizations:
1. Trailing stop loss
2. Time-based filter (only trade during high liquidity hours)
3. Volume spike detection
4. Early exit on reversal signals
5. Multiple confirmation signals

Usage
-----
    python advanced_optimization.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pandas as _pd
import numpy as _np

from utils import fetch_historical_ohlcv
from backtest_optimized import (
    Trade,
    StrategyResult,
    ema,
    rsi,
    adx,
    atr,
    sma,
    RISK_PER_TRADE,
    FEE_PER_TRADE,
)

from config import (
    EXCHANGE_ID,
    SYMBOL,
    TIMEFRAME,
    LOOKBACK_DAYS,
    DATA_FILE,
    ATR_BREAKOUT_MULTIPLIER,
    ATR_SL_MULTIPLIER,
    ATR_TP_RR,
    RSI_LONG_MIN,
    RSI_LONG_MAX,
    RSI_SHORT_MIN,
    RSI_SHORT_MAX,
    VOLUME_MULTIPLIER,
    ADX_THRESHOLD,
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
)


def backtest_atr_with_trailing_stop(
    df: _pd.DataFrame,
    use_trailing_stop: bool = False,
    trailing_stop_atr_mult: float = 0.5,
) -> StrategyResult:
    """Backtest ATR Breakout with optional trailing stop."""
    if len(df) < 50:
        return StrategyResult("ATR Breakout")
    
    ema20 = ema(df["close"], EMA_FAST_PERIOD)
    ema50 = ema(df["close"], EMA_SLOW_PERIOD)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    signals = _np.zeros(len(df), dtype=int)
    
    for i in range(50, len(df)):
        if (_pd.isna(ema20.iloc[i]) or _pd.isna(ema50.iloc[i]) or 
            _pd.isna(atr_val.iloc[i]) or _pd.isna(rsi_val.iloc[i]) or
            _pd.isna(volume_sma.iloc[i]) or _pd.isna(adx_val.iloc[i])):
            continue
        
        price = df["close"].iloc[i]
        ema20_curr = ema20.iloc[i]
        ema50_curr = ema50.iloc[i]
        atr_curr = atr_val.iloc[i]
        rsi_curr = rsi_val.iloc[i]
        vol_curr = df["volume"].iloc[i]
        adx_curr = adx_val.iloc[i]
        
        if not (vol_curr >= volume_sma.iloc[i] * VOLUME_MULTIPLIER and adx_curr >= ADX_THRESHOLD):
            continue
        
        breakout_long = ema20_curr + (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        breakout_short = ema20_curr - (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        
        if ema20_curr > ema50_curr and price > breakout_long:
            if RSI_LONG_MIN < rsi_curr < RSI_LONG_MAX:
                signals[i] = 1
        elif ema20_curr < ema50_curr and price < breakout_short:
            if RSI_SHORT_MIN < rsi_curr < RSI_SHORT_MAX:
                signals[i] = -1
    
    # Backtest with trailing stop
    result = StrategyResult("ATR Breakout" + (" + Trailing Stop" if use_trailing_stop else ""))
    in_pos = False
    direction = None
    entry_price = 0.0
    entry_time = None
    stop = 0.0
    tp = 0.0
    quantity = 0.0
    highest_price = 0.0  # For trailing stop (long)
    lowest_price = float('inf')  # For trailing stop (short)
    
    for i, row in df.iterrows():
        if _pd.isna(atr_val.iloc[i]):
            continue
        
        atr_curr = atr_val.iloc[i]
        price = row["close"]
        
        if not in_pos:
            if signals[i] == 1:
                direction = 1
                entry_price = price
                entry_time = row["datetime"]
                stop = entry_price - (ATR_SL_MULTIPLIER * atr_curr)
                tp = entry_price + (ATR_TP_RR * atr_curr)
                risk = entry_price - stop
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
                    in_pos = True
                    highest_price = entry_price
            elif signals[i] == -1:
                direction = -1
                entry_price = price
                entry_time = row["datetime"]
                stop = entry_price + (ATR_SL_MULTIPLIER * atr_curr)
                tp = entry_price - (ATR_TP_RR * atr_curr)
                risk = stop - entry_price
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
                    in_pos = True
                    lowest_price = entry_price
        else:
            exit_flag = False
            profit = 0.0
            
            # Update trailing stop for long
            if direction == 1:
                if price > highest_price:
                    highest_price = price
                    if use_trailing_stop:
                        # Move stop loss up to trailing_stop_atr_mult × ATR below highest price
                        new_stop = highest_price - (trailing_stop_atr_mult * atr_curr)
                        if new_stop > stop:
                            stop = new_stop
                
                if price <= stop:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif price >= tp:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
                elif signals[i] == -1:
                    profit = (price - entry_price) * quantity - FEE_PER_TRADE
                    exit_flag = True
            
            # Update trailing stop for short
            elif direction == -1:
                if price < lowest_price:
                    lowest_price = price
                    if use_trailing_stop:
                        # Move stop loss down to trailing_stop_atr_mult × ATR above lowest price
                        new_stop = lowest_price + (trailing_stop_atr_mult * atr_curr)
                        if new_stop < stop:
                            stop = new_stop
                
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
                highest_price = 0.0
                lowest_price = float('inf')
    
    return result


def backtest_with_time_filter(df: _pd.DataFrame, start_hour: int = 8, end_hour: int = 20) -> StrategyResult:
    """Backtest with time filter (only trade during specified hours UTC)."""
    if len(df) < 50:
        return StrategyResult("ATR Breakout")
    
    ema20 = ema(df["close"], EMA_FAST_PERIOD)
    ema50 = ema(df["close"], EMA_SLOW_PERIOD)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    signals = _np.zeros(len(df), dtype=int)
    
    for i in range(50, len(df)):
        # Time filter
        hour = df["datetime"].iloc[i].hour
        if not (start_hour <= hour < end_hour):
            continue
        
        if (_pd.isna(ema20.iloc[i]) or _pd.isna(ema50.iloc[i]) or 
            _pd.isna(atr_val.iloc[i]) or _pd.isna(rsi_val.iloc[i]) or
            _pd.isna(volume_sma.iloc[i]) or _pd.isna(adx_val.iloc[i])):
            continue
        
        price = df["close"].iloc[i]
        ema20_curr = ema20.iloc[i]
        ema50_curr = ema50.iloc[i]
        atr_curr = atr_val.iloc[i]
        rsi_curr = rsi_val.iloc[i]
        vol_curr = df["volume"].iloc[i]
        adx_curr = adx_val.iloc[i]
        
        if not (vol_curr >= volume_sma.iloc[i] * VOLUME_MULTIPLIER and adx_curr >= ADX_THRESHOLD):
            continue
        
        breakout_long = ema20_curr + (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        breakout_short = ema20_curr - (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        
        if ema20_curr > ema50_curr and price > breakout_long:
            if RSI_LONG_MIN < rsi_curr < RSI_LONG_MAX:
                signals[i] = 1
        elif ema20_curr < ema50_curr and price < breakout_short:
            if RSI_SHORT_MIN < rsi_curr < RSI_SHORT_MAX:
                signals[i] = -1
    
    # Backtest (same as original)
    result = StrategyResult(f"ATR Breakout (Time Filter {start_hour}-{end_hour}h UTC)")
    in_pos = False
    direction = None
    entry_price = 0.0
    entry_time = None
    stop = 0.0
    tp = 0.0
    quantity = 0.0
    
    for i, row in df.iterrows():
        if _pd.isna(atr_val.iloc[i]):
            continue
        
        atr_curr = atr_val.iloc[i]
        price = row["close"]
        
        if not in_pos:
            if signals[i] == 1:
                direction = 1
                entry_price = price
                entry_time = row["datetime"]
                stop = entry_price - (ATR_SL_MULTIPLIER * atr_curr)
                tp = entry_price + (ATR_TP_RR * atr_curr)
                risk = entry_price - stop
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
                    in_pos = True
            elif signals[i] == -1:
                direction = -1
                entry_price = price
                entry_time = row["datetime"]
                stop = entry_price + (ATR_SL_MULTIPLIER * atr_curr)
                tp = entry_price - (ATR_TP_RR * atr_curr)
                risk = stop - entry_price
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
                    in_pos = True
        else:
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


def run_advanced_optimization():
    """Test advanced optimizations."""
    # Load data
    if DATA_FILE and os.path.exists(DATA_FILE):
        print(f"Loading data from {DATA_FILE}...")
        data = _pd.read_csv(DATA_FILE)
        data["datetime"] = _pd.to_datetime(data["datetime"])
        data = data.sort_values("datetime").reset_index(drop=True)
        print(f"Loaded {len(data)} candles\n")
    else:
        print("Data file not found!")
        return
    
    print("="*80)
    print("ADVANCED OPTIMIZATION TESTS")
    print("="*80)
    
    # Baseline
    print("\n1. BASELINE (Current Configuration)")
    baseline = backtest_atr_with_trailing_stop(data, use_trailing_stop=False)
    print(f"   Profit: ${baseline.total_profit:.2f}")
    print(f"   Trades: {baseline.trade_count}, Win Rate: {baseline.win_rate:.2%}")
    print(f"   Avg Win: ${baseline.avg_win:.2f}, Avg Loss: ${baseline.avg_loss:.2f}")
    
    # Test 1: Trailing Stop Loss
    print("\n2. TRAILING STOP LOSS (0.5× ATR)")
    trailing_05 = backtest_atr_with_trailing_stop(data, use_trailing_stop=True, trailing_stop_atr_mult=0.5)
    print(f"   Profit: ${trailing_05.total_profit:.2f}")
    print(f"   Trades: {trailing_05.trade_count}, Win Rate: {trailing_05.win_rate:.2%}")
    print(f"   Avg Win: ${trailing_05.avg_win:.2f}, Avg Loss: ${trailing_05.avg_loss:.2f}")
    improvement = trailing_05.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    print("\n3. TRAILING STOP LOSS (0.75× ATR)")
    trailing_075 = backtest_atr_with_trailing_stop(data, use_trailing_stop=True, trailing_stop_atr_mult=0.75)
    print(f"   Profit: ${trailing_075.total_profit:.2f}")
    print(f"   Trades: {trailing_075.trade_count}, Win Rate: {trailing_075.win_rate:.2%}")
    print(f"   Avg Win: ${trailing_075.avg_win:.2f}, Avg Loss: ${trailing_075.avg_loss:.2f}")
    improvement = trailing_075.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    # Test 2: Time Filter
    print("\n4. TIME FILTER (8-20h UTC - High Liquidity Hours)")
    time_filter = backtest_with_time_filter(data, start_hour=8, end_hour=20)
    print(f"   Profit: ${time_filter.total_profit:.2f}")
    print(f"   Trades: {time_filter.trade_count}, Win Rate: {time_filter.win_rate:.2%}")
    print(f"   Avg Win: ${time_filter.avg_win:.2f}, Avg Loss: ${time_filter.avg_loss:.2f}")
    improvement = time_filter.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    print("\n5. TIME FILTER (0-24h UTC - All Hours)")
    time_all = backtest_with_time_filter(data, start_hour=0, end_hour=24)
    print(f"   Profit: ${time_all.total_profit:.2f}")
    print(f"   Trades: {time_all.trade_count}, Win Rate: {time_all.win_rate:.2%}")
    print(f"   Avg Win: ${time_all.avg_win:.2f}, Avg Loss: ${time_all.avg_loss:.2f}")
    improvement = time_all.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    results = [
        ("Baseline", baseline),
        ("Trailing Stop 0.5×ATR", trailing_05),
        ("Trailing Stop 0.75×ATR", trailing_075),
        ("Time Filter 8-20h", time_filter),
    ]
    
    results.sort(key=lambda x: x[1].total_profit, reverse=True)
    
    print("\nBest to Worst:")
    for i, (name, res) in enumerate(results, 1):
        print(f"{i}. {name}: ${res.total_profit:.2f} (WR: {res.win_rate:.2%}, Trades: {res.trade_count})")
    
    best = results[0]
    print(f"\n✅ Best Configuration: {best[0]}")
    print(f"   Profit: ${best[1].total_profit:.2f}")
    print(f"   Improvement over baseline: ${best[1].total_profit - baseline.total_profit:+.2f}")
    print("="*80)


if __name__ == "__main__":
    run_advanced_optimization()

