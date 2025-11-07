"""
ATR Breakout Strategy - Production Script
=========================================

Real-time trading signal generator for ATR Breakout strategy.
Fetches live data and displays signals with professional formatting.

Usage
-----
    python atr_breakout_production.py

The script will continuously fetch data and display signals.
Press Ctrl+C to stop.
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import pandas as _pd
import numpy as _np

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = RESET = ''
    class Back:
        RED = GREEN = YELLOW = BLUE = RESET = ''
    class Style:
        BRIGHT = DIM = RESET_ALL = RESET = ''

from utils import (
    fetch_latest_ohlcv,
    get_current_price,
    ema,
    rsi,
    send_telegram_message,
)

from backtest_optimized import (
    adx,
    atr,
    sma,
)

# Import configuration
from config import (
    # Exchange config
    EXCHANGE_ID,
    SYMBOL,
    TIMEFRAME,
    LOOKBACK_CANDLES,
    # Strategy parameters
    ATR_BREAKOUT_MULTIPLIER,
    ATR_SL_MULTIPLIER,
    ATR_TP_RR,
    RSI_LONG_MIN,
    RSI_LONG_MAX,
    RSI_SHORT_MIN,
    RSI_SHORT_MAX,
    VOLUME_MULTIPLIER,
    ADX_THRESHOLD,
    # EMA periods
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
    # Production config
    UPDATE_INTERVAL,
    CLEAR_SCREEN,
    # Logging config
    SIGNAL_LOG_FILE,
    ENABLE_SIGNAL_LOGGING,
    # Telegram config
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    ENABLE_TELEGRAM,
)


def clear_screen():
    """Clear terminal screen if enabled in config."""
    if CLEAR_SCREEN:
        os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print header with strategy info."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}")
    print(f"{Fore.CYAN}{Style.BRIGHT}ATR BREAKOUT STRATEGY - PRODUCTION MODE")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
    print(f"{Fore.WHITE}Symbol: {Fore.YELLOW}{SYMBOL}")
    print(f"{Fore.WHITE}Timeframe: {Fore.YELLOW}{TIMEFRAME}")
    print(f"{Fore.WHITE}Exchange: {Fore.YELLOW}{EXCHANGE_ID.upper()}")
    print(f"{Fore.CYAN}{'='*80}\n")


def print_separator(color=Fore.CYAN):
    """Print separator line."""
    print(f"{color}{'-'*80}{Style.RESET_ALL}")


def format_price(price: float) -> str:
    """Format price with 2 decimal places."""
    return f"${price:,.2f}"


def format_percent(value: float) -> str:
    """Format percentage."""
    return f"{value:.2f}%"


def get_signal_info(df: _pd.DataFrame) -> Dict:
    """
    Calculate indicators and generate signal information.
    
    Returns dict with all signal data.
    """
    if len(df) < 50:
        return {
            "error": "Insufficient data",
            "signal": 0,
        }
    
    # Calculate indicators
    ema20 = ema(df["close"], EMA_FAST_PERIOD)
    ema50 = ema(df["close"], EMA_SLOW_PERIOD)
    atr_val = atr(df["high"], df["low"], df["close"], 14)
    rsi_val = rsi(df["close"], window=14)
    volume_sma = sma(df["volume"], 20)
    adx_val = adx(df["high"], df["low"], df["close"], 14)
    
    # Get latest values
    i = len(df) - 1
    
    if (_pd.isna(ema20.iloc[i]) or _pd.isna(ema50.iloc[i]) or 
        _pd.isna(atr_val.iloc[i]) or _pd.isna(rsi_val.iloc[i]) or
        _pd.isna(volume_sma.iloc[i]) or _pd.isna(adx_val.iloc[i])):
        return {
            "error": "NaN values in indicators",
            "signal": 0,
        }
    
    current_price = df["close"].iloc[i]
    ema20_current = ema20.iloc[i]
    ema50_current = ema50.iloc[i]
    atr_current = atr_val.iloc[i]
    rsi_current = rsi_val.iloc[i]
    volume_current = df["volume"].iloc[i]
    adx_current = adx_val.iloc[i]
    volume_avg = volume_sma.iloc[i]
    
    # Calculate breakout levels
    breakout_long = ema20_current + (ATR_BREAKOUT_MULTIPLIER * atr_current)
    breakout_short = ema20_current - (ATR_BREAKOUT_MULTIPLIER * atr_current)
    
    # Check filters
    volume_ok = volume_current >= volume_avg * VOLUME_MULTIPLIER
    adx_ok = adx_current >= ADX_THRESHOLD
    
    # Determine trend
    trend = "UPTREND" if ema20_current > ema50_current else "DOWNTREND" if ema20_current < ema50_current else "SIDEWAYS"
    
    # Generate signal
    signal = 0
    signal_reason = ""
    direction = "NONE"
    
    if ema20_current > ema50_current:  # Uptrend
        if current_price > breakout_long:
            if RSI_LONG_MIN < rsi_current < RSI_LONG_MAX:
                if volume_ok and adx_ok:
                    signal = 1
                    direction = "LONG"
                    signal_reason = f"Price broke above EMA20 + {ATR_BREAKOUT_MULTIPLIER}×ATR with RSI {rsi_current:.1f}"
                else:
                    signal_reason = "Breakout detected but filters failed (Volume or ADX)"
            else:
                signal_reason = f"Breakout detected but RSI {rsi_current:.1f} not in range ({RSI_LONG_MIN}-{RSI_LONG_MAX})"
        else:
            signal_reason = f"Waiting for breakout above {format_price(breakout_long)}"
    elif ema20_current < ema50_current:  # Downtrend
        if current_price < breakout_short:
            if RSI_SHORT_MIN < rsi_current < RSI_SHORT_MAX:
                if volume_ok and adx_ok:
                    signal = -1
                    direction = "SHORT"
                    signal_reason = f"Price broke below EMA20 - {ATR_BREAKOUT_MULTIPLIER}×ATR with RSI {rsi_current:.1f}"
                else:
                    signal_reason = "Breakout detected but filters failed (Volume or ADX)"
            else:
                signal_reason = f"Breakout detected but RSI {rsi_current:.1f} not in range ({RSI_SHORT_MIN}-{RSI_SHORT_MAX})"
        else:
            signal_reason = f"Waiting for breakout below {format_price(breakout_short)}"
    else:  # Sideways
        signal_reason = "EMA20 ≈ EMA50 - No clear trend"
    
    # Calculate stop loss and take profit
    if signal != 0:
        if signal == 1:  # Long
            stop_loss = current_price - (ATR_SL_MULTIPLIER * atr_current)
            take_profit = current_price + (ATR_TP_RR * atr_current)
        else:  # Short
            stop_loss = current_price + (ATR_SL_MULTIPLIER * atr_current)
            take_profit = current_price - (ATR_TP_RR * atr_current)
    else:
        stop_loss = None
        take_profit = None
    
    return {
        "signal": signal,
        "direction": direction,
        "signal_reason": signal_reason,
        "current_price": current_price,
        "ema20": ema20_current,
        "ema50": ema50_current,
        "atr": atr_current,
        "rsi": rsi_current,
        "adx": adx_current,
        "volume": volume_current,
        "volume_avg": volume_avg,
        "volume_ratio": volume_current / volume_avg if volume_avg > 0 else 0,
        "trend": trend,
        "breakout_long": breakout_long,
        "breakout_short": breakout_short,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "volume_ok": volume_ok,
        "adx_ok": adx_ok,
        "latest_candle_time": df["datetime"].iloc[i],
    }


def print_market_data(info: Dict):
    """Print current market data."""
    print(f"{Fore.CYAN}{Style.BRIGHT}📊 MARKET DATA")
    print_separator(Fore.CYAN)
    print(f"{Fore.WHITE}Time: {Fore.YELLOW}{info['latest_candle_time']}")
    print(f"{Fore.WHITE}Current Price: {Fore.YELLOW}{Style.BRIGHT}{format_price(info['current_price'])}")
    print(f"{Fore.WHITE}Trend: {Fore.GREEN if info['trend'] == 'UPTREND' else Fore.RED if info['trend'] == 'DOWNTREND' else Fore.YELLOW}{info['trend']}")
    print()


def print_indicators(info: Dict):
    """Print technical indicators."""
    print(f"{Fore.CYAN}{Style.BRIGHT}📈 TECHNICAL INDICATORS")
    print_separator(Fore.CYAN)
    
    # EMA
    ema_color = Fore.GREEN if info['ema20'] > info['ema50'] else Fore.RED
    print(f"{Fore.WHITE}EMA20: {Fore.YELLOW}{format_price(info['ema20'])}")
    print(f"{Fore.WHITE}EMA50: {Fore.YELLOW}{format_price(info['ema50'])}")
    print(f"{Fore.WHITE}EMA Relationship: {ema_color}{'EMA20 > EMA50' if info['ema20'] > info['ema50'] else 'EMA20 < EMA50' if info['ema20'] < info['ema50'] else 'EMA20 ≈ EMA50'}")
    
    # ATR
    print(f"{Fore.WHITE}ATR: {Fore.YELLOW}{format_price(info['atr'])}")
    print(f"{Fore.WHITE}Breakout Long Level: {Fore.GREEN}{format_price(info['breakout_long'])}")
    print(f"{Fore.WHITE}Breakout Short Level: {Fore.RED}{format_price(info['breakout_short'])}")
    
    # RSI
    rsi_color = Fore.RED if info['rsi'] > 70 else Fore.GREEN if info['rsi'] < 30 else Fore.YELLOW
    print(f"{Fore.WHITE}RSI: {rsi_color}{info['rsi']:.2f}")
    print(f"{Fore.WHITE}RSI Range (Long): {Fore.YELLOW}{RSI_LONG_MIN}-{RSI_LONG_MAX}")
    print(f"{Fore.WHITE}RSI Range (Short): {Fore.YELLOW}{RSI_SHORT_MIN}-{RSI_SHORT_MAX}")
    
    # ADX
    adx_color = Fore.GREEN if info['adx'] >= ADX_THRESHOLD else Fore.RED
    adx_status = "✓ PASS" if info['adx_ok'] else "✗ FAIL"
    print(f"{Fore.WHITE}ADX: {adx_color}{info['adx']:.2f} {adx_status} (Threshold: {ADX_THRESHOLD})")
    
    # Volume
    volume_color = Fore.GREEN if info['volume_ok'] else Fore.RED
    volume_status = "✓ PASS" if info['volume_ok'] else "✗ FAIL"
    print(f"{Fore.WHITE}Volume: {Fore.YELLOW}{info['volume']:,.0f}")
    print(f"{Fore.WHITE}Volume Avg: {Fore.YELLOW}{info['volume_avg']:,.0f}")
    print(f"{Fore.WHITE}Volume Ratio: {volume_color}{info['volume_ratio']:.2f}× {volume_status} (Required: {VOLUME_MULTIPLIER}×)")
    
    print()


def log_signal_to_file(info: Dict, log_file: str = None):
    """
    Log signal to file with full details for tracing.
    
    Parameters
    ----------
    info : Dict
        Signal information dictionary
    log_file : str
        Path to log file (uses SIGNAL_LOG_FILE from config if not provided)
    """
    if not ENABLE_SIGNAL_LOGGING:
        return
    
    if info['signal'] == 0:
        return  # Only log when there's an actual signal
    
    if log_file is None:
        log_file = SIGNAL_LOG_FILE
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "candle_time": info['latest_candle_time'].isoformat() if hasattr(info['latest_candle_time'], 'isoformat') else str(info['latest_candle_time']),
        "signal": {
            "type": info['direction'],
            "value": info['signal'],
        },
        "price": {
            "current": info['current_price'],
            "entry": info['current_price'],
            "stop_loss": info['stop_loss'],
            "take_profit": info['take_profit'],
        },
        "indicators": {
            "ema20": info['ema20'],
            "ema50": info['ema50'],
            "atr": info['atr'],
            "rsi": info['rsi'],
            "adx": info['adx'],
        },
        "breakout_levels": {
            "long": info['breakout_long'],
            "short": info['breakout_short'],
        },
        "filters": {
            "volume_ok": info['volume_ok'],
            "adx_ok": info['adx_ok'],
            "volume": info['volume'],
            "volume_avg": info['volume_avg'],
            "volume_ratio": info['volume_ratio'],
        },
        "trend": info['trend'],
        "risk_reward": {
            "ratio": ATR_TP_RR,
            "stop_loss_distance": abs(info['stop_loss'] - info['current_price']),
            "take_profit_distance": abs(info['take_profit'] - info['current_price']),
            "stop_loss_pct": abs((info['stop_loss'] - info['current_price']) / info['current_price'] * 100),
            "take_profit_pct": abs((info['take_profit'] - info['current_price']) / info['current_price'] * 100),
        },
        "strategy_params": {
            "atr_breakout_multiplier": ATR_BREAKOUT_MULTIPLIER,
            "atr_sl_multiplier": ATR_SL_MULTIPLIER,
            "atr_tp_rr": ATR_TP_RR,
            "rsi_long_min": RSI_LONG_MIN,
            "rsi_long_max": RSI_LONG_MAX,
            "rsi_short_min": RSI_SHORT_MIN,
            "rsi_short_max": RSI_SHORT_MAX,
            "volume_multiplier": VOLUME_MULTIPLIER,
            "adx_threshold": ADX_THRESHOLD,
        },
        "signal_reason": info['signal_reason'],
    }
    
    # Append to log file (JSON format for easy parsing)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, indent=2, default=str) + '\n')
            f.write("\n" + "="*80 + "\n\n")
    except Exception as e:
        print(f"{Fore.RED}Error logging signal: {e}{Style.RESET_ALL}")


def format_signal_telegram_message(info: Dict) -> str:
    """Format signal information as Telegram message."""
    signal = info['signal']
    direction = info['direction']
    
    message = f"<b>🚀 ATR BREAKOUT SIGNAL</b>\n"
    message += f"⏰ Time: {info['latest_candle_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"💰 Price: {format_price(info['current_price'])}\n"
    message += f"📊 Trend: {info['trend']}\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if signal == 1:  # LONG signal
        message += f"<b>🟢 LONG SIGNAL - BUY NOW</b>\n\n"
        message += f"💵 Entry: {format_price(info['current_price'])}\n"
        message += f"🛑 Stop Loss: {format_price(info['stop_loss'])} ({format_percent((info['stop_loss'] - info['current_price']) / info['current_price'] * 100)})\n"
        message += f"🎯 Take Profit: {format_price(info['take_profit'])} ({format_percent((info['take_profit'] - info['current_price']) / info['current_price'] * 100)})\n"
        message += f"⚖️ Risk:Reward = 1:{ATR_TP_RR}\n\n"
        message += f"<b>📈 Indicators:</b>\n"
        message += f"• EMA20: {format_price(info['ema20'])}\n"
        message += f"• EMA50: {format_price(info['ema50'])}\n"
        message += f"• ATR: {format_price(info['atr'])}\n"
        message += f"• RSI: {info['rsi']:.2f}\n"
        message += f"• ADX: {info['adx']:.2f}\n"
        message += f"• Volume: {info['volume']:,.0f} ({info['volume_ratio']:.2f}× avg)\n\n"
        message += f"📝 {info['signal_reason']}\n"
        
    elif signal == -1:  # SHORT signal
        message += f"<b>🔴 SHORT SIGNAL - SELL NOW</b>\n\n"
        message += f"💵 Entry: {format_price(info['current_price'])}\n"
        message += f"🛑 Stop Loss: {format_price(info['stop_loss'])} ({format_percent((info['stop_loss'] - info['current_price']) / info['current_price'] * 100)})\n"
        message += f"🎯 Take Profit: {format_price(info['take_profit'])} ({format_percent((info['take_profit'] - info['current_price']) / info['current_price'] * 100)})\n"
        message += f"⚖️ Risk:Reward = 1:{ATR_TP_RR}\n\n"
        message += f"<b>📈 Indicators:</b>\n"
        message += f"• EMA20: {format_price(info['ema20'])}\n"
        message += f"• EMA50: {format_price(info['ema50'])}\n"
        message += f"• ATR: {format_price(info['atr'])}\n"
        message += f"• RSI: {info['rsi']:.2f}\n"
        message += f"• ADX: {info['adx']:.2f}\n"
        message += f"• Volume: {info['volume']:,.0f} ({info['volume_ratio']:.2f}× avg)\n\n"
        message += f"📝 {info['signal_reason']}\n"
    
    return message


def print_signal(info: Dict):
    """Print trading signal with highlight."""
    print(f"{Fore.CYAN}{Style.BRIGHT}🎯 TRADING SIGNAL")
    print_separator(Fore.CYAN)
    
    signal = info['signal']
    direction = info['direction']
    
    if signal == 1:  # LONG signal
        print(f"{Back.GREEN}{Fore.WHITE}{Style.BRIGHT}{' '*20}LONG SIGNAL{' '*20}")
        print(f"{Back.GREEN}{Fore.WHITE}{Style.BRIGHT}{' '*20}BUY NOW{' '*20}")
        print()
        print(f"{Fore.GREEN}{Style.BRIGHT}Entry Price: {format_price(info['current_price'])}")
        print(f"{Fore.RED}Stop Loss: {format_price(info['stop_loss'])} ({format_percent((info['stop_loss'] - info['current_price']) / info['current_price'] * 100)})")
        print(f"{Fore.GREEN}Take Profit: {format_price(info['take_profit'])} ({format_percent((info['take_profit'] - info['current_price']) / info['current_price'] * 100)})")
        print(f"{Fore.YELLOW}Risk:Reward = 1:{ATR_TP_RR}")
        
        # Log to file
        if ENABLE_SIGNAL_LOGGING:
            log_signal_to_file(info)
            print(f"{Fore.CYAN}✓ Signal logged to {SIGNAL_LOG_FILE}{Style.RESET_ALL}")
        
        # Send Telegram notification
        if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            message = format_signal_telegram_message(info)
            success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
            if success:
                print(f"{Fore.CYAN}✓ Signal notification sent to Telegram{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Failed to send Telegram notification{Style.RESET_ALL}")
        
    elif signal == -1:  # SHORT signal
        print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{' '*20}SHORT SIGNAL{' '*20}")
        print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}{' '*20}SELL NOW{' '*20}")
        print()
        print(f"{Fore.RED}{Style.BRIGHT}Entry Price: {format_price(info['current_price'])}")
        print(f"{Fore.GREEN}Stop Loss: {format_price(info['stop_loss'])} ({format_percent((info['stop_loss'] - info['current_price']) / info['current_price'] * 100)})")
        print(f"{Fore.RED}Take Profit: {format_price(info['take_profit'])} ({format_percent((info['take_profit'] - info['current_price']) / info['current_price'] * 100)})")
        print(f"{Fore.YELLOW}Risk:Reward = 1:{ATR_TP_RR}")
        
        # Log to file
        if ENABLE_SIGNAL_LOGGING:
            log_signal_to_file(info)
            print(f"{Fore.CYAN}✓ Signal logged to {SIGNAL_LOG_FILE}{Style.RESET_ALL}")
        
        # Send Telegram notification
        if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            message = format_signal_telegram_message(info)
            success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
            if success:
                print(f"{Fore.CYAN}✓ Signal notification sent to Telegram{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Failed to send Telegram notification{Style.RESET_ALL}")
        
    else:  # No signal
        print(f"{Fore.YELLOW}{Style.BRIGHT}No Signal")
        print(f"{Fore.WHITE}Status: {Style.DIM}{info['signal_reason']}{Style.RESET_ALL}")
    
    print()


def print_strategy_params():
    """Print strategy parameters."""
    print(f"{Fore.CYAN}{Style.BRIGHT}⚙️  STRATEGY PARAMETERS")
    print_separator(Fore.CYAN)
    print(f"{Fore.WHITE}ATR Breakout Multiplier (k): {Fore.YELLOW}{ATR_BREAKOUT_MULTIPLIER}")
    print(f"{Fore.WHITE}R:R Ratio: {Fore.YELLOW}{ATR_TP_RR}:1")
    print(f"{Fore.WHITE}RSI Long Range: {Fore.YELLOW}{RSI_LONG_MIN}-{RSI_LONG_MAX}")
    print(f"{Fore.WHITE}RSI Short Range: {Fore.YELLOW}{RSI_SHORT_MIN}-{RSI_SHORT_MAX}")
    print(f"{Fore.WHITE}Volume Multiplier: {Fore.YELLOW}{VOLUME_MULTIPLIER}×")
    print(f"{Fore.WHITE}ADX Threshold: {Fore.YELLOW}{ADX_THRESHOLD}")
    print(f"{Fore.WHITE}Stop Loss: {Fore.YELLOW}{ATR_SL_MULTIPLIER}× ATR")
    print()


def run_production():
    """Main production loop."""
    # Send start notification
    if ENABLE_TELEGRAM and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        start_message = (
            f"<b>🤖 ATR Breakout Bot Started</b>\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Exchange: {EXCHANGE_ID.upper()}\n"
            f"💱 Symbol: {SYMBOL}\n"
            f"⏱️ Timeframe: {TIMEFRAME}\n"
            f"\n<b>Strategy Parameters:</b>\n"
            f"• ATR Breakout Multiplier: {ATR_BREAKOUT_MULTIPLIER}\n"
            f"• R:R Ratio: {ATR_TP_RR}:1\n"
            f"• RSI Long: {RSI_LONG_MIN}-{RSI_LONG_MAX}\n"
            f"• RSI Short: {RSI_SHORT_MIN}-{RSI_SHORT_MAX}\n"
            f"• Volume Multiplier: {VOLUME_MULTIPLIER}×\n"
            f"• ADX Threshold: {ADX_THRESHOLD}\n"
            f"\nBot is now monitoring for trading signals..."
        )
        success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, start_message)
        if success:
            print(f"{Fore.GREEN}✓ Start notification sent to Telegram{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Failed to send Telegram start notification{Style.RESET_ALL}")
    
    print_header()
    print_strategy_params()
    
    print(f"{Fore.YELLOW}Fetching real-time data...")
    print(f"{Style.DIM}Press Ctrl+C to stop{Style.RESET_ALL}\n")
    
    try:
        while True:
            try:
                # Fetch latest data
                df = fetch_latest_ohlcv(EXCHANGE_ID, SYMBOL, TIMEFRAME, LOOKBACK_CANDLES)
                current_price = get_current_price(EXCHANGE_ID, SYMBOL)
                
                # Calculate signal
                info = get_signal_info(df)
                
                if "error" in info:
                    print(f"{Fore.RED}Error: {info['error']}")
                    time.sleep(10)
                    continue
                
                # Clear screen and print
                clear_screen()
                print_header()
                
                # Print all information
                print_market_data(info)
                print_indicators(info)
                print_signal(info)
                print_strategy_params()
                
                # Print footer
                print_separator(Fore.CYAN)
                print(f"{Style.DIM}Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
                print(f"{Style.DIM}Next update in {UPDATE_INTERVAL} seconds... (Press Ctrl+C to stop){Style.RESET_ALL}")
                
                # Wait for next update (configurable)
                time.sleep(UPDATE_INTERVAL)
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}Stopping...")
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {e}")
                print(f"{Fore.YELLOW}Retrying in 10 seconds...")
                time.sleep(10)
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Script stopped by user.")
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_production()

