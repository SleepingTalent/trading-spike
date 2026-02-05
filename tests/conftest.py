"""
Pytest fixtures for backtest testing with mocked market data.

These fixtures provide deterministic price data that produces predictable
RSI values and trading signals, enabling reliable unit tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


def generate_price_series(
    start_price: float = 100.0,
    days: int = 252,
    trend: str = "neutral",
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.Series:
    """
    Generate synthetic price data with controlled characteristics.

    Args:
        start_price: Starting price
        days: Number of trading days
        trend: "up", "down", or "neutral"
        volatility: Daily volatility (standard deviation of returns)
        seed: Random seed for reproducibility

    Returns:
        pd.Series with datetime index and price values
    """
    np.random.seed(seed)

    # Base drift based on trend
    drift = {"up": 0.001, "down": -0.001, "neutral": 0.0}[trend]

    # Generate daily returns
    returns = np.random.normal(drift, volatility, days)

    # Convert to prices
    prices = start_price * np.cumprod(1 + returns)

    # Create datetime index (daily frequency, no business day offset)
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start=start_date, periods=days, freq="D")

    return pd.Series(prices, index=dates, name="Close")


def generate_mean_reverting_prices(
    start_price: float = 100.0,
    days: int = 252,
    mean_price: float = 100.0,
    reversion_speed: float = 0.1,
    volatility: float = 0.02,
    seed: int = 42,
) -> pd.Series:
    """
    Generate price data with mean-reverting characteristics.

    This creates price patterns where the RSI strategy should perform well,
    with clear oversold and overbought conditions that revert.
    """
    np.random.seed(seed)

    prices = [start_price]
    for _ in range(days - 1):
        current = prices[-1]
        # Mean reversion component
        reversion = reversion_speed * (mean_price - current)
        # Random shock
        shock = np.random.normal(0, volatility * current)
        # New price
        new_price = current + reversion + shock
        prices.append(max(new_price, 1.0))  # Price floor

    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start=start_date, periods=days, freq="D")

    return pd.Series(prices, index=dates, name="Close")


def generate_trending_with_pullbacks(
    start_price: float = 100.0,
    days: int = 252,
    trend_strength: float = 0.002,
    pullback_frequency: int = 20,
    pullback_depth: float = 0.05,
    seed: int = 42,
) -> pd.Series:
    """
    Generate trending price data with periodic pullbacks.

    This creates scenarios where trailing stops would be triggered
    during pullbacks, testing the risk management logic.
    """
    np.random.seed(seed)

    prices = [start_price]
    for i in range(days - 1):
        current = prices[-1]

        # Check if we're in a pullback period
        if i % pullback_frequency < 5 and i > pullback_frequency:
            # Pullback: price drops
            change = -pullback_depth / 5
        else:
            # Trending: price rises with some noise
            change = trend_strength + np.random.normal(0, 0.01)

        new_price = current * (1 + change)
        prices.append(max(new_price, 1.0))

    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start=start_date, periods=days, freq="D")

    return pd.Series(prices, index=dates, name="Close")


class MockYFData:
    """Mock for vbt.YFData.download that returns fixture data."""

    def __init__(self, price_data: pd.Series):
        self._data = {"Close": price_data}

    def get(self, key: str):
        return self._data.get(key)


@pytest.fixture
def mock_neutral_prices():
    """Fixture providing neutral/sideways price data."""
    return generate_price_series(trend="neutral", seed=42)


@pytest.fixture
def mock_uptrend_prices():
    """Fixture providing uptrending price data."""
    return generate_price_series(trend="up", seed=42)


@pytest.fixture
def mock_downtrend_prices():
    """Fixture providing downtrending price data."""
    return generate_price_series(trend="down", seed=42)


@pytest.fixture
def mock_mean_reverting_prices():
    """Fixture providing mean-reverting price data (ideal for RSI strategy)."""
    return generate_mean_reverting_prices(seed=42)


@pytest.fixture
def mock_trending_with_pullbacks():
    """Fixture providing trending data with pullbacks (tests trailing stops)."""
    return generate_trending_with_pullbacks(seed=42)


@pytest.fixture
def patch_yf_download():
    """
    Context manager fixture to patch Yahoo Finance downloads.

    Usage:
        def test_example(patch_yf_download, mock_neutral_prices):
            with patch_yf_download(mock_neutral_prices):
                result = await _run_backtest(...)
    """
    def _patch(price_data: pd.Series):
        mock_download = MagicMock(return_value=MockYFData(price_data))
        return patch("vectorbt.data.custom.YFData.download", mock_download)

    return _patch


# Pre-configured market scenarios for multi-symbol tests
MOCK_MARKET_DATA = {
    "AAPL": generate_mean_reverting_prices(start_price=150, seed=1),
    "MSFT": generate_mean_reverting_prices(start_price=350, seed=2),
    "GOOGL": generate_price_series(trend="up", seed=3),
    "BARC.L": generate_mean_reverting_prices(start_price=2.0, seed=4),
    "LLOY.L": generate_mean_reverting_prices(start_price=0.5, seed=5),
    "BTC-USD": generate_trending_with_pullbacks(start_price=45000, seed=6),
}


@pytest.fixture
def patch_yf_multi_symbol():
    """
    Patch Yahoo Finance to return different data per symbol.

    This enables testing the full validation flow with multiple symbols
    without hitting the network.
    """
    def mock_download(symbol, **kwargs):
        if symbol in MOCK_MARKET_DATA:
            return MockYFData(MOCK_MARKET_DATA[symbol])
        # Return empty data for unknown symbols
        return MockYFData(pd.Series([], name="Close"))

    return patch("vectorbt.data.custom.YFData.download", side_effect=mock_download)
