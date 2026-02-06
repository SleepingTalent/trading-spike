"""
Tests for the Alpaca execution client.

Tests the response parsers and client methods with mocked MCP sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from execution.alpaca_client import (
    AlpacaExecutionClient,
    AlpacaClientError,
    _extract_field,
    _safe_float,
    _parse_account,
    _parse_order,
    _parse_orders,
    _parse_positions,
    _parse_clock,
    _parse_order_type,
    _parse_order_status,
)
from execution.models import (
    OrderSide,
    OrderType,
    OrderStatus,
    OrderRequest,
    TimeInForce,
)


# ── Parser Unit Tests ────────────────────────────────────────────────


class TestExtractField:
    def test_extracts_simple_field(self):
        text = "Account ID: ABC123\nCash: $50,000"
        assert _extract_field(text, "Account ID") == "ABC123"

    def test_extracts_field_with_dollar(self):
        text = "Cash: $50,000.00\nEquity: $75,000"
        assert _extract_field(text, "Cash") == "$50,000.00"

    def test_returns_default_when_missing(self):
        text = "Something: value"
        assert _extract_field(text, "Missing", "default") == "default"

    def test_handles_extra_whitespace(self):
        text = "  Cash:   $1,000.50  "
        assert _extract_field(text, "Cash") == "$1,000.50"

    def test_handles_empty_text(self):
        assert _extract_field("", "Field", "default") == "default"


class TestSafeFloat:
    def test_parses_simple_number(self):
        assert _safe_float("123.45") == 123.45

    def test_strips_dollar_sign(self):
        assert _safe_float("$1,234.56") == 1234.56

    def test_strips_commas(self):
        assert _safe_float("1,000,000") == 1000000.0

    def test_returns_default_for_none(self):
        assert _safe_float("None") == 0.0

    def test_returns_default_for_na(self):
        assert _safe_float("N/A") == 0.0

    def test_returns_default_for_empty(self):
        assert _safe_float("") == 0.0

    def test_returns_default_for_invalid(self):
        assert _safe_float("not_a_number", 99.0) == 99.0

    def test_handles_negative(self):
        assert _safe_float("-45.67") == -45.67


class TestParseAccount:
    def test_parses_account_response(self):
        text = """
        Account Information:
        --------------------
        Account ID: PA12345678
        Cash: $100,000.00
        Portfolio Value: $100,000.00
        Buying Power: $200,000.00
        Equity: $100,000.00
        Currency: USD
        Status: ACTIVE
        Paper Trading Account
        """
        account = _parse_account(text)
        assert account.account_id == "PA12345678"
        assert account.cash == 100000.0
        assert account.portfolio_value == 100000.0
        assert account.buying_power == 200000.0
        assert account.equity == 100000.0
        assert account.currency == "USD"
        assert account.paper is True

    def test_defaults_on_missing_fields(self):
        text = "Some minimal response"
        account = _parse_account(text)
        assert account.account_id == "unknown"
        assert account.cash == 0.0


class TestParseOrder:
    def test_parses_order_response(self):
        text = """
        Order Submitted Successfully:
        Order ID: abc-123-def
        Symbol: AAPL
        Side: buy
        Quantity: 10
        Type: market
        Status: accepted
        Submitted At: 2024-01-15T10:30:00Z
        """
        order = _parse_order(text)
        assert order.id == "abc-123-def"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.qty == 10.0
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.ACCEPTED

    def test_parses_filled_order(self):
        text = """
        Order ID: xyz-789
        Symbol: MSFT
        Side: sell
        Quantity: 5
        Filled Qty: 5
        Type: limit
        Status: filled
        Filled Avg Price: $350.25
        Submitted At: 2024-01-15T10:30:00Z
        Filled At: 2024-01-15T10:30:05Z
        """
        order = _parse_order(text)
        assert order.id == "xyz-789"
        assert order.side == OrderSide.SELL
        assert order.filled_qty == 5.0
        assert order.order_type == OrderType.LIMIT
        assert order.status == OrderStatus.FILLED
        assert order.filled_avg_price == 350.25


class TestParseOrders:
    def test_parses_empty_orders(self):
        assert _parse_orders("No open orders found.") == []
        assert _parse_orders("") == []

    def test_parses_multiple_orders(self):
        text = """
        Order ID: order-1
        Symbol: AAPL
        Side: buy
        Quantity: 10
        Type: market
        Status: new
        Submitted At: 2024-01-15T10:00:00Z

        Order ID: order-2
        Symbol: MSFT
        Side: sell
        Quantity: 5
        Type: limit
        Status: filled
        Submitted At: 2024-01-15T11:00:00Z
        """
        orders = _parse_orders(text)
        assert len(orders) == 2
        assert orders[0].symbol == "AAPL"
        assert orders[1].symbol == "MSFT"


class TestParsePositions:
    def test_parses_empty_positions(self):
        assert _parse_positions("No open positions.") == []
        assert _parse_positions("") == []

    def test_parses_position(self):
        text = """
        Symbol: AAPL
        Quantity: 10
        Side: long
        Market Value: $1,500.00
        Avg Entry Price: $145.00
        Current Price: $150.00
        Unrealized P/L: $50.00
        Unrealized P/L %: 3.45
        """
        positions = _parse_positions(text)
        assert len(positions) == 1
        pos = positions[0]
        assert pos.symbol == "AAPL"
        assert pos.qty == 10.0
        assert pos.side == "long"
        assert pos.market_value == 1500.0
        assert pos.avg_entry_price == 145.0
        assert pos.current_price == 150.0
        assert pos.unrealized_pl == 50.0


class TestParseClock:
    def test_parses_open_market(self):
        text = """
        Market Status:
        -------------
        Current Time: 2024-01-15T10:30:00-05:00
        Is Open: Yes
        Next Open: 2024-01-16T09:30:00-05:00
        Next Close: 2024-01-15T16:00:00-05:00
        """
        clock = _parse_clock(text)
        assert clock.is_open is True
        assert "2024-01-16" in clock.next_open
        assert "2024-01-15" in clock.next_close

    def test_parses_closed_market(self):
        text = """
        Market Status:
        Current Time: 2024-01-15T20:00:00-05:00
        Is Open: No
        Next Open: 2024-01-16T09:30:00-05:00
        Next Close: 2024-01-16T16:00:00-05:00
        """
        clock = _parse_clock(text)
        assert clock.is_open is False


class TestParseOrderType:
    def test_known_types(self):
        assert _parse_order_type("market") == OrderType.MARKET
        assert _parse_order_type("limit") == OrderType.LIMIT
        assert _parse_order_type("stop") == OrderType.STOP
        assert _parse_order_type("stop_limit") == OrderType.STOP_LIMIT
        assert _parse_order_type("trailing_stop") == OrderType.TRAILING_STOP

    def test_defaults_to_market(self):
        assert _parse_order_type("unknown") == OrderType.MARKET


class TestParseOrderStatus:
    def test_known_statuses(self):
        assert _parse_order_status("filled") == OrderStatus.FILLED
        assert _parse_order_status("canceled") == OrderStatus.CANCELED
        assert _parse_order_status("cancelled") == OrderStatus.CANCELED
        assert _parse_order_status("rejected") == OrderStatus.REJECTED

    def test_defaults_to_new(self):
        assert _parse_order_status("unknown") == OrderStatus.NEW


# ── Client Tests (Mocked MCP Session) ───────────────────────────────


class TestAlpacaClient:
    @pytest.fixture
    def mock_session(self):
        """Create a mocked MCP ClientSession."""
        session = AsyncMock()
        return session

    def _make_tool_result(self, text: str, is_error: bool = False):
        """Create a mock tool result."""
        content = MagicMock()
        content.text = text
        result = MagicMock()
        result.content = [content]
        result.isError = is_error
        return result

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result("OK")
        result = await client._call_tool("test_tool", {"key": "value"})
        assert result == "OK"
        mock_session.call_tool.assert_called_once_with("test_tool", {"key": "value"})

    @pytest.mark.asyncio
    async def test_call_tool_error(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result(
            "Something went wrong", is_error=True
        )
        with pytest.raises(AlpacaClientError, match="Something went wrong"):
            await client._call_tool("test_tool")

    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        client = AlpacaExecutionClient()
        with pytest.raises(AlpacaClientError, match="Not connected"):
            await client._call_tool("test_tool")

    @pytest.mark.asyncio
    async def test_get_account(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result(
            "Account ID: TEST123\nCash: $50,000\nPortfolio Value: $50,000\n"
            "Buying Power: $100,000\nEquity: $50,000\nPaper trading"
        )
        account = await client.get_account()
        assert account.account_id == "TEST123"
        assert account.cash == 50000.0
        assert account.paper is True

    @pytest.mark.asyncio
    async def test_submit_order(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result(
            "Order ID: ord-001\nSymbol: AAPL\nSide: buy\nQuantity: 10\n"
            "Type: market\nStatus: accepted\nSubmitted At: 2024-01-15T10:00:00Z"
        )
        request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            qty=10,
        )
        order = await client.submit_order(request)
        assert order.id == "ord-001"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY

        # Verify the tool was called with correct args
        call_args = mock_session.call_tool.call_args
        assert call_args[0][0] == "place_order"
        assert call_args[0][1]["symbol"] == "AAPL"
        assert call_args[0][1]["side"] == "buy"
        assert call_args[0][1]["qty"] == "10"

    @pytest.mark.asyncio
    async def test_get_positions(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result(
            "Symbol: AAPL\nQuantity: 10\nSide: long\nMarket Value: $1,500\n"
            "Avg Entry Price: $145\nCurrent Price: $150\n"
            "Unrealized P/L: $50\nUnrealized P/L %: 3.45"
        )
        positions = await client.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_clock(self, mock_session):
        client = AlpacaExecutionClient()
        client._session = mock_session

        mock_session.call_tool.return_value = self._make_tool_result(
            "Market Status:\nCurrent Time: 2024-01-15T10:30:00\n"
            "Is Open: Yes\nNext Open: 2024-01-16T09:30:00\n"
            "Next Close: 2024-01-15T16:00:00"
        )
        clock = await client.get_clock()
        assert clock.is_open is True
