"""Tests for the Backtest MCP Server."""

import pytest
import sys
sys.path.insert(0, "src")

from backtest_mcp.server import _run_backtest, _get_performance_metrics, _optimize_parameters


@pytest.mark.asyncio
async def test_run_backtest_returns_results():
    """Test that run_backtest returns valid results."""
    result = await _run_backtest(
        symbol="AAPL",
        start_date="2024-06-01",
        end_date="2024-08-01",  # Short period for speed
        rsi_window=14,
        rsi_entry=30,
        rsi_exit=70,
        trailing_stop=0.03,
        initial_cash=10000,
    )

    assert "error" not in result
    assert result["symbol"] == "AAPL"
    assert "results" in result
    assert "total_return_pct" in result["results"]
    assert "total_trades" in result["results"]
    assert "final_value" in result["results"]


@pytest.mark.asyncio
async def test_run_backtest_uk_stock():
    """Test that UK stocks work."""
    result = await _run_backtest(
        symbol="LLOY.L",
        start_date="2024-06-01",
        end_date="2024-08-01",
    )

    assert "error" not in result
    assert result["symbol"] == "LLOY.L"


@pytest.mark.asyncio
async def test_run_backtest_invalid_symbol():
    """Test that invalid symbols return an error."""
    result = await _run_backtest(
        symbol="INVALID_SYMBOL_12345",
        start_date="2024-06-01",
        end_date="2024-08-01",
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_get_performance_metrics():
    """Test that performance metrics returns detailed stats."""
    result = await _get_performance_metrics(
        symbol="AAPL",
        start_date="2024-06-01",
        end_date="2024-08-01",
    )

    assert "error" not in result
    assert "returns" in result
    assert "risk_metrics" in result
    assert "trade_stats" in result
    assert "capital" in result


@pytest.mark.asyncio
async def test_optimize_parameters():
    """Test that parameter optimization works."""
    result = await _optimize_parameters(
        symbol="AAPL",
        start_date="2024-06-01",
        end_date="2024-08-01",
        rsi_windows=[10, 14],  # Fewer combinations for speed
        trailing_stops=[0.03, 0.05],
    )

    assert "error" not in result
    assert "best_parameters" in result
    assert "all_results" in result
    assert result["optimization"]["total_combinations"] == 4


@pytest.mark.asyncio
async def test_backtest_with_custom_params():
    """Test backtest with custom RSI parameters."""
    result = await _run_backtest(
        symbol="AAPL",
        start_date="2024-06-01",
        end_date="2024-08-01",
        rsi_window=10,
        rsi_entry=25,
        rsi_exit=75,
        trailing_stop=0.02,
        initial_cash=50000,
    )

    assert "error" not in result
    assert result["strategy"]["rsi_window"] == 10
    assert result["strategy"]["rsi_entry"] == 25
    assert result["strategy"]["trailing_stop_pct"] == 2.0
