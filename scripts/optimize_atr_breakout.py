"""
Advanced Optimization Script for ATR Breakout Strategy
======================================================

This script performs comprehensive optimization of ATR Breakout strategy
by testing multiple parameter combinations and filters.

Usage
-----
    python optimize_atr_breakout.py
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from itertools import product

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import numpy as _np
import pandas as _pd

from utils import (
    fetch_historical_ohlcv,
    ema,
    rsi,
    bollinger_bands,
)

# Import from backtest_optimized
from backtest_optimized import (
    Trade,
    StrategyResult,
    adx,
    atr,
    sma,
    RISK_PER_TRADE,
    FEE_PER_TRADE,
)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

DATA_FILE: Optional[str] = "btcusdt_ohlcv.csv"
LOOKBACK_DAYS: int = 30

# Parameter ranges to test
ATR_BREAKOUT_MULTIPLIERS = [0.8, 1.0, 1.2, 1.5]  # k values
ATR_TP_RRS = [1.5, 2.0, 2.5, 3.0]  # R:R ratios
RSI_LONG_RANGES = [
    (50, 70), (52, 68), (55, 65), (52, 70), (50, 65)
]
RSI_SHORT_RANGES = [
    (30, 50), (32, 48), (35, 45), (30, 48), (32, 50)
]
VOLUME_MULTIPLIERS = [1.2, 1.5, 2.0]
ADX_THRESHOLDS = [25, 30, 35]


def backtest_atr_breakout_optimized(
    df: _pd.DataFrame,
    atr_breakout_mult: float,
    atr_tp_rr: float,
    rsi_long_min: float,
    rsi_long_max: float,
    rsi_short_min: float,
    rsi_short_max: float,
    volume_mult: float,
    adx_threshold: float,
    name: str = "ATR Breakout",
) -> Tuple[StrategyResult, int]:
    """
    Backtest ATR Breakout with specific parameters.
    Returns (result, signal_count).
    """
    if len(df) < 50:
        return StrategyResult(name), 0
    
    # Calculate indicators
    ema20 = ema(df["close"], 20)
    ema50 = ema(df["close"], 50)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    signals = _np.zeros(len(df), dtype=int)
    signal_count = 0
    
    for i in range(50, len(df)):
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
        
        # Filters
        volume_ok = volume_current >= volume_sma.iloc[i] * volume_mult
        adx_ok = adx_current >= adx_threshold
        
        if not (volume_ok and adx_ok):
            continue
        
        # Calculate breakout levels
        breakout_long = ema20_current + (atr_breakout_mult * atr_current)
        breakout_short = ema20_current - (atr_breakout_mult * atr_current)
        
        # Trend filter: EMA20 > EMA50 → uptrend (only LONG)
        if ema20_current > ema50_current:
            if current_price > breakout_long:
                if rsi_long_min < rsi_current < rsi_long_max:
                    signals[i] = 1
                    signal_count += 1
        
        # Trend filter: EMA20 < EMA50 → downtrend (only SHORT)
        elif ema20_current < ema50_current:
            if current_price < breakout_short:
                if rsi_short_min < rsi_current < rsi_short_max:
                    signals[i] = -1
                    signal_count += 1
    
    # Backtest
    result = StrategyResult(name)
    in_pos = False
    direction: Optional[int] = None
    entry_price: float = 0.0
    entry_time: _pd.Timestamp
    stop: float = 0.0
    tp: float = 0.0
    quantity: float = 0.0
    
    for i, row in df.iterrows():
        if _pd.isna(atr_val.iloc[i]):
            continue
            
        current_atr = atr_val.iloc[i]
        
        if not in_pos:
            if signals[i] == 1:
                direction = 1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price - (1.0 * current_atr)
                tp = entry_price + (atr_tp_rr * current_atr)
                risk_amount = entry_price - stop
                if risk_amount > 0:
                    quantity = RISK_PER_TRADE / risk_amount
                else:
                    continue
                in_pos = True
            elif signals[i] == -1:
                direction = -1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price + (1.0 * current_atr)
                tp = entry_price - (atr_tp_rr * current_atr)
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
    
    return result, signal_count


def run_optimization():
    """Run comprehensive parameter optimization."""
    # Load data
    if DATA_FILE and os.path.exists(DATA_FILE):
        print(f"Loading data from {DATA_FILE}...")
        data = _pd.read_csv(DATA_FILE)
        data["datetime"] = _pd.to_datetime(data["datetime"])
        data = data.sort_values("datetime").reset_index(drop=True)
        print(f"Loaded {len(data)} candles")
    else:
        print("Data file not found!")
        return
    
    print("\n" + "="*80)
    print("ATR BREAKOUT STRATEGY - COMPREHENSIVE OPTIMIZATION")
    print("="*80)
    print(f"Testing {len(ATR_BREAKOUT_MULTIPLIERS) * len(ATR_TP_RRS) * len(RSI_LONG_RANGES) * len(RSI_SHORT_RANGES) * len(VOLUME_MULTIPLIERS) * len(ADX_THRESHOLDS)} combinations...")
    print("This may take a while...\n")
    
    best_result = None
    best_params = None
    best_profit = float('-inf')
    results = []
    
    total_combinations = (len(ATR_BREAKOUT_MULTIPLIERS) * len(ATR_TP_RRS) * 
                         len(RSI_LONG_RANGES) * len(RSI_SHORT_RANGES) * 
                         len(VOLUME_MULTIPLIERS) * len(ADX_THRESHOLDS))
    current = 0
    
    # Test all combinations
    for (atr_mult, atr_rr, rsi_long, rsi_short, vol_mult, adx_thresh) in product(
        ATR_BREAKOUT_MULTIPLIERS,
        ATR_TP_RRS,
        RSI_LONG_RANGES,
        RSI_SHORT_RANGES,
        VOLUME_MULTIPLIERS,
        ADX_THRESHOLDS
    ):
        current += 1
        if current % 100 == 0:
            print(f"Progress: {current}/{total_combinations} ({current*100/total_combinations:.1f}%)")
        
        name = f"ATR(k={atr_mult},RR={atr_rr},RSI={rsi_long[0]}-{rsi_long[1]}/{rsi_short[0]}-{rsi_short[1]},Vol={vol_mult},ADX={adx_thresh})"
        
        result, signal_count = backtest_atr_breakout_optimized(
            data,
            atr_mult,
            atr_rr,
            rsi_long[0], rsi_long[1],
            rsi_short[0], rsi_short[1],
            vol_mult,
            adx_thresh,
            name
        )
        
        # Only consider strategies with reasonable number of trades (10-500)
        if 10 <= result.trade_count <= 500:
            results.append({
                'params': {
                    'atr_mult': atr_mult,
                    'atr_rr': atr_rr,
                    'rsi_long': rsi_long,
                    'rsi_short': rsi_short,
                    'vol_mult': vol_mult,
                    'adx_thresh': adx_thresh,
                },
                'result': result,
                'signal_count': signal_count,
            })
            
            if result.total_profit > best_profit:
                best_profit = result.total_profit
                best_result = result
                best_params = {
                    'atr_mult': atr_mult,
                    'atr_rr': atr_rr,
                    'rsi_long': rsi_long,
                    'rsi_short': rsi_short,
                    'vol_mult': vol_mult,
                    'adx_thresh': adx_thresh,
                }
    
    # Sort by profit
    results.sort(key=lambda x: x['result'].total_profit, reverse=True)
    
    # Print top 10
    print("\n" + "="*80)
    print("TOP 10 OPTIMIZED CONFIGURATIONS")
    print("="*80)
    
    for i, res in enumerate(results[:10], 1):
        r = res['result']
        p = res['params']
        print(f"\n{i}. Profit: ${r.total_profit:.2f} | Win Rate: {r.win_rate:.2%} | Trades: {r.trade_count}")
        print(f"   Params: k={p['atr_mult']}, R:R={p['atr_rr']}, RSI_L={p['rsi_long'][0]}-{p['rsi_long'][1]}, RSI_S={p['rsi_short'][0]}-{p['rsi_short'][1]}, Vol={p['vol_mult']}, ADX={p['adx_thresh']}")
        print(f"   Wins: {r.wins}, Losses: {r.losses}, Avg Win: ${r.avg_win:.2f}, Avg Loss: ${r.avg_loss:.2f}")
    
    # Print best
    if best_result:
        print("\n" + "="*80)
        print("BEST CONFIGURATION")
        print("="*80)
        print(f"Profit: ${best_result.total_profit:.2f}")
        print(f"Win Rate: {best_result.win_rate:.2%}")
        print(f"Trades: {best_result.trade_count}")
        print(f"Wins: {best_result.wins}, Losses: {best_result.losses}")
        print(f"Avg Win: ${best_result.avg_win:.2f}, Avg Loss: ${best_result.avg_loss:.2f}")
        print(f"\nParameters:")
        print(f"  ATR Breakout Multiplier (k): {best_params['atr_mult']}")
        print(f"  R:R Ratio: {best_params['atr_rr']}")
        print(f"  RSI Long Range: {best_params['rsi_long'][0]}-{best_params['rsi_long'][1]}")
        print(f"  RSI Short Range: {best_params['rsi_short'][0]}-{best_params['rsi_short'][1]}")
        print(f"  Volume Multiplier: {best_params['vol_mult']}")
        print(f"  ADX Threshold: {best_params['adx_thresh']}")
        print("="*80)
    
    return best_params, best_result, results


if __name__ == "__main__":
    best_params, best_result, all_results = run_optimization()

