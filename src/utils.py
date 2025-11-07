"""
Utility functions for BTCUSDT scalping bot
==========================================

This module contains shared functions for indicators and data fetching
used by both backtest and signal production scripts.
"""

import datetime as _dt
from typing import Optional
import urllib.parse
import urllib.request
import ssl

import pandas as _pd

try:
    import ccxt  # type: ignore[import]
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ccxt library is required for live data retrieval. Install it with 'pip install ccxt'."
    ) from exc


# ----------------------------------------------------------------------
# Helper functions for indicators
# ----------------------------------------------------------------------

def ema(series: _pd.Series, span: int) -> _pd.Series:
    """Compute exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: _pd.Series, window: int = 14) -> _pd.Series:
    """Compute the Relative Strength Index (RSI)."""
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    gain = up.rolling(window).mean()
    loss = down.rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: _pd.Series, window: int = 20, n_std: float = 2.0) -> _pd.DataFrame:
    """Return DataFrame with Bollinger middle, upper and lower bands."""
    mid = series.rolling(window).mean()
    std = series.rolling(window).std(ddof=0)
    upper = mid + n_std * std
    lower = mid - n_std * std
    return _pd.DataFrame({"mid": mid, "upper": upper, "lower": lower})


# ----------------------------------------------------------------------
# Data retrieval
# ----------------------------------------------------------------------

def get_exchange(exchange_id: str):
    """
    Create and configure exchange instance.
    
    Parameters
    ----------
    exchange_id : str
        Name of the exchange as recognised by ccxt (e.g. "binance" or "bybit").
    
    Returns
    -------
    ccxt.Exchange
        Configured exchange instance.
    """
    exchange_class = getattr(ccxt, exchange_id)
    # For Binance, ensure we're using futures market for perpetual contracts
    if exchange_id == "binance":
        exchange = exchange_class({
            'options': {
                'defaultType': 'future',  # Use futures market for perpetual contracts
            }
        })
    else:
        exchange = exchange_class()
    return exchange


def fetch_historical_ohlcv(
    exchange_id: str, symbol: str, timeframe: str, days: int
) -> _pd.DataFrame:
    """
    Download historical OHLCV data from the specified exchange using ccxt.

    Parameters
    ----------
    exchange_id : str
        Name of the exchange as recognised by ccxt (e.g. "binance" or "bybit").
    symbol : str
        Trading pair symbol (e.g. "BTC/USDT" for spot or "BTC/USDT:USDT" for perpetual futures).
    timeframe : str
        Candle interval (e.g. "1m", "5m").
    days : int
        Number of days of data to fetch.  ccxt may limit the number of
        candles returned per request, so the function loops backward in
        batches of up to 1000 candles until the requested lookback is covered.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``datetime``, ``open``, ``high``, ``low``,
        ``close`` and ``volume``.  The index is not set.
    """
    exchange = get_exchange(exchange_id)

    # Calculate start timestamp in milliseconds
    now_ms = int(_dt.datetime.utcnow().timestamp() * 1000)
    since_ms = now_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    while since_ms < now_ms:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=1000)
        if not ohlcv:
            break
        last_ts = ohlcv[-1][0]
        all_data.extend(ohlcv)
        # advance since pointer to last candle + 1 ms
        since_ms = last_ts + 1
        # safety break to avoid infinite loop
        if len(ohlcv) < 1000:
            break

    # convert to DataFrame
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    df = _pd.DataFrame(all_data, columns=cols)
    df["datetime"] = _pd.to_datetime(df["timestamp"], unit="ms")
    return df[["datetime", "open", "high", "low", "close", "volume"]].copy()


def fetch_latest_ohlcv(
    exchange_id: str, symbol: str, timeframe: str, limit: int = 200
) -> _pd.DataFrame:
    """
    Fetch the most recent OHLCV candles for signal generation.

    Parameters
    ----------
    exchange_id : str
        Name of the exchange as recognised by ccxt (e.g. "binance" or "bybit").
    symbol : str
        Trading pair symbol (e.g. "BTC/USDT:USDT" for perpetual futures).
    timeframe : str
        Candle interval (e.g. "1m", "5m").
    limit : int
        Number of recent candles to fetch (default: 200 for indicator calculation).

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``datetime``, ``open``, ``high``, ``low``,
        ``close`` and ``volume``, sorted by datetime ascending.
    """
    exchange = get_exchange(exchange_id)
    
    # Fetch recent candles
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    
    if not ohlcv:
        raise ValueError(f"No data returned from {exchange_id} for {symbol}")
    
    # convert to DataFrame
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    df = _pd.DataFrame(ohlcv, columns=cols)
    df["datetime"] = _pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["datetime", "open", "high", "low", "close", "volume"]].copy()
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def get_current_price(exchange_id: str, symbol: str) -> float:
    """
    Get the current ticker price for the symbol.

    Parameters
    ----------
    exchange_id : str
        Name of the exchange as recognised by ccxt.
    symbol : str
        Trading pair symbol.

    Returns
    -------
    float
        Current price.
    """
    exchange = get_exchange(exchange_id)
    ticker = exchange.fetch_ticker(symbol)
    return float(ticker["last"])


# ----------------------------------------------------------------------
# Telegram notification
# ----------------------------------------------------------------------

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Send a message to Telegram bot.
    
    Parameters
    ----------
    bot_token : str
        Telegram bot token from BotFather.
    chat_id : str
        Telegram chat ID to send message to.
    message : str
        Message text to send.
    
    Returns
    -------
    bool
        True if message sent successfully, False otherwise.
    """
    if not bot_token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        request = urllib.request.Request(url, data=data_encoded)
        
        # Create SSL context that doesn't verify certificates (for environments with proxy/self-signed certs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

