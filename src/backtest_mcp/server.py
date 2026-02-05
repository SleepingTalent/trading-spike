"""
Backtest MCP Server

An MCP server that wraps VectorBT for strategy backtesting.
Provides tools for running backtests, analyzing performance, and optimizing parameters.
"""

import json
from datetime import datetime
from typing import Any

import numpy as np
import vectorbt as vbt
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

mcp = Server("backtest-mcp")


def _serialize_results(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable formats."""
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _serialize_results(v) for k, v in obj.items()}
    if hasattr(obj, "to_dict"):
        return _serialize_results(obj.to_dict())
    return obj


@mcp.list_tools()
async def list_tools() -> list[Tool]:
    """List available backtesting tools."""
    return [
        Tool(
            name="run_backtest",
            description="""Run a backtest on historical data using RSI strategy with trailing stops.

Parameters:
- symbol: Stock/crypto ticker (e.g., "AAPL", "BTC-USD")
- start_date: Start date (YYYY-MM-DD)
- end_date: End date (YYYY-MM-DD)
- rsi_window: RSI period (default: 14)
- rsi_entry: RSI threshold to enter (default: 30, oversold)
- rsi_exit: RSI threshold to exit (default: 70, overbought)
- trailing_stop: Trailing stop percentage (default: 0.03 = 3%)
- initial_cash: Starting capital (default: 10000)

Returns backtest results including total return, trades, and key metrics.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Ticker symbol"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "rsi_window": {"type": "integer", "default": 14},
                    "rsi_entry": {"type": "number", "default": 30},
                    "rsi_exit": {"type": "number", "default": 70},
                    "trailing_stop": {"type": "number", "default": 0.03},
                    "initial_cash": {"type": "number", "default": 10000},
                },
                "required": ["symbol", "start_date", "end_date"],
            },
        ),
        Tool(
            name="get_performance_metrics",
            description="""Get detailed performance metrics for a completed backtest.

Returns comprehensive statistics including:
- Total and annual returns
- Sharpe ratio and Sortino ratio
- Max drawdown and duration
- Win rate and profit factor
- Number of trades and average trade duration""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "rsi_window": {"type": "integer", "default": 14},
                    "rsi_entry": {"type": "number", "default": 30},
                    "rsi_exit": {"type": "number", "default": 70},
                    "trailing_stop": {"type": "number", "default": 0.03},
                    "initial_cash": {"type": "number", "default": 10000},
                },
                "required": ["symbol", "start_date", "end_date"],
            },
        ),
        Tool(
            name="optimize_parameters",
            description="""Optimize strategy parameters by testing multiple combinations.

Tests combinations of RSI windows and trailing stop percentages to find
the best performing parameters based on total return.

Parameters:
- symbol: Ticker to optimize on
- start_date/end_date: Date range for optimization
- rsi_windows: List of RSI periods to test (default: [10, 14, 20])
- trailing_stops: List of trailing stop %s to test (default: [0.02, 0.03, 0.05])

Returns the best parameters and performance comparison.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "rsi_windows": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "default": [10, 14, 20],
                    },
                    "trailing_stops": {
                        "type": "array",
                        "items": {"type": "number"},
                        "default": [0.02, 0.03, 0.05],
                    },
                    "initial_cash": {"type": "number", "default": 10000},
                },
                "required": ["symbol", "start_date", "end_date"],
            },
        ),
    ]


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a backtesting tool."""

    if name == "run_backtest":
        result = await _run_backtest(**arguments)
    elif name == "get_performance_metrics":
        result = await _get_performance_metrics(**arguments)
    elif name == "optimize_parameters":
        result = await _optimize_parameters(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    rsi_window: int = 14,
    rsi_entry: float = 30,
    rsi_exit: float = 70,
    trailing_stop: float = 0.03,
    initial_cash: float = 10000,
) -> dict:
    """Run a backtest with the given parameters."""
    try:
        # Download price data
        price = vbt.YFData.download(
            symbol,
            start=start_date,
            end=end_date,
        ).get("Close")

        if price is None or len(price) == 0:
            return {"error": f"No data found for {symbol}"}

        # Calculate RSI
        rsi = vbt.RSI.run(price, window=rsi_window)

        # Generate signals
        entries = rsi.rsi_crossed_below(rsi_entry)
        exits = rsi.rsi_crossed_above(rsi_exit)

        # Run backtest with trailing stop
        portfolio = vbt.Portfolio.from_signals(
            price,
            entries=entries,
            exits=exits,
            sl_trail=trailing_stop,
            init_cash=initial_cash,
            fees=0.001,  # 0.1% commission
        )

        # Extract key results
        stats = portfolio.stats()

        return _serialize_results({
            "symbol": symbol,
            "period": f"{start_date} to {end_date}",
            "strategy": {
                "rsi_window": rsi_window,
                "rsi_entry": rsi_entry,
                "rsi_exit": rsi_exit,
                "trailing_stop_pct": trailing_stop * 100,
            },
            "results": {
                "total_return_pct": float(stats.get("Total Return [%]", 0)),
                "total_trades": int(stats.get("Total Trades", 0)),
                "win_rate_pct": float(stats.get("Win Rate [%]", 0)),
                "max_drawdown_pct": float(stats.get("Max Drawdown [%]", 0)),
                "sharpe_ratio": float(stats.get("Sharpe Ratio", 0)),
                "final_value": float(stats.get("End Value", initial_cash)),
            },
        })

    except Exception as e:
        return {"error": str(e)}


async def _get_performance_metrics(
    symbol: str,
    start_date: str,
    end_date: str,
    rsi_window: int = 14,
    rsi_entry: float = 30,
    rsi_exit: float = 70,
    trailing_stop: float = 0.03,
    initial_cash: float = 10000,
) -> dict:
    """Get detailed performance metrics."""
    try:
        # Download and run backtest
        price = vbt.YFData.download(symbol, start=start_date, end=end_date).get("Close")

        if price is None or len(price) == 0:
            return {"error": f"No data found for {symbol}"}

        rsi = vbt.RSI.run(price, window=rsi_window)
        entries = rsi.rsi_crossed_below(rsi_entry)
        exits = rsi.rsi_crossed_above(rsi_exit)

        portfolio = vbt.Portfolio.from_signals(
            price,
            entries=entries,
            exits=exits,
            sl_trail=trailing_stop,
            init_cash=initial_cash,
            fees=0.001,
        )

        stats = portfolio.stats()

        return _serialize_results({
            "symbol": symbol,
            "period": f"{start_date} to {end_date}",
            "returns": {
                "total_return_pct": stats.get("Total Return [%]", 0),
                "benchmark_return_pct": stats.get("Benchmark Return [%]", 0),
                "annual_return_pct": stats.get("Annualized Return [%]", 0),
                "annual_volatility_pct": stats.get("Annualized Volatility [%]", 0),
            },
            "risk_metrics": {
                "sharpe_ratio": stats.get("Sharpe Ratio", 0),
                "sortino_ratio": stats.get("Sortino Ratio", 0),
                "calmar_ratio": stats.get("Calmar Ratio", 0),
                "max_drawdown_pct": stats.get("Max Drawdown [%]", 0),
                "max_drawdown_duration": str(stats.get("Max Drawdown Duration", "N/A")),
            },
            "trade_stats": {
                "total_trades": stats.get("Total Trades", 0),
                "win_rate_pct": stats.get("Win Rate [%]", 0),
                "profit_factor": stats.get("Profit Factor", 0),
                "expectancy": stats.get("Expectancy", 0),
                "avg_winning_trade_pct": stats.get("Avg Winning Trade [%]", 0),
                "avg_losing_trade_pct": stats.get("Avg Losing Trade [%]", 0),
            },
            "capital": {
                "initial_cash": initial_cash,
                "final_value": stats.get("End Value", initial_cash),
                "total_fees_paid": stats.get("Total Fees Paid", 0),
            },
        })

    except Exception as e:
        return {"error": str(e)}


async def _optimize_parameters(
    symbol: str,
    start_date: str,
    end_date: str,
    rsi_windows: list[int] = None,
    trailing_stops: list[float] = None,
    initial_cash: float = 10000,
) -> dict:
    """Optimize strategy parameters."""
    if rsi_windows is None:
        rsi_windows = [10, 14, 20]
    if trailing_stops is None:
        trailing_stops = [0.02, 0.03, 0.05]

    try:
        # Download price data
        price = vbt.YFData.download(symbol, start=start_date, end=end_date).get("Close")

        if price is None or len(price) == 0:
            return {"error": f"No data found for {symbol}"}

        results = []
        best_return = float("-inf")
        best_params = None

        # Test all combinations
        for rsi_window in rsi_windows:
            rsi = vbt.RSI.run(price, window=rsi_window)
            entries = rsi.rsi_crossed_below(30)
            exits = rsi.rsi_crossed_above(70)

            for trail_stop in trailing_stops:
                portfolio = vbt.Portfolio.from_signals(
                    price,
                    entries=entries,
                    exits=exits,
                    sl_trail=trail_stop,
                    init_cash=initial_cash,
                    fees=0.001,
                )

                stats = portfolio.stats()
                total_return = float(stats.get("Total Return [%]", 0))

                result = {
                    "rsi_window": rsi_window,
                    "trailing_stop_pct": trail_stop * 100,
                    "total_return_pct": total_return,
                    "sharpe_ratio": float(stats.get("Sharpe Ratio", 0)),
                    "max_drawdown_pct": float(stats.get("Max Drawdown [%]", 0)),
                    "total_trades": int(stats.get("Total Trades", 0)),
                }
                results.append(result)

                if total_return > best_return:
                    best_return = total_return
                    best_params = result

        # Sort by return
        results.sort(key=lambda x: x["total_return_pct"], reverse=True)

        return {
            "symbol": symbol,
            "period": f"{start_date} to {end_date}",
            "optimization": {
                "rsi_windows_tested": rsi_windows,
                "trailing_stops_tested": [s * 100 for s in trailing_stops],
                "total_combinations": len(results),
            },
            "best_parameters": best_params,
            "all_results": results[:10],  # Top 10 results
        }

    except Exception as e:
        return {"error": str(e)}


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
