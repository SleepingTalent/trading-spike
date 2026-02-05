# Tasks

## Phase 1: Data + Backtest

### 1.1 Set up Ollama with LLM
- [x] Install Ollama on Mac
- [x] Pull DeepSeek-R1 32B model
- [x] Verify model runs locally
- [x] Test basic prompts for trading analysis

### 1.2 Configure Alpha Vantage MCP Server
- [x] Get Alpha Vantage API key (stored in .env)
- [x] Configure MCP server connection
- [x] Test data retrieval (quotes, time series)
- [x] Test technical indicators (RSI, MACD, etc.)
- [x] Test news sentiment endpoint

> **Note:** Free tier limited to 25 requests/day. Consider premium for production use.

### 1.3 Build Backtest MCP Server
- [x] Set up Python project structure (src/backtest_mcp/)
- [x] Install VectorBT + yfinance
- [x] Create MCP server scaffold
- [x] Implement `run_backtest` tool
- [x] Implement `get_performance_metrics` tool
- [x] Implement `optimize_parameters` tool
- [x] Test with sample strategy (AAPL 2024: +18% optimized)

### 1.4 Create Initial Trading Strategy
- [x] Define entry signal logic (RSI crosses below 30 = oversold)
- [x] Define exit signal logic (RSI crosses above 70 OR trailing stop)
- [x] Configure trailing stop parameters (default 3%, conservative 2%, aggressive 5%)
- [x] Document strategy rules (src/backtest_mcp/strategy.py)

### 1.5 Validate with Historical Data
- [x] Backtest on UK stocks (LSE) - Avg +10.8%, 4/5 profitable
- [x] Backtest on US stocks - Avg +19.1%, 5/5 profitable
- [x] Backtest on crypto - Avg +27.2%, 3/3 profitable
- [x] Analyze performance metrics (Sharpe, drawdown, win rate)
- [x] Iterate on strategy parameters (RSI 14-20, trailing stop 2-3%)

#### Validation Results (2024-01-01 to 2024-12-31)

| Market | Avg Return | Win Rate | Max Drawdown | Profitable |
|--------|------------|----------|--------------|------------|
| UK Stocks | +10.8% | 90% | 10.5% | 4/5 (80%) |
| US Stocks | +19.1% | 67% | 12.3% | 5/5 (100%) |
| Crypto | +27.2% | 85% | 25.3% | 3/3 (100%) |

**Top Performers:** NVDA (+72%), SOL-USD (+37%), BARC.L (+33%), ETH-USD (+25%), BTC-USD (+20%)

**Optimized Parameters:** RSI 14-20, Trailing Stop 2%, yields best risk-adjusted returns.

---

## Phase 2: Paper Trading
> *To be planned after Phase 1 completion*

---

## Phase 3: Single Market Live
> *To be planned after Phase 2 completion*

---

## Phase 4: Multi-Market
> *To be planned after Phase 3 completion*
