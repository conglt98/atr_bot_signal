"""
Configuration File for ATR Breakout Strategy
===========================================

This file contains all configuration parameters for the ATR Breakout trading strategy.
Modify these values to customize the strategy behavior.

IMPORTANT: 
- Sensitive configuration (Telegram tokens) should be set in .env file
- After modifying this file, restart the production script for changes to take effect.
- Load environment variables from .env file using python-dotenv (install: pip install python-dotenv)
"""

import os
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env in project root (parent of src/)
    config_file_path = Path(__file__).parent  # src/
    project_root = config_file_path.parent     # project root
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, continue without it
    pass

# ============================================================================
# EXCHANGE CONFIGURATION
# ============================================================================

# Exchange ID (supported: "binance", "bybit")
# This determines which exchange to fetch data from
EXCHANGE_ID: str = "binance"

# Trading pair symbol
# Format: "BTC/USDT:USDT" for perpetual futures on Binance
# Format: "BTCUSDT" for perpetual futures on Bybit
SYMBOL: str = "BTC/USDT:USDT"

# Timeframe for candles
# Options: "1m", "5m", "15m", "1h", "4h", "1d"
# Note: Strategy optimized for "1m" timeframe
TIMEFRAME: str = "1m"

# Number of historical candles to fetch for indicator calculation
# Recommended: 200-500 candles (more = more accurate but slower)
LOOKBACK_CANDLES: int = 200


# ============================================================================
# ATR BREAKOUT STRATEGY PARAMETERS
# ============================================================================

# ATR Breakout Multiplier (k)
# This determines how far price must break above/below EMA20 to trigger a signal
# Higher value = stronger breakout required = fewer but better signals
# Lower value = weaker breakout accepted = more signals but potentially lower quality
# Optimized value: 1.2
# Range: 0.5 - 2.0
ATR_BREAKOUT_MULTIPLIER: float = 1.2

# Risk:Reward Ratio
# This is the ratio of take profit distance to stop loss distance
# Example: R:R = 3.5 means if you risk $1, you aim to make $3.50
# Higher R:R = need higher win rate, but bigger profits when you win
# Lower R:R = can win with lower win rate, but smaller profits
# Optimized value: 3.5 (requires ~22.2% win rate to break even, tested: $111.01 profit)
# Previous value: 2.5 (tested: $54.70 profit)
# Range: 1.0 - 5.0
ATR_TP_RR: float = 3.5

# Stop Loss Multiplier
# Stop loss distance in terms of ATR
# Example: 1.0 means stop loss is 1× ATR away from entry
# Higher value = wider stop loss = less likely to be stopped out, but bigger losses
# Lower value = tighter stop loss = more likely to be stopped out, but smaller losses
# Optimized value: 1.0
# Range: 0.5 - 2.0
ATR_SL_MULTIPLIER: float = 1.0


# ============================================================================
# RSI FILTER PARAMETERS
# ============================================================================

# RSI Range for LONG signals
# Only enter LONG when RSI is between these values
# Higher min = stronger momentum required
# Lower max = avoid overbought conditions
# Optimized: 55-65 (balanced momentum, not too extreme)
# Range: 50-70 (typical), 55-65 (stricter), 50-60 (very strict)
RSI_LONG_MIN: float = 55
RSI_LONG_MAX: float = 65

# RSI Range for SHORT signals
# Only enter SHORT when RSI is between these values
# Lower max = stronger momentum required
# Higher min = avoid oversold conditions
# Optimized: 35-45 (balanced momentum, not too extreme)
# Range: 30-50 (typical), 35-45 (stricter), 40-50 (very strict)
RSI_SHORT_MIN: float = 35
RSI_SHORT_MAX: float = 45


# ============================================================================
# VOLUME FILTER PARAMETERS
# ============================================================================

# Volume Multiplier
# Only trade when current volume is at least this many times the average volume
# Higher value = stricter filter = fewer signals but higher quality
# Lower value = looser filter = more signals but potentially lower quality
# Optimized value: 2.5 (volume must be 250% of average)
# Range: 1.0 - 5.0
# Note: 1.0 = no filter, 2.5 = very strict, 5.0 = extremely strict
VOLUME_MULTIPLIER: float = 2.5


# ============================================================================
# ADX FILTER PARAMETERS
# ============================================================================

# ADX Threshold
# ADX (Average Directional Index) measures trend strength
# Only trade when ADX is above this threshold (strong trend)
# Higher value = only trade in very strong trends = fewer but better signals
# Lower value = trade in weaker trends = more signals but potentially lower quality
# Optimized value: 25 (strong trend)
# Range: 20-40
# Note: ADX < 20 = weak/no trend, ADX 20-25 = moderate trend, ADX > 25 = strong trend
ADX_THRESHOLD: float = 25


# ============================================================================
# RISK MANAGEMENT PARAMETERS
# ============================================================================

# Risk per trade in USD
# This is the maximum amount you're willing to lose per trade
# The position size will be calculated to ensure you never lose more than this
# Example: $5 means you risk $5 per trade
# Adjust based on your account size and risk tolerance
# Recommended: 1-5% of account balance
RISK_PER_TRADE: float = 5.0

# Trading fee per round-trip trade (entry + exit)
# This is subtracted from each trade's profit/loss
# Binance Futures: ~$1.2-1.5 per round trip for small trades
# Bybit: ~$1.0-1.3 per round trip
# Adjust based on your exchange and trading volume
FEE_PER_TRADE: float = 1.4


# ============================================================================
# OTHER STRATEGY PARAMETERS (for backtesting)
# ============================================================================

# Stop loss as percentage of entry price (for other strategies, not ATR Breakout)
# ATR Breakout uses ATR-based stop loss, not percentage-based
# This is used by EMA, Bollinger, MACD strategies
STOP_PCT: float = 0.0020  # 0.20%

# Reward:Risk ratios for other strategies
RR_EMA: float = 2.5      # EMA strategy R:R
RR_BB: float = 2.0        # Bollinger+RSI strategy R:R
RR_MACD: float = 2.5      # MACD strategy R:R

# Filter parameters for other strategies
MIN_VOLUME_MULTIPLIER: float = 1.5  # Volume filter for other strategies
MIN_ADX: float = 30.0               # ADX filter for other strategies
MIN_ATR_PCT: float = 0.0015         # ATR volatility filter (0.15%)


# ============================================================================
# BACKTEST CONFIGURATION
# ============================================================================

# Number of days of historical data to backtest
# More days = more data but slower backtest
# Recommended: 30-90 days
LOOKBACK_DAYS: int = 30

# CSV file to load data from (for backtesting)
# Set to None to fetch from exchange API
# If file exists, backtest will use it instead of fetching
# Path is relative to project root
DATA_FILE: str = "data/btcusdt_ohlcv.csv"


# ============================================================================
# PRODUCTION SCRIPT CONFIGURATION
# ============================================================================

# Update interval in seconds
# How often to fetch new data and check for signals
# Recommended: 60 seconds (1 minute) for 1m timeframe
# For 5m timeframe, you can use 300 seconds (5 minutes)
UPDATE_INTERVAL: int = 60

# Enable/disable screen clearing
# If True, screen will be cleared before each update (cleaner display)
# If False, new data will append to screen (see history)
CLEAR_SCREEN: bool = True

# Signal logging configuration
# Path to log file for signals (relative to project root)
# Signals will be logged in JSON format for easy parsing
SIGNAL_LOG_FILE: str = "logs/signals.log"

# Enable signal logging
# If True, signals will be logged to file when detected
# If False, signals will only be displayed on screen
ENABLE_SIGNAL_LOGGING: bool = True


# ============================================================================
# TELEGRAM NOTIFICATION CONFIGURATION
# ============================================================================

# Telegram bot token from BotFather
# Load from environment variable or use default (for backward compatibility)
# IMPORTANT: Set TELEGRAM_BOT_TOKEN in .env file for production
TELEGRAM_BOT_TOKEN: str = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "xxx"  # Default for backward compatibility
)

# Telegram chat ID to send notifications to
# Get it from: https://api.telegram.org/bot<TOKEN>/getUpdates
# IMPORTANT: Set TELEGRAM_CHAT_ID in .env file for production
TELEGRAM_CHAT_ID: str = os.getenv(
    "TELEGRAM_CHAT_ID",
    "yyy"  # Default for backward compatibility
)

# Enable Telegram notifications
# Set to True to receive notifications when bot starts and when signals are detected
ENABLE_TELEGRAM: bool = True


# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

# EMA Periods for trend filter
# EMA20 and EMA50 are used to determine trend direction
# EMA20 > EMA50 = uptrend (only LONG signals)
# EMA20 < EMA50 = downtrend (only SHORT signals)
# These values are optimized for 1-minute scalping
# For longer timeframes, you might want to use EMA50/EMA200
EMA_FAST_PERIOD: int = 20
EMA_SLOW_PERIOD: int = 50

# ATR Period
# Period for calculating Average True Range
# Standard: 14 (most common)
# Higher = smoother ATR, Lower = more responsive ATR
ATR_PERIOD: int = 14

# RSI Period
# Period for calculating Relative Strength Index
# Standard: 14 (most common)
# Higher = smoother RSI, Lower = more responsive RSI
RSI_PERIOD: int = 14

# ADX Period
# Period for calculating Average Directional Index
# Standard: 14 (most common)
# Higher = smoother ADX, Lower = more responsive ADX
ADX_PERIOD: int = 14

# Volume SMA Period
# Period for calculating volume moving average
# Used to compare current volume with average
# Standard: 20 (most common)
VOLUME_SMA_PERIOD: int = 20


# ============================================================================
# NOTES
# ============================================================================

"""
OPTIMIZATION RESULTS:
---------------------
These parameters were optimized through comprehensive backtesting on 30 days of data.

Best Configuration:
- ATR Breakout Multiplier: 1.2
- R:R Ratio: 2.5:1
- RSI Long: 55-65
- RSI Short: 35-45
- Volume Multiplier: 2.5×
- ADX Threshold: 25

Performance:
- Total P/L: +$54.70 (best performing strategy)
- Win Rate: 36.30%
- Trades: 135
- Avg Win: $16.83
- Avg Loss: -$8.96
- Profit Factor: 1.88

RECOMMENDATIONS:
----------------
1. Start with default optimized values
2. Forward test on demo account for at least 1 month
3. Adjust parameters based on your risk tolerance:
   - Conservative: Increase filters (volume, ADX), increase R:R
   - Aggressive: Decrease filters, decrease R:R
4. Monitor performance and adjust as needed
5. Never risk more than you can afford to lose

WARNING:
--------
Past performance does not guarantee future results.
Always test on demo account before using real money.
"""

