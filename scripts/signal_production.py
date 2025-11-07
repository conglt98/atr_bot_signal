"""
Signal Production Script for BTCUSDT Scalping Bot
=================================================

This script generates real-time trading signals for BTCUSDT perpetual futures.
It fetches the latest market data, calculates indicators, and outputs trading
signals from multiple strategies (EMA, Bollinger+RSI, MACD).

Usage
-----
    python signal_production.py

The script will fetch the latest data and display current signals from all
strategies. You can run this in a loop or schedule it to run periodically
(e.g., every minute) to get continuous signal updates.
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, continue without it
    pass

import pandas as _pd
import numpy as _np
from datetime import datetime
from typing import Dict, Optional

from utils import (
    fetch_latest_ohlcv,
    get_current_price,
    ema,
    rsi,
    bollinger_bands,
    send_telegram_message,
)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# Exchange and symbol configuration
EXCHANGE_ID: str = "binance"  # e.g. "binance" or "bybit"
SYMBOL: str = "BTC/USDT:USDT"  # perpetual futures pair (BTCUSDT.P) recognised by ccxt
TIMEFRAME: str = "1m"          # 1‑minute candles

# Strategy parameters (should match backtest.py)
STOP_PCT: float = 0.0015       # stop loss distance as fraction of price (0.15 %)
RR_EMA: float = 2.0            # reward: risk ratio for EMA crossover strategy
RR_BB: float = 1.5             # reward: risk ratio for Bollinger+RSI strategy
RR_MACD: float = 2.0           # reward: risk ratio for MACD crossover strategy

# Data fetching
LOOKBACK_CANDLES: int = 200    # number of candles to fetch for indicator calculation

# Telegram notification configuration
# IMPORTANT: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file
# SECURITY: Never commit real tokens to Git!
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM: bool = True  # Set to True to enable Telegram notifications


# ----------------------------------------------------------------------
# Signal generation functions
# ----------------------------------------------------------------------

def get_ema_signal(df: _pd.DataFrame) -> Dict[str, any]:
    """
    Get current EMA(9/21) crossover signal.
    
    Returns
    -------
    dict
        Contains 'signal' (-1, 0, or 1), 'direction' (str), 'entry_price' (float),
        'stop_loss' (float), 'take_profit' (float), and 'reason' (str).
    """
    if len(df) < 21:
        return {
            "signal": 0,
            "direction": "NONE",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Insufficient data"
        }
    
    ema_fast = ema(df["close"], 9)
    ema_slow = ema(df["close"], 21)
    
    current_price = df["close"].iloc[-1]
    ema_fast_current = ema_fast.iloc[-1]
    ema_slow_current = ema_slow.iloc[-1]
    ema_fast_prev = ema_fast.iloc[-2] if len(ema_fast) > 1 else ema_fast_current
    ema_slow_prev = ema_slow.iloc[-2] if len(ema_slow) > 1 else ema_slow_current
    
    # Check for crossover
    signal = 0
    direction = "NONE"
    reason = "No signal"
    
    # Bullish crossover: fast crosses above slow
    if ema_fast_current > ema_slow_current and ema_fast_prev <= ema_slow_prev:
        signal = 1
        direction = "LONG"
        reason = f"EMA(9) crossed above EMA(21) - Bullish momentum"
    # Bearish crossover: fast crosses below slow
    elif ema_fast_current < ema_slow_current and ema_fast_prev >= ema_slow_prev:
        signal = -1
        direction = "SHORT"
        reason = f"EMA(9) crossed below EMA(21) - Bearish momentum"
    
    # Calculate stop loss and take profit
    if signal != 0:
        if signal == 1:  # Long
            stop_loss = current_price * (1 - STOP_PCT)
            take_profit = current_price * (1 + STOP_PCT * RR_EMA)
        else:  # Short
            stop_loss = current_price * (1 + STOP_PCT)
            take_profit = current_price * (1 - STOP_PCT * RR_EMA)
    else:
        stop_loss = 0.0
        take_profit = 0.0
    
    return {
        "signal": signal,
        "direction": direction,
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reason": reason,
        "ema_fast": ema_fast_current,
        "ema_slow": ema_slow_current,
    }


def get_bollinger_rsi_signal(df: _pd.DataFrame) -> Dict[str, any]:
    """
    Get current Bollinger Bands + RSI signal.
    
    Returns
    -------
    dict
        Contains signal information similar to get_ema_signal.
    """
    if len(df) < 20:
        return {
            "signal": 0,
            "direction": "NONE",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Insufficient data"
        }
    
    bands = bollinger_bands(df["close"], window=20, n_std=2.0)
    rsi_val = rsi(df["close"], window=14)
    
    current_price = df["close"].iloc[-1]
    lower_band = bands["lower"].iloc[-1]
    upper_band = bands["upper"].iloc[-1]
    rsi_current = rsi_val.iloc[-1]
    
    signal = 0
    direction = "NONE"
    reason = "No signal"
    
    # Oversold: price below lower band and RSI < 30
    if current_price < lower_band and rsi_current < 30:
        signal = 1
        direction = "LONG"
        reason = f"Oversold: Price below lower BB ({current_price:.2f} < {lower_band:.2f}) and RSI < 30 ({rsi_current:.1f})"
    # Overbought: price above upper band and RSI > 70
    elif current_price > upper_band and rsi_current > 70:
        signal = -1
        direction = "SHORT"
        reason = f"Overbought: Price above upper BB ({current_price:.2f} > {upper_band:.2f}) and RSI > 70 ({rsi_current:.1f})"
    
    # Calculate stop loss and take profit
    if signal != 0:
        if signal == 1:  # Long
            stop_loss = current_price * (1 - STOP_PCT)
            take_profit = current_price * (1 + STOP_PCT * RR_BB)
        else:  # Short
            stop_loss = current_price * (1 + STOP_PCT)
            take_profit = current_price * (1 - STOP_PCT * RR_BB)
    else:
        stop_loss = 0.0
        take_profit = 0.0
    
    return {
        "signal": signal,
        "direction": direction,
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reason": reason,
        "rsi": rsi_current,
        "bb_upper": upper_band,
        "bb_lower": lower_band,
    }


def get_macd_signal(df: _pd.DataFrame) -> Dict[str, any]:
    """
    Get current MACD crossover signal.
    
    Returns
    -------
    dict
        Contains signal information similar to get_ema_signal.
    """
    if len(df) < 26:
        return {
            "signal": 0,
            "direction": "NONE",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "reason": "Insufficient data"
        }
    
    macd_line = ema(df["close"], 12) - ema(df["close"], 26)
    signal_line = ema(macd_line, 9)
    
    current_price = df["close"].iloc[-1]
    macd_current = macd_line.iloc[-1]
    signal_current = signal_line.iloc[-1]
    macd_prev = macd_line.iloc[-2] if len(macd_line) > 1 else macd_current
    signal_prev = signal_line.iloc[-2] if len(signal_line) > 1 else signal_current
    
    signal = 0
    direction = "NONE"
    reason = "No signal"
    
    # Bullish crossover: MACD crosses above signal
    if macd_current > signal_current and macd_prev <= signal_prev:
        signal = 1
        direction = "LONG"
        reason = f"MACD crossed above Signal line - Bullish momentum"
    # Bearish crossover: MACD crosses below signal
    elif macd_current < signal_current and macd_prev >= signal_prev:
        signal = -1
        direction = "SHORT"
        reason = f"MACD crossed below Signal line - Bearish momentum"
    
    # Calculate stop loss and take profit
    if signal != 0:
        if signal == 1:  # Long
            stop_loss = current_price * (1 - STOP_PCT)
            take_profit = current_price * (1 + STOP_PCT * RR_MACD)
        else:  # Short
            stop_loss = current_price * (1 + STOP_PCT)
            take_profit = current_price * (1 - STOP_PCT * RR_MACD)
    else:
        stop_loss = 0.0
        take_profit = 0.0
    
    return {
        "signal": signal,
        "direction": direction,
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "reason": reason,
        "macd": macd_current,
        "signal_line": signal_current,
    }


# ----------------------------------------------------------------------
# Main signal production logic
# ----------------------------------------------------------------------

def generate_signals() -> Dict[str, Dict]:
    """
    Fetch latest data and generate signals from all strategies.
    
    Returns
    -------
    dict
        Dictionary containing signals from all strategies and current market data.
    """
    print(f"Fetching latest {TIMEFRAME} data for {SYMBOL} from {EXCHANGE_ID}...")
    try:
        df = fetch_latest_ohlcv(EXCHANGE_ID, SYMBOL, TIMEFRAME, LOOKBACK_CANDLES)
        current_price = get_current_price(EXCHANGE_ID, SYMBOL)
        
        print(f"Fetched {len(df)} candles")
        print(f"Latest candle time: {df['datetime'].iloc[-1]}")
        print(f"Current price: ${current_price:.2f}\n")
        
        # Generate signals
        ema_signal = get_ema_signal(df)
        bb_signal = get_bollinger_rsi_signal(df)
        macd_signal = get_macd_signal(df)
        
        return {
            "timestamp": datetime.now(),
            "current_price": current_price,
            "latest_candle_time": df["datetime"].iloc[-1],
            "ema": ema_signal,
            "bollinger_rsi": bb_signal,
            "macd": macd_signal,
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {}


def format_signal_message(signals: Dict[str, Dict]) -> str:
    """Format signal information as Telegram message."""
    if not signals:
        return "No signals available."
    
    message = f"<b>🚀 BTCUSDT Trading Signals</b>\n"
    message += f"⏰ Time: {signals['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"💰 Price: ${signals['current_price']:.2f}\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    strategies = [
        ("EMA(9/21) Crossover", signals.get("ema", {})),
        ("Bollinger Bands + RSI", signals.get("bollinger_rsi", {})),
        ("MACD Crossover", signals.get("macd", {})),
    ]
    
    has_signal = False
    for strategy_name, signal_data in strategies:
        if not signal_data:
            continue
        
        signal = signal_data.get('signal', 0)
        if signal != 0:
            has_signal = True
            direction = signal_data.get('direction', 'NONE')
            emoji = "🟢" if signal == 1 else "🔴"
            
            message += f"<b>{emoji} {strategy_name}</b>\n"
            message += f"📊 Signal: <b>{direction}</b>\n"
            message += f"💵 Entry: ${signal_data.get('entry_price', 0):.2f}\n"
            message += f"🛑 Stop Loss: ${signal_data.get('stop_loss', 0):.2f}\n"
            message += f"🎯 Take Profit: ${signal_data.get('take_profit', 0):.2f}\n"
            message += f"📝 Reason: {signal_data.get('reason', 'N/A')}\n"
            message += f"\n"
    
    if not has_signal:
        message += "⏸️ No trading signals at this time.\n"
    
    return message


def print_signals(signals: Dict[str, Dict]) -> None:
    """Print formatted signal output."""
    if not signals:
        print("No signals available.")
        return
    
    print("="*70)
    print(f"BTCUSDT Perpetual Futures - Trading Signals")
    print(f"Time: {signals['timestamp']}")
    print(f"Current Price: ${signals['current_price']:.2f}")
    print("="*70)
    
    strategies = [
        ("EMA(9/21) Crossover", signals.get("ema", {})),
        ("Bollinger Bands + RSI", signals.get("bollinger_rsi", {})),
        ("MACD Crossover", signals.get("macd", {})),
    ]
    
    for strategy_name, signal_data in strategies:
        if not signal_data:
            continue
            
        print(f"\n{strategy_name}:")
        print(f"  Signal: {signal_data.get('direction', 'NONE')}")
        
        if signal_data.get('signal') != 0:
            print(f"  Entry Price: ${signal_data.get('entry_price', 0):.2f}")
            print(f"  Stop Loss: ${signal_data.get('stop_loss', 0):.2f}")
            print(f"  Take Profit: ${signal_data.get('take_profit', 0):.2f}")
            print(f"  Reason: {signal_data.get('reason', 'N/A')}")
        else:
            print(f"  Reason: {signal_data.get('reason', 'No signal')}")
    
    print("\n" + "="*70)
    
    # Send Telegram notification if enabled and there are signals
    if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        # Check if any strategy has a signal
        has_signal = any(
            signal_data.get('signal', 0) != 0
            for signal_data in [signals.get("ema", {}), signals.get("bollinger_rsi", {}), signals.get("macd", {})]
        )
        
        if has_signal:
            message = format_signal_message(signals)
            success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
            if success:
                print("✓ Signal notification sent to Telegram")
            else:
                print("✗ Failed to send Telegram notification")


def run_signal_production() -> None:
    """Main function to generate and display signals."""
    # Send start notification
    if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        start_message = (
            f"<b>🤖 Signal Production Bot Started</b>\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Exchange: {EXCHANGE_ID}\n"
            f"💱 Symbol: {SYMBOL}\n"
            f"⏱️ Timeframe: {TIMEFRAME}\n"
            f"\nBot is now monitoring for trading signals..."
        )
        success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, start_message)
        if success:
            print("✓ Start notification sent to Telegram")
        else:
            print("✗ Failed to send Telegram start notification")
    
    signals = generate_signals()
    print_signals(signals)


if __name__ == "__main__":  # pragma: no cover
    run_signal_production()

