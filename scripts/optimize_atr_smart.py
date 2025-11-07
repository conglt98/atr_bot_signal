"""
Smart Optimization for ATR Breakout Strategy
============================================

Optimizes ATR Breakout strategy by testing key parameters systematically.
Uses a smarter approach: test most impactful parameters first.

Usage
-----
    python optimize_atr_smart.py
"""

import os
import sys
from pathlib import Path
from typing import Tuple, Dict, List, Optional

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
)

from backtest_optimized import (
    Trade,
    StrategyResult,
    adx,
    atr,
    sma,
    RISK_PER_TRADE,
    FEE_PER_TRADE,
)


DATA_FILE: Optional[str] = "btcusdt_ohlcv.csv"


def backtest_atr_config(
    df: _pd.DataFrame,
    atr_k: float,
    atr_rr: float,
    rsi_long_min: float,
    rsi_long_max: float,
    rsi_short_min: float,
    rsi_short_max: float,
    volume_mult: float,
    adx_thresh: float,
) -> StrategyResult:
    """Backtest single configuration."""
    if len(df) < 50:
        return StrategyResult("")
    
    ema20 = ema(df["close"], 20)
    ema50 = ema(df["close"], 50)
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
        
        if not (vol_curr >= volume_sma.iloc[i] * volume_mult and adx_curr >= adx_thresh):
            continue
        
        breakout_long = ema20_curr + (atr_k * atr_curr)
        breakout_short = ema20_curr - (atr_k * atr_curr)
        
        if ema20_curr > ema50_curr and price > breakout_long:
            if rsi_long_min < rsi_curr < rsi_long_max:
                signals[i] = 1
        elif ema20_curr < ema50_curr and price < breakout_short:
            if rsi_short_min < rsi_curr < rsi_short_max:
                signals[i] = -1
    
    # Backtest
    result = StrategyResult("")
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
        
        if not in_pos:
            if signals[i] == 1:
                direction = 1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price - (1.0 * atr_curr)
                tp = entry_price + (atr_rr * atr_curr)
                risk = entry_price - stop
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
                    in_pos = True
            elif signals[i] == -1:
                direction = -1
                entry_price = row["close"]
                entry_time = row["datetime"]
                stop = entry_price + (1.0 * atr_curr)
                tp = entry_price - (atr_rr * atr_curr)
                risk = stop - entry_price
                if risk > 0:
                    quantity = RISK_PER_TRADE / risk
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


def optimize_step_by_step(df: _pd.DataFrame):
    """Optimize parameters step by step."""
    print("="*80)
    print("ATR BREAKOUT - SMART OPTIMIZATION")
    print("="*80)
    
    # Start with current best known parameters
    best_config = {
        'atr_k': 1.0,
        'atr_rr': 2.0,
        'rsi_long_min': 55,
        'rsi_long_max': 65,
        'rsi_short_min': 35,
        'rsi_short_max': 45,
        'volume_mult': 1.5,
        'adx_thresh': 30,
    }
    
    best_result = backtest_atr_config(df, **best_config)
    best_profit = best_result.total_profit
    
    print(f"\nInitial config: Profit = ${best_profit:.2f}, Trades = {best_result.trade_count}, WR = {best_result.win_rate:.2%}")
    
    # Step 1: Optimize R:R ratio (most impactful)
    print("\n" + "-"*80)
    print("Step 1: Optimizing R:R Ratio...")
    print("-"*80)
    
    for rr in [1.5, 2.0, 2.5, 3.0, 3.5]:
        config = best_config.copy()
        config['atr_rr'] = rr
        result = backtest_atr_config(df, **config)
        print(f"  R:R = {rr}: Profit = ${result.total_profit:.2f}, Trades = {result.trade_count}, WR = {result.win_rate:.2%}")
        if result.total_profit > best_profit and 10 <= result.trade_count <= 500:
            best_profit = result.total_profit
            best_config['atr_rr'] = rr
            best_result = result
    
    print(f"  → Best R:R = {best_config['atr_rr']}, Profit = ${best_profit:.2f}")
    
    # Step 2: Optimize ATR multiplier (k)
    print("\n" + "-"*80)
    print("Step 2: Optimizing ATR Breakout Multiplier (k)...")
    print("-"*80)
    
    for k in [0.8, 1.0, 1.2, 1.5, 2.0]:
        config = best_config.copy()
        config['atr_k'] = k
        result = backtest_atr_config(df, **config)
        print(f"  k = {k}: Profit = ${result.total_profit:.2f}, Trades = {result.trade_count}, WR = {result.win_rate:.2%}")
        if result.total_profit > best_profit and 10 <= result.trade_count <= 500:
            best_profit = result.total_profit
            best_config['atr_k'] = k
            best_result = result
    
    print(f"  → Best k = {best_config['atr_k']}, Profit = ${best_profit:.2f}")
    
    # Step 3: Optimize RSI ranges
    print("\n" + "-"*80)
    print("Step 3: Optimizing RSI Ranges...")
    print("-"*80)
    
    rsi_configs = [
        ((50, 70), (30, 50)),
        ((52, 68), (32, 48)),
        ((55, 65), (35, 45)),
        ((50, 65), (35, 50)),
        ((52, 70), (30, 48)),
        ((48, 68), (32, 52)),
    ]
    
    for rsi_long, rsi_short in rsi_configs:
        config = best_config.copy()
        config['rsi_long_min'] = rsi_long[0]
        config['rsi_long_max'] = rsi_long[1]
        config['rsi_short_min'] = rsi_short[0]
        config['rsi_short_max'] = rsi_short[1]
        result = backtest_atr_config(df, **config)
        print(f"  RSI L={rsi_long}, S={rsi_short}: Profit = ${result.total_profit:.2f}, Trades = {result.trade_count}, WR = {result.win_rate:.2%}")
        if result.total_profit > best_profit and 10 <= result.trade_count <= 500:
            best_profit = result.total_profit
            best_config['rsi_long_min'] = rsi_long[0]
            best_config['rsi_long_max'] = rsi_long[1]
            best_config['rsi_short_min'] = rsi_short[0]
            best_config['rsi_short_max'] = rsi_short[1]
            best_result = result
    
    print(f"  → Best RSI: L={best_config['rsi_long_min']}-{best_config['rsi_long_max']}, S={best_config['rsi_short_min']}-{best_config['rsi_short_max']}, Profit = ${best_profit:.2f}")
    
    # Step 4: Optimize filters
    print("\n" + "-"*80)
    print("Step 4: Optimizing Filters (Volume & ADX)...")
    print("-"*80)
    
    for vol_mult in [1.2, 1.5, 2.0, 2.5]:
        for adx_thresh in [25, 30, 35, 40]:
            config = best_config.copy()
            config['volume_mult'] = vol_mult
            config['adx_thresh'] = adx_thresh
            result = backtest_atr_config(df, **config)
            if result.trade_count >= 10:  # At least 10 trades
                print(f"  Vol={vol_mult}, ADX={adx_thresh}: Profit = ${result.total_profit:.2f}, Trades = {result.trade_count}, WR = {result.win_rate:.2%}")
                if result.total_profit > best_profit and result.trade_count <= 500:
                    best_profit = result.total_profit
                    best_config['volume_mult'] = vol_mult
                    best_config['adx_thresh'] = adx_thresh
                    best_result = result
    
    print(f"  → Best: Vol={best_config['volume_mult']}, ADX={best_config['adx_thresh']}, Profit = ${best_profit:.2f}")
    
    # Final result
    print("\n" + "="*80)
    print("FINAL OPTIMIZED CONFIGURATION")
    print("="*80)
    print(f"Profit: ${best_result.total_profit:.2f}")
    print(f"Win Rate: {best_result.win_rate:.2%}")
    print(f"Trades: {best_result.trade_count}")
    print(f"Wins: {best_result.wins}, Losses: {best_result.losses}")
    print(f"Avg Win: ${best_result.avg_win:.2f}, Avg Loss: ${best_result.avg_loss:.2f}")
    print(f"\nParameters:")
    for key, value in best_config.items():
        print(f"  {key}: {value}")
    print("="*80)
    
    return best_config, best_result


if __name__ == "__main__":
    # Load data
    if DATA_FILE and os.path.exists(DATA_FILE):
        print(f"Loading data from {DATA_FILE}...")
        data = _pd.read_csv(DATA_FILE)
        data["datetime"] = _pd.to_datetime(data["datetime"])
        data = data.sort_values("datetime").reset_index(drop=True)
        print(f"Loaded {len(data)} candles\n")
    else:
        print("Data file not found!")
        exit(1)
    
    best_config, best_result = optimize_step_by_step(data)

