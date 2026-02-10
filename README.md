# Binance Futures Trading Bot

A command-line trading bot for **Binance USDT-M Futures** built in Python. Supports multiple order types including market, limit, stop-limit, OCO, TWAP, and grid trading strategies — plus historical trade analysis and Fear & Greed Index integration. All with comprehensive logging, input validation, and error handling.

> ⚠️ **DISCLAIMER**: This bot is for **educational purposes only**. Always use the **Testnet** for development and testing. Trading cryptocurrency futures involves significant risk of loss. Never trade with money you can't afford to lose.

---

## Features

| Order Type | Description | Module |
|---|---|---|
| **Market Order** | Execute immediately at market price | `src/market_orders.py` |
| **Limit Order** | Execute at a specific price (GTC) | `src/limit_orders.py` |
| **Stop-Limit** | Conditional order with trigger + limit price | `src/advanced/stop_limit.py` |
| **OCO** | Take-profit + stop-loss pair (custom implementation) | `src/advanced/oco.py` |
| **TWAP** | Split large orders across time intervals | `src/advanced/twap.py` |
| **Grid Trading** | Automated buy/sell grid within a price range | `src/advanced/grid.py` |

| Analysis Tool | Description | Module |
|---|---|---|
| **Historical Analysis** | Trade performance review — PnL, win rate, volume by coin | `src/analysis/historical_analysis.py` |
| **Fear & Greed Index** | Market sentiment analysis with contrarian trading signals | `src/analysis/fear_greed.py` |

**Additional features:**
- 🔐 Secure API key management via `.env` file
- 📝 Dual logging (console + `bot.log` file)
- ✅ Input validation before every API call
- 🧪 Testnet-first development (safe to experiment)
- 🖥️ CLI interface for every order type
- 📊 Historical trade data analysis (211k+ trades)
- 🌡️ Fear & Greed Index with contrarian buy/sell signals

---

## Prerequisites

- **Python 3.8+**
- **Binance account** with Futures enabled
- **Binance Futures Testnet API keys** (for safe testing)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pruthvijain/pruthvijain-binance-bot.git
cd pruthvijain-binance-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
USE_TESTNET=True
```

### 4. Get Binance Futures Testnet API Keys

1. Go to [https://testnet.binancefuture.com/](https://testnet.binancefuture.com/)
2. Log in with your GitHub account
3. Click **"API Key"** in the bottom left
4. Generate a new API key pair
5. Copy the API Key and Secret into your `.env` file

---

## Usage Examples

All commands are run from the project root directory.

### Market Order
```bash
# Buy 0.001 BTC at market price
python -m src.market_orders BTCUSDT BUY 0.001

# Sell 0.01 ETH at market price
python -m src.market_orders ETHUSDT SELL 0.01
```

### Limit Order
```bash
# Buy 0.001 BTC at $50,000
python -m src.limit_orders BTCUSDT BUY 0.001 50000

# Sell 0.01 ETH at $4,000
python -m src.limit_orders ETHUSDT SELL 0.01 4000
```

### Stop-Limit Order
```bash
# Stop-loss: sell BTC if price drops to $58,000 (limit at $57,800)
python -m src.advanced.stop_limit BTCUSDT SELL 0.001 58000 57800

# Buy on breakout above $62,000 (limit at $62,200)
python -m src.advanced.stop_limit BTCUSDT BUY 0.001 62000 62200
```

### OCO Order (One-Cancels-Other)
```bash
# Take-profit at $65,000 OR stop-loss at $58,000
python -m src.advanced.oco BTCUSDT SELL 0.001 65000 58000

# Place without monitoring
python -m src.advanced.oco BTCUSDT SELL 0.001 65000 58000 --no-monitor
```

### TWAP Strategy
```bash
# Buy 0.01 BTC over 10 minutes in 5 chunks
python -m src.advanced.twap BTCUSDT BUY 0.01 600 5

# Sell 0.1 ETH over 30 minutes in 10 chunks
python -m src.advanced.twap ETHUSDT SELL 0.1 1800 10
```

### Grid Trading
```bash
# Grid from $58,000 to $62,000 with 10 levels, 0.001 BTC each
python -m src.advanced.grid BTCUSDT 58000 62000 10 0.001

# Place grid without monitoring
python -m src.advanced.grid BTCUSDT 58000 62000 10 0.001 --no-monitor
```

### Historical Trade Analysis
```bash
# Full portfolio analysis (top 10 coins by volume)
python -m src.analysis.historical_analysis

# Filter by specific coin
python -m src.analysis.historical_analysis --coin AIXBT

# Show top 5 coins only
python -m src.analysis.historical_analysis --top 5
```

### Fear & Greed Index
```bash
# Full sentiment report
python -m src.analysis.fear_greed

# Show contrarian trading signal
python -m src.analysis.fear_greed --signal

# Analyze only the last 30 days
python -m src.analysis.fear_greed --latest 30 --signal
```

---

## File Structure

```
pruthvijain-binance-bot/
├── src/
│   ├── __init__.py              # Package init
│   ├── config.py                # API config, constants, .env loading
│   ├── logger_setup.py          # Dual logging (console + file)
│   ├── validators.py            # Input validation functions
│   ├── client.py                # BinanceClient API wrapper class
│   ├── market_orders.py         # Market order class + CLI
│   ├── limit_orders.py          # Limit order class + CLI
│   ├── advanced/
│   │   ├── __init__.py          # Subpackage init
│   │   ├── stop_limit.py        # Stop-limit order class + CLI
│   │   ├── oco.py               # Custom OCO implementation + CLI
│   │   ├── twap.py              # TWAP execution strategy + CLI
│   │   └── grid.py              # Grid trading strategy + CLI
│   └── analysis/
│       ├── __init__.py          # Subpackage init
│       ├── historical_analysis.py  # Trade data analytics + CLI
│       └── fear_greed.py        # Sentiment analysis + CLI
├── historical_data.csv          # 211k+ trade records for analysis
├── fear_greed_index.csv         # Daily sentiment data (2018-present)
├── .env.example                 # Template for API keys (safe to commit)
├── .gitignore                   # Ignores .env, logs, __pycache__
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## Testing Guide

### 1. Verify Configuration
```bash
python -m src.config
```
This prints your masked API key and current environment (TESTNET/PRODUCTION).

### 2. Test Logger
```bash
python -m src.logger_setup
```
Verifies logging works and creates `bot.log`.

### 3. Test Validators
```bash
python -m src.validators
```
Runs all validation functions with valid and invalid inputs.

### 4. Test API Connection
```bash
python -m src.client
```
Connects to Binance and fetches the current BTC price.

### 5. Place a Test Order
```bash
python -m src.market_orders BTCUSDT BUY 0.001
```

---

## Logging

All operations are logged to:
- **Console** — INFO level and above (real-time monitoring)
- **`bot.log`** — DEBUG level and above (detailed audit trail)

Log format:
```
2024-01-15 10:30:00 - src.market_orders - INFO - Placing BUY order for BTCUSDT
```

---

## Troubleshooting

| Error | Solution |
|---|---|
| `APIError: -2015 Invalid API-key` | Check your API keys in `.env`. Ensure you're using Futures Testnet keys. |
| `APIError: -1121 Invalid symbol` | Symbol must be uppercase and end with USDT (e.g., `BTCUSDT`). |
| `APIError: -4003 Quantity less than minimum` | Increase your order quantity. Check minimums with `get_symbol_info()`. |
| `ConnectionError` | Check your internet connection. Binance Testnet may be temporarily down. |
| `ModuleNotFoundError` | Run from the project root directory and install deps: `pip install -r requirements.txt` |

---

## ⚠️ Testnet vs Production

| | Testnet | Production |
|---|---|---|
| **URL** | testnet.binancefuture.com | fapi.binance.com |
| **Real Money** | No (fake funds) | Yes |
| **Config** | `USE_TESTNET=True` | `USE_TESTNET=False` |
| **Risk** | None | Real financial risk |

**Always develop and test on Testnet first!**

---

## License

This project is for educational purposes. Use at your own risk.

## Author

**Pruthvi Jain**
