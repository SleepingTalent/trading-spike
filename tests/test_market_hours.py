"""
Tests for market hours logic.
"""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from execution.market_hours import (
    Market,
    US_EASTERN,
    UK_LONDON,
    get_market_for_symbol,
    get_open_markets,
    get_schedule,
    is_market_open,
)


class TestGetMarketForSymbol:
    def test_us_stock(self):
        assert get_market_for_symbol("AAPL") == Market.US_STOCKS
        assert get_market_for_symbol("MSFT") == Market.US_STOCKS
        assert get_market_for_symbol("NVDA") == Market.US_STOCKS

    def test_uk_stock(self):
        assert get_market_for_symbol("BARC.L") == Market.UK_STOCKS
        assert get_market_for_symbol("LLOY.L") == Market.UK_STOCKS
        assert get_market_for_symbol("HSBA.L") == Market.UK_STOCKS

    def test_crypto(self):
        assert get_market_for_symbol("BTC-USD") == Market.CRYPTO
        assert get_market_for_symbol("ETH-USD") == Market.CRYPTO
        assert get_market_for_symbol("SOL-USD") == Market.CRYPTO
        assert get_market_for_symbol("BTC-GBP") == Market.CRYPTO
        assert get_market_for_symbol("ETH-EUR") == Market.CRYPTO


class TestIsMarketOpen:
    def test_crypto_always_open(self):
        # Monday morning
        now = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)
        assert is_market_open(Market.CRYPTO, now) is True

        # Saturday night
        now = datetime(2024, 1, 20, 23, 0, tzinfo=timezone.utc)
        assert is_market_open(Market.CRYPTO, now) is True

    def test_us_market_open_during_hours(self):
        # 10:30 AM Eastern on Monday = market is open
        now = datetime(2024, 1, 15, 10, 30, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is True

    def test_us_market_closed_after_hours(self):
        # 5:00 PM Eastern on Monday = market is closed
        now = datetime(2024, 1, 15, 17, 0, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is False

    def test_us_market_closed_on_weekend(self):
        # 10:30 AM Eastern on Saturday
        now = datetime(2024, 1, 20, 10, 30, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is False

    def test_us_market_closed_before_open(self):
        # 8:00 AM Eastern on Monday = before 9:30 AM open
        now = datetime(2024, 1, 15, 8, 0, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is False

    def test_uk_market_open_during_hours(self):
        # 10:00 AM London on Monday
        now = datetime(2024, 1, 15, 10, 0, tzinfo=UK_LONDON)
        assert is_market_open(Market.UK_STOCKS, now) is True

    def test_uk_market_closed_after_hours(self):
        # 5:00 PM London on Monday
        now = datetime(2024, 1, 15, 17, 0, tzinfo=UK_LONDON)
        assert is_market_open(Market.UK_STOCKS, now) is False

    def test_uk_market_closed_on_weekend(self):
        # 10:00 AM London on Sunday
        now = datetime(2024, 1, 21, 10, 0, tzinfo=UK_LONDON)
        assert is_market_open(Market.UK_STOCKS, now) is False

    def test_us_market_open_at_exact_open(self):
        # Exactly 9:30 AM Eastern
        now = datetime(2024, 1, 15, 9, 30, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is True

    def test_us_market_open_at_exact_close(self):
        # Exactly 4:00 PM Eastern
        now = datetime(2024, 1, 15, 16, 0, tzinfo=US_EASTERN)
        assert is_market_open(Market.US_STOCKS, now) is True


class TestGetOpenMarkets:
    def test_weekday_during_overlap(self):
        # 10:00 AM Eastern on Monday = 3:00 PM London
        # US market is open (9:30-16:00 ET), UK is open (8:00-16:30 London), crypto always
        now = datetime(2024, 1, 15, 10, 0, tzinfo=US_EASTERN)
        open_markets = get_open_markets(now)
        assert Market.CRYPTO in open_markets
        assert Market.US_STOCKS in open_markets
        assert Market.UK_STOCKS in open_markets

    def test_weekend_only_crypto(self):
        # Saturday noon UTC
        now = datetime(2024, 1, 20, 12, 0, tzinfo=timezone.utc)
        open_markets = get_open_markets(now)
        assert open_markets == [Market.CRYPTO]


class TestGetSchedule:
    def test_us_schedule(self):
        schedule = get_schedule(Market.US_STOCKS)
        assert schedule.open_time == time(9, 30)
        assert schedule.close_time == time(16, 0)
        assert schedule.is_24_7 is False

    def test_crypto_schedule(self):
        schedule = get_schedule(Market.CRYPTO)
        assert schedule.is_24_7 is True
        assert 6 in schedule.trading_days  # Sunday
