# Tasks

## Phase 1: Data + Backtest

### 1.1 Set up Ollama with LLM
- [x] Install Ollama on Mac
- [x] Pull DeepSeek-R1 32B model
- [x] Verify model runs locally
- [x] Test basic prompts for trading analysis

### 1.2 Configure Alpha Vantage MCP Server
- [x] Get Alpha Vantage API key (stored in .env)
- [ ] Configure MCP server connection
- [ ] Test data retrieval (quotes, time series)
- [ ] Test technical indicators (RSI, MACD, etc.)
- [ ] Test news sentiment endpoint

### 1.3 Build Backtest MCP Server
- [ ] Set up Python project structure
- [ ] Install VectorBT
- [ ] Create MCP server scaffold
- [ ] Implement `run_backtest` tool
- [ ] Implement `get_performance_metrics` tool
- [ ] Implement `optimize_parameters` tool
- [ ] Test with sample strategy

### 1.4 Create Initial Trading Strategy
- [ ] Define entry signal logic (RSI oversold, etc.)
- [ ] Define exit signal logic (RSI overbought, trailing stop)
- [ ] Configure trailing stop parameters
- [ ] Document strategy rules

### 1.5 Validate with Historical Data
- [ ] Backtest on UK stocks (LSE)
- [ ] Backtest on US stocks
- [ ] Backtest on crypto
- [ ] Analyze performance metrics (Sharpe, drawdown, win rate)
- [ ] Iterate on strategy parameters

---

## Phase 2: Paper Trading
> *To be planned after Phase 1 completion*

---

## Phase 3: Single Market Live
> *To be planned after Phase 2 completion*

---

## Phase 4: Multi-Market
> *To be planned after Phase 3 completion*
