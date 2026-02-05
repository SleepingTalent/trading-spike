#!/usr/bin/env python3
"""
Strategy Validation Script

Runs backtests across multiple markets (UK stocks, US stocks, crypto)
to validate the RSI mean-reversion strategy with trailing stops.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, "src")

from backtest_mcp.server import _run_backtest, _get_performance_metrics, _optimize_parameters
from backtest_mcp.strategy import DEFAULT_STRATEGY, CONSERVATIVE_STRATEGY, AGGRESSIVE_STRATEGY


@dataclass
class BacktestResult:
    """Container for backtest results."""
    symbol: str
    market: str
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    error: str | None = None


# Test symbols for each market
UK_STOCKS = [
    ("BARC.L", "Barclays"),
    ("LLOY.L", "Lloyds"),
    ("VOD.L", "Vodafone"),
    ("BP.L", "BP"),
    ("HSBA.L", "HSBC"),
]

US_STOCKS = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("GOOGL", "Alphabet"),
    ("AMZN", "Amazon"),
    ("NVDA", "NVIDIA"),
]

CRYPTO = [
    ("BTC-USD", "Bitcoin"),
    ("ETH-USD", "Ethereum"),
    ("SOL-USD", "Solana"),
]

# Date range for backtests (1 year)
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"


async def run_single_backtest(symbol: str, name: str, market: str) -> BacktestResult:
    """Run a backtest for a single symbol."""
    print(f"  Testing {name} ({symbol})...", end=" ", flush=True)

    result = await _run_backtest(
        symbol=symbol,
        start_date=START_DATE,
        end_date=END_DATE,
        rsi_window=DEFAULT_STRATEGY.rsi_window,
        rsi_entry=DEFAULT_STRATEGY.rsi_entry_threshold,
        rsi_exit=DEFAULT_STRATEGY.rsi_exit_threshold,
        trailing_stop=DEFAULT_STRATEGY.trailing_stop_pct,
    )

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return BacktestResult(
            symbol=symbol,
            market=market,
            total_return_pct=0,
            sharpe_ratio=0,
            max_drawdown_pct=0,
            win_rate_pct=0,
            total_trades=0,
            error=result["error"],
        )

    results = result.get("results", {})
    print(f"Return: {results.get('total_return_pct', 0):.1f}%")

    return BacktestResult(
        symbol=symbol,
        market=market,
        total_return_pct=results.get("total_return_pct", 0),
        sharpe_ratio=results.get("sharpe_ratio", 0),
        max_drawdown_pct=results.get("max_drawdown_pct", 0),
        win_rate_pct=results.get("win_rate_pct", 0),
        total_trades=results.get("total_trades", 0),
    )


async def validate_market(symbols: list[tuple[str, str]], market_name: str) -> list[BacktestResult]:
    """Validate strategy on a specific market."""
    print(f"\n{'='*60}")
    print(f"Testing {market_name}")
    print(f"{'='*60}")

    results = []
    for symbol, name in symbols:
        result = await run_single_backtest(symbol, name, market_name)
        results.append(result)

    return results


def print_summary(results: list[BacktestResult], market_name: str):
    """Print summary statistics for a market."""
    valid_results = [r for r in results if r.error is None]

    if not valid_results:
        print(f"\n{market_name}: No valid results")
        return

    avg_return = sum(r.total_return_pct for r in valid_results) / len(valid_results)
    avg_sharpe = sum(r.sharpe_ratio for r in valid_results) / len(valid_results)
    avg_drawdown = sum(r.max_drawdown_pct for r in valid_results) / len(valid_results)
    avg_winrate = sum(r.win_rate_pct for r in valid_results) / len(valid_results)
    total_trades = sum(r.total_trades for r in valid_results)

    profitable = len([r for r in valid_results if r.total_return_pct > 0])

    print(f"\n{market_name} Summary ({len(valid_results)} symbols):")
    print(f"  Avg Return:     {avg_return:+.1f}%")
    print(f"  Avg Sharpe:     {avg_sharpe:.2f}")
    print(f"  Avg Drawdown:   {avg_drawdown:.1f}%")
    print(f"  Avg Win Rate:   {avg_winrate:.1f}%")
    print(f"  Total Trades:   {total_trades}")
    print(f"  Profitable:     {profitable}/{len(valid_results)} ({100*profitable/len(valid_results):.0f}%)")


def print_results_table(all_results: list[BacktestResult]):
    """Print a formatted table of all results."""
    print(f"\n{'='*88}")
    print("DETAILED RESULTS")
    print(f"{'='*88}")
    print(f"{'Symbol':<12} {'Market':<18} {'Return':>10} {'Sharpe':>8} {'Drawdown':>10} {'Win Rate':>10} {'Trades':>8}")
    print("-" * 88)

    for r in sorted(all_results, key=lambda x: x.total_return_pct, reverse=True):
        if r.error:
            print(f"{r.symbol:<12} {r.market:<18} {'ERROR':>10}")
        else:
            print(f"{r.symbol:<12} {r.market:<18} {r.total_return_pct:>+9.1f}% {r.sharpe_ratio:>8.2f} {r.max_drawdown_pct:>9.1f}% {r.win_rate_pct:>9.1f}% {r.total_trades:>8}")


async def run_optimization(symbol: str, name: str):
    """Run parameter optimization on a symbol."""
    print(f"\nOptimizing parameters for {name} ({symbol})...")

    result = await _optimize_parameters(
        symbol=symbol,
        start_date=START_DATE,
        end_date=END_DATE,
        rsi_windows=[10, 14, 20, 25],
        trailing_stops=[0.02, 0.03, 0.04, 0.05],
    )

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    best = result.get("best_parameters", {})
    print(f"  Best RSI Window:    {best.get('rsi_window')}")
    print(f"  Best Trailing Stop: {best.get('trailing_stop_pct')}%")
    print(f"  Best Return:        {best.get('total_return_pct', 0):+.1f}%")
    print(f"  Sharpe Ratio:       {best.get('sharpe_ratio', 0):.2f}")


async def main():
    """Run full strategy validation."""
    print("=" * 60)
    print("RSI Mean-Reversion Strategy Validation")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Strategy: RSI({DEFAULT_STRATEGY.rsi_window}) Entry<{DEFAULT_STRATEGY.rsi_entry_threshold} Exit>{DEFAULT_STRATEGY.rsi_exit_threshold}")
    print(f"Trailing Stop: {DEFAULT_STRATEGY.trailing_stop_pct * 100}%")
    print("=" * 60)

    all_results = []

    # Test each market
    uk_results = await validate_market(UK_STOCKS, "UK Stocks (LSE)")
    all_results.extend(uk_results)

    us_results = await validate_market(US_STOCKS, "US Stocks")
    all_results.extend(us_results)

    crypto_results = await validate_market(CRYPTO, "Crypto")
    all_results.extend(crypto_results)

    # Print summaries
    print("\n" + "=" * 60)
    print("MARKET SUMMARIES")
    print("=" * 60)
    print_summary(uk_results, "UK Stocks")
    print_summary(us_results, "US Stocks")
    print_summary(crypto_results, "Crypto")

    # Print detailed results table
    print_results_table(all_results)

    # Run optimization on best performing symbol from each market
    print("\n" + "=" * 60)
    print("PARAMETER OPTIMIZATION")
    print("=" * 60)

    # Find best symbol from each market for optimization
    for market, results in [("UK", uk_results), ("US", us_results), ("Crypto", crypto_results)]:
        valid = [r for r in results if r.error is None]
        if valid:
            best = max(valid, key=lambda x: x.total_return_pct)
            await run_optimization(best.symbol, f"{market} Best ({best.symbol})")

    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
