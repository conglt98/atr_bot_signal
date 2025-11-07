"""
Final Optimization Tests
========================

Tests additional improvements:
1. Early exit on RSI reversal
2. Volume spike detection (only trade on volume spikes)
3. Combined filters
4. Different R:R ratios with current config
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass

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


def backtest_with_early_exit(df: _pd.DataFrame, use_early_exit: bool = False) -> StrategyResult:
    """Backtest with early exit on RSI reversal."""
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
    
    # Backtest
    result = StrategyResult("ATR Breakout" + (" + Early Exit" if use_early_exit else ""))
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
        rsi_curr = rsi_val.iloc[i]
        
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
            
            # Early exit on RSI reversal
            if use_early_exit:
                if direction == 1:  # Long position
                    # Exit if RSI drops below 50 (momentum weakening)
                    if rsi_curr < 50:
                        profit = (price - entry_price) * quantity - FEE_PER_TRADE
                        exit_flag = True
                elif direction == -1:  # Short position
                    # Exit if RSI rises above 50 (momentum weakening)
                    if rsi_curr > 50:
                        profit = (entry_price - price) * quantity - FEE_PER_TRADE
                        exit_flag = True
            
            if not exit_flag:
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


def backtest_with_volume_spike(df: _pd.DataFrame, volume_spike_mult: float = 3.0) -> StrategyResult:
    """Backtest with volume spike filter (only trade on volume spikes)."""
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
        
        # Volume spike filter: volume must be at least volume_spike_mult × average
        volume_spike_ok = vol_curr >= volume_sma.iloc[i] * volume_spike_mult
        if not (volume_spike_ok and adx_curr >= ADX_THRESHOLD):
            continue
        
        breakout_long = ema20_curr + (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        breakout_short = ema20_curr - (ATR_BREAKOUT_MULTIPLIER * atr_curr)
        
        if ema20_curr > ema50_curr and price > breakout_long:
            if RSI_LONG_MIN < rsi_curr < RSI_LONG_MAX:
                signals[i] = 1
        elif ema20_curr < ema50_curr and price < breakout_short:
            if RSI_SHORT_MIN < rsi_curr < RSI_SHORT_MAX:
                signals[i] = -1
    
    # Backtest (same as baseline)
    result = StrategyResult(f"ATR Breakout (Volume Spike {volume_spike_mult}×)")
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


def test_different_rr_ratios(df: _pd.DataFrame):
    """Test different R:R ratios with current configuration."""
    results = []
    
    for rr in [2.0, 2.5, 3.0, 3.5]:
        # Temporarily change R:R
        global ATR_TP_RR
        original_rr = ATR_TP_RR
        ATR_TP_RR = rr
        
        result = backtest_with_early_exit(df, use_early_exit=False)
        result.name = f"ATR Breakout (R:R={rr})"
        results.append((rr, result))
        
        ATR_TP_RR = original_rr
    
    return results


def run_final_tests():
    """Run final optimization tests."""
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
    print("FINAL OPTIMIZATION TESTS")
    print("="*80)
    
    # Baseline
    print("\n1. BASELINE (Current Configuration)")
    baseline = backtest_with_early_exit(data, use_early_exit=False)
    print(f"   Profit: ${baseline.total_profit:.2f}")
    print(f"   Trades: {baseline.trade_count}, Win Rate: {baseline.win_rate:.2%}")
    print(f"   Avg Win: ${baseline.avg_win:.2f}, Avg Loss: ${baseline.avg_loss:.2f}")
    
    # Early exit
    print("\n2. EARLY EXIT ON RSI REVERSAL")
    early_exit = backtest_with_early_exit(data, use_early_exit=True)
    print(f"   Profit: ${early_exit.total_profit:.2f}")
    print(f"   Trades: {early_exit.trade_count}, Win Rate: {early_exit.win_rate:.2%}")
    print(f"   Avg Win: ${early_exit.avg_win:.2f}, Avg Loss: ${early_exit.avg_loss:.2f}")
    improvement = early_exit.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    # Volume spike
    print("\n3. VOLUME SPIKE FILTER (3× Average)")
    volume_spike = backtest_with_volume_spike(data, volume_spike_mult=3.0)
    print(f"   Profit: ${volume_spike.total_profit:.2f}")
    print(f"   Trades: {volume_spike.trade_count}, Win Rate: {volume_spike.win_rate:.2%}")
    print(f"   Avg Win: ${volume_spike.avg_win:.2f}, Avg Loss: ${volume_spike.avg_loss:.2f}")
    improvement = volume_spike.total_profit - baseline.total_profit
    print(f"   Improvement: ${improvement:+.2f}")
    
    # Different R:R ratios
    print("\n4. TESTING DIFFERENT R:R RATIOS")
    rr_results = test_different_rr_ratios(data)
    for rr, result in rr_results:
        print(f"   R:R = {rr}: Profit = ${result.total_profit:.2f}, Trades = {result.trade_count}, WR = {result.win_rate:.2%}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    all_results = [
        ("Baseline", baseline),
        ("Early Exit", early_exit),
        ("Volume Spike 3×", volume_spike),
    ]
    
    # Add R:R results
    for rr, result in rr_results:
        all_results.append((f"R:R={rr}", result))
    
    all_results.sort(key=lambda x: x[1].total_profit, reverse=True)
    
    print("\nBest to Worst:")
    for i, (name, res) in enumerate(all_results, 1):
        print(f"{i}. {name}: ${res.total_profit:.2f} (WR: {res.win_rate:.2%}, Trades: {res.trade_count})")
    
    best = all_results[0]
    print(f"\n✅ Best Configuration: {best[0]}")
    print(f"   Profit: ${best[1].total_profit:.2f}")
    print(f"   Improvement over baseline: ${best[1].total_profit - baseline.total_profit:+.2f}")
    
    if best[1].total_profit > baseline.total_profit:
        print(f"\n💡 RECOMMENDATION: Consider using {best[0]} configuration")
    else:
        print(f"\n💡 RECOMMENDATION: Current baseline configuration is optimal")
    
    print("="*80)


if __name__ == "__main__":
    run_final_tests()

