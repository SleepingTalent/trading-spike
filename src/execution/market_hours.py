"""
Market Hours Awareness

Provides market hours information for US stocks, UK stocks (LSE),
and crypto markets. Used by the orchestrator to determine when
trading cycles should run.
"""

from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import Enum
from zoneinfo import ZoneInfo


class Market(Enum):
    US_STOCKS = "us_stocks"
    UK_STOCKS = "uk_stocks"
    CRYPTO = "crypto"


# Timezone constants
US_EASTERN = ZoneInfo("America/New_York")
UK_LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc


@dataclass(frozen=True)
class MarketSchedule:
    """Trading schedule for a market."""

    market: Market
    open_time: time
    close_time: time
    timezone: ZoneInfo
    trading_days: tuple[int, ...]  # 0=Monday, 6=Sunday
    is_24_7: bool = False


# Market schedules
US_STOCK_SCHEDULE = MarketSchedule(
    market=Market.US_STOCKS,
    open_time=time(9, 30),
    close_time=time(16, 0),
    timezone=US_EASTERN,
    trading_days=(0, 1, 2, 3, 4),  # Mon-Fri
)

UK_STOCK_SCHEDULE = MarketSchedule(
    market=Market.UK_STOCKS,
    open_time=time(8, 0),
    close_time=time(16, 30),
    timezone=UK_LONDON,
    trading_days=(0, 1, 2, 3, 4),  # Mon-Fri
)

CRYPTO_SCHEDULE = MarketSchedule(
    market=Market.CRYPTO,
    open_time=time(0, 0),
    close_time=time(23, 59, 59),
    timezone=ZoneInfo("UTC"),
    trading_days=(0, 1, 2, 3, 4, 5, 6),  # Every day
    is_24_7=True,
)

SCHEDULES: dict[Market, MarketSchedule] = {
    Market.US_STOCKS: US_STOCK_SCHEDULE,
    Market.UK_STOCKS: UK_STOCK_SCHEDULE,
    Market.CRYPTO: CRYPTO_SCHEDULE,
}


def get_schedule(market: Market) -> MarketSchedule:
    """Get the trading schedule for a market."""
    return SCHEDULES[market]


def is_market_open(market: Market, now: datetime | None = None) -> bool:
    """
    Check if a market is currently open.

    Args:
        market: The market to check.
        now: Current time (defaults to UTC now). Must be timezone-aware.

    Returns:
        True if the market is currently in trading hours.

    Note:
        This does not account for holidays. Use Alpaca's get_clock()
        for authoritative US market status. This is a fast local check
        for scheduling decisions.
    """
    schedule = SCHEDULES[market]

    if schedule.is_24_7:
        return True

    if now is None:
        now = datetime.now(UTC)

    # Convert to the market's timezone
    local_now = now.astimezone(schedule.timezone)

    # Check if it's a trading day
    if local_now.weekday() not in schedule.trading_days:
        return False

    # Check if within trading hours
    current_time = local_now.time()
    return schedule.open_time <= current_time <= schedule.close_time


def get_market_for_symbol(symbol: str) -> Market:
    """
    Determine which market a symbol belongs to.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "BARC.L", "BTC-USD").

    Returns:
        The Market enum for the symbol.
    """
    if symbol.endswith(".L"):
        return Market.UK_STOCKS
    if symbol.endswith("-USD") or symbol.endswith("-GBP") or symbol.endswith("-EUR"):
        return Market.CRYPTO
    return Market.US_STOCKS


def get_open_markets(now: datetime | None = None) -> list[Market]:
    """Get all currently open markets."""
    return [m for m in Market if is_market_open(m, now)]
