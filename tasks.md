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

### Architecture

```
Strategic Layer: Ollama (DeepSeek-R1 32B)
  │  tool calls via ollama.chat(tools=[...])
  ▼
Orchestrator (src/orchestrator/)
  │  MCP client sessions
  │
  ├──▶ Alpha Vantage MCP  [remote HTTP]  — market data, indicators, sentiment
  ├──▶ Backtest MCP       [stdio]         — strategy validation (existing)
  └──▶ Risk Manager MCP   [stdio]         — risk checks, then delegates to Alpaca
          │
          └──▶ Alpaca MCP Server [stdio]  — order execution, positions, account
```

**Key design decisions:**
- Risk Manager is the **only** pathway to execution — LLM never calls Alpaca directly
- Alpaca MCP server (official) provides 40+ tools for paper trading
- UK stocks use a simulated local ledger (Alpaca doesn't support LSE)
- Alpha Vantage free tier (25 req/day) managed via caching + using Alpaca for real-time prices
- LLM sees a curated subset of ~15 tools (not all 40+ from Alpaca)

### Market Support

| Market | Execution | Data Source |
|--------|-----------|-------------|
| US Stocks | Alpaca paper trading | Alpaca MCP + Alpha Vantage |
| Crypto | Alpaca paper trading | Alpaca MCP + Alpha Vantage |
| UK Stocks (LSE) | Simulated ledger | Alpha Vantage + yfinance |

### 2.1 Alpaca Integration + Execution Layer
- [x] Add `alpaca-py` and `alpaca-mcp-server` dependencies
- [x] Create `src/execution/alpaca_client.py` — MCP client wrapper for Alpaca server
- [x] Create `src/execution/models.py` — Order, Position, AccountInfo dataclasses
- [x] Create `src/execution/market_hours.py` — market hours awareness (US, UK, crypto)
- [x] Create `src/execution/simulated_ledger.py` — JSON-based position ledger for UK stocks
- [x] Add `scripts/test_alpaca_connection.py` — end-to-end paper trading test
- [x] Add unit tests with mocked MCP session
- [x] Update `.env.example` with Alpaca keys

### 2.2 Risk Manager MCP Server
- [ ] Create `src/risk_manager_mcp/server.py` — MCP server (follows backtest_mcp pattern)
- [ ] Create `src/risk_manager_mcp/rules.py` — RiskConfig with safety limits:
  - Max 10% of portfolio per position
  - Max 5 concurrent positions
  - Max 3% daily loss (circuit breaker)
  - Max 2% loss per trade
  - 3% trailing stop on all positions
  - Max 10 trades/day, min 60s between orders
- [ ] Create `src/risk_manager_mcp/state.py` — portfolio state tracking, daily P&L
- [ ] Implement tools: `check_and_submit_order`, `get_risk_status`, `get_positions`, `close_position`, `emergency_close_all`, `update_risk_config`
- [ ] Circuit breaker: auto-close all positions when daily loss exceeds threshold
- [ ] Risk Manager internally holds AlpacaExecutionClient (from 2.1)
- [ ] Add comprehensive unit tests for all risk rules

### 2.3 Shared Infrastructure + Caching
- [ ] Create `src/shared/cache.py` — file-based response cache with TTL
- [ ] Create `src/shared/rate_limiter.py` — Alpha Vantage daily request tracker (persisted)
- [ ] Create `src/shared/config.py` — TradingConfig loaded from env vars
- [ ] Create `src/shared/logging.py` — structured trading logger (JSON + human-readable)
- [ ] Create `src/shared/mcp_client.py` — MCPServerManager for multi-server connections
- [ ] Update `.gitignore` for `.cache/` directory
- [ ] Add unit tests for all shared modules

### 2.4 LLM Orchestration Loop
- [ ] Create `src/orchestrator/agent.py` — TradingAgent with analyze→decide→execute cycle
- [ ] Create `src/orchestrator/ollama_client.py` — Ollama wrapper with tool calling loop
- [ ] Create `src/orchestrator/tool_bridge.py` — MCP tools → Ollama format, routing by prefix
- [ ] Create `src/orchestrator/prompts.py` — system prompt, analysis/decision/review templates
- [ ] Create `src/orchestrator/scheduler.py` — market-hours-aware scheduling loop
- [ ] Create `src/orchestrator/models.py` — MarketAnalysis, TradeDecision, TradingCycleResult
- [ ] Create `src/orchestrator/main.py` — entry point connecting all MCP servers
- [ ] Add `config/watchlist.yaml` — symbols to monitor per market
- [ ] Add `scripts/run_single_cycle.py` — one-shot trading cycle for testing
- [ ] Add `ollama` and `pyyaml` dependencies
- [ ] Add unit tests with mocked Ollama + mocked MCP servers

### 2.5 Monitoring + Documentation + Polish
- [ ] Create `src/monitoring/tracker.py` — SQLite-based performance tracker
- [ ] Create `src/monitoring/alerts.py` — logging-based alerts for critical events
- [ ] Create `scripts/dashboard.py` — formatted summary of trading activity
- [ ] Wire PerformanceTracker into TradingAgent cycle
- [ ] Update CI/CD to test all new packages
- [ ] Add `ruff` linter configuration
- [ ] Update README.md with Phase 2 setup instructions
- [ ] Update CLAUDE.md with conventions for new packages

---

## Phase 3: Single Market Live
> *To be planned after Phase 2 completion*

---

## Phase 4: Multi-Market
> *To be planned after Phase 3 completion*
