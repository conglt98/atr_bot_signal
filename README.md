# ATR Breakout Trading Strategy

A Python-based trading bot for BTCUSDT perpetual futures using ATR (Average True Range) Breakout strategy with multiple filters and optimizations.

## Project Structure

```
project_code/
├── src/                    # Source code modules
│   ├── config.py           # Configuration file (reads from .env for sensitive data)
│   └── utils.py            # Utility functions (indicators, data fetching, Telegram)
├── scripts/                # Executable scripts
│   ├── atr_breakout_production.py  # Main production script
│   ├── backtest_optimized.py      # Optimized backtesting
│   ├── backtest.py                 # Basic backtesting
│   ├── pull_data.py                # Data fetching script
│   └── optimize_*.py                # Optimization scripts
├── data/                   # Data files (CSV files, etc.)
├── logs/                   # Log files
├── docs/                   # Documentation files
├── tests/                  # Test files (if any)
├── .env                    # Environment variables (sensitive configs - NOT in git)
├── .env.example            # Example environment variables template
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
└── docker-compose.yml     # Docker Compose configuration
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your sensitive configuration:

```bash
cp .env.example .env
```

Edit `.env` file:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

**Important**: The `.env` file is in `.gitignore` and should never be committed to git.

### 3. Configure Strategy Parameters

Edit `src/config.py` to customize:
- Exchange settings (EXCHANGE_ID, SYMBOL, TIMEFRAME)
- Strategy parameters (ATR_BREAKOUT_MULTIPLIER, RSI ranges, etc.)
- Risk management (RISK_PER_TRADE, FEE_PER_TRADE)

## Usage

### Production Script

Run the main production script to generate real-time trading signals:

```bash
python scripts/atr_breakout_production.py
```

### Backtesting

Run optimized backtest:

```bash
python scripts/backtest_optimized.py
```

### Pull Historical Data

Download historical data for backtesting:

```bash
python scripts/pull_data.py
```

Data will be saved to `data/btcusdt_ohlcv.csv`.

## Docker

### Build and Run

```bash
docker-compose up --build
```

### Run in Background

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

## Configuration

### Sensitive Configuration (`.env` file)

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `TELEGRAM_CHAT_ID`: Telegram chat ID for notifications

### Strategy Configuration (`src/config.py`)

All non-sensitive configuration is in `src/config.py`:
- Exchange settings
- Strategy parameters
- Risk management
- Filter thresholds

## Notes

- The project uses `python-dotenv` to load environment variables from `.env` file
- All sensitive data (API keys, tokens) should be in `.env` file, not in `config.py`
- Logs are stored in `logs/` directory
- Data files are stored in `data/` directory
- Documentation is in `docs/` directory

## Security

⚠️ **Never commit `.env` file to git!** It contains sensitive information.

The `.gitignore` file is configured to exclude:
- `.env` files
- `__pycache__/` directories
- `*.pyc` files
- `logs/` directory
- `data/*.csv` files

