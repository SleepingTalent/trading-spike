"""
Alpaca Execution Client

Wraps the Alpaca MCP server, managing a subprocess and MCP client session.
Provides typed methods for order submission, position management, and account info.
"""

import json
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .models import (
    AccountInfo,
    MarketClock,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class AlpacaClientError(Exception):
    """Raised when an Alpaca MCP tool call fails."""


class AlpacaExecutionClient:
    """
    MCP client wrapper for the Alpaca MCP server.

    Starts the Alpaca MCP server as a subprocess via stdio transport
    and exposes typed methods for trading operations.

    Usage:
        async with AlpacaExecutionClient() as client:
            account = await client.get_account()
            order = await client.submit_order(OrderRequest(...))
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ):
        self._api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self._secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")
        self._paper = paper
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> "AlpacaExecutionClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Start the Alpaca MCP server and establish a client session."""
        env = {
            **os.environ,
            "ALPACA_API_KEY": self._api_key,
            "ALPACA_SECRET_KEY": self._secret_key,
            "ALPACA_PAPER_TRADE": "true" if self._paper else "false",
        }

        server_params = StdioServerParameters(
            command="uvx",
            args=["alpaca-mcp-server", "serve"],
            env=env,
        )

        self._exit_stack = AsyncExitStack()
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def disconnect(self) -> None:
        """Shut down the MCP session and server process."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None

    def _ensure_connected(self) -> ClientSession:
        if self._session is None:
            raise AlpacaClientError("Not connected. Call connect() first.")
        return self._session

    async def _call_tool(self, name: str, arguments: dict | None = None) -> str:
        """Call an Alpaca MCP tool and return the text result."""
        session = self._ensure_connected()
        result = await session.call_tool(name, arguments or {})

        # MCP tool results are a list of content blocks
        texts = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)

        combined = "\n".join(texts)
        if result.isError:
            raise AlpacaClientError(f"Tool '{name}' failed: {combined}")

        return combined

    # ── Account ──────────────────────────────────────────────────────

    async def get_account(self) -> AccountInfo:
        """Get account information."""
        text = await self._call_tool("get_account")
        return _parse_account(text)

    # ── Orders ───────────────────────────────────────────────────────

    async def submit_order(self, request: OrderRequest) -> Order:
        """Submit a new order through Alpaca."""
        args: dict = {
            "symbol": request.symbol,
            "side": request.side.value,
            "qty": str(request.qty),
            "type": request.order_type.value,
            "time_in_force": request.time_in_force.value,
        }
        if request.limit_price is not None:
            args["limit_price"] = str(request.limit_price)
        if request.stop_price is not None:
            args["stop_price"] = str(request.stop_price)
        if request.trail_percent is not None:
            args["trail_percent"] = str(request.trail_percent)

        text = await self._call_tool("place_order", args)
        return _parse_order(text)

    async def get_orders(self, status: str = "open") -> list[Order]:
        """Get orders filtered by status."""
        text = await self._call_tool("get_orders", {"status": status})
        return _parse_orders(text)

    async def cancel_order(self, order_id: str) -> str:
        """Cancel a specific order by ID."""
        return await self._call_tool("cancel_order_by_id", {"order_id": order_id})

    async def cancel_all_orders(self) -> str:
        """Cancel all open orders."""
        return await self._call_tool("cancel_all_orders")

    # ── Positions ────────────────────────────────────────────────────

    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        text = await self._call_tool("get_positions")
        return _parse_positions(text)

    async def close_position(self, symbol: str) -> str:
        """Close a position for a given symbol."""
        return await self._call_tool(
            "close_position", {"symbol_or_id": symbol}
        )

    async def close_all_positions(self) -> str:
        """Close all open positions."""
        return await self._call_tool("close_all_positions")

    # ── Market Clock ─────────────────────────────────────────────────

    async def get_clock(self) -> MarketClock:
        """Get current market clock status."""
        text = await self._call_tool("get_clock")
        return _parse_clock(text)


# ── Response Parsers ─────────────────────────────────────────────────
#
# The Alpaca MCP server returns human-readable formatted text.
# These parsers extract key-value pairs from that text.


def _extract_field(text: str, field: str, default: str = "") -> str:
    """Extract a field value from formatted text output."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(field):
            # Handle "Field: Value" and "Field:  Value" patterns
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return default


def _safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert a string to float, stripping $ and commas."""
    try:
        cleaned = value.replace("$", "").replace(",", "").strip()
        if not cleaned or cleaned in ("None", "N/A", ""):
            return default
        return float(cleaned)
    except (ValueError, AttributeError):
        return default


def _parse_account(text: str) -> AccountInfo:
    """Parse account info from Alpaca MCP text response."""
    return AccountInfo(
        account_id=_extract_field(text, "Account ID", "unknown"),
        cash=_safe_float(_extract_field(text, "Cash")),
        portfolio_value=_safe_float(_extract_field(text, "Portfolio Value")),
        buying_power=_safe_float(_extract_field(text, "Buying Power")),
        equity=_safe_float(_extract_field(text, "Equity")),
        currency=_extract_field(text, "Currency", "USD"),
        paper="paper" in text.lower() or "Paper" in text,
    )


def _parse_order(text: str) -> Order:
    """Parse a single order from Alpaca MCP text response."""
    return Order(
        id=_extract_field(text, "Order ID", _extract_field(text, "ID", "unknown")),
        symbol=_extract_field(text, "Symbol", "unknown"),
        side=OrderSide(_extract_field(text, "Side", "buy").lower()),
        qty=_safe_float(_extract_field(text, "Quantity", _extract_field(text, "Qty", "0"))),
        filled_qty=_safe_float(_extract_field(text, "Filled Qty", _extract_field(text, "Filled Quantity", "0"))),
        order_type=_parse_order_type(_extract_field(text, "Type", "market")),
        status=_parse_order_status(_extract_field(text, "Status", "new")),
        submitted_at=_extract_field(text, "Submitted At", _extract_field(text, "Created At", "")),
        filled_at=_extract_field(text, "Filled At", None),
        filled_avg_price=_safe_float(_extract_field(text, "Filled Avg Price", _extract_field(text, "Average Fill Price", "0"))) or None,
    )


def _parse_orders(text: str) -> list[Order]:
    """Parse multiple orders from Alpaca MCP text response."""
    if not text.strip() or "no open orders" in text.lower() or "no orders" in text.lower():
        return []

    # Split on order boundaries — each order typically starts with a separator or "Order ID:"
    orders = []
    current_block = []

    for line in text.splitlines():
        stripped = line.strip()
        # Detect order boundary: a new "Order ID" or separator line
        if (stripped.startswith("Order ID:") or stripped.startswith("ID:")) and current_block:
            orders.append(_parse_order("\n".join(current_block)))
            current_block = []
        if stripped:
            current_block.append(line)

    if current_block:
        orders.append(_parse_order("\n".join(current_block)))

    return orders


def _parse_positions(text: str) -> list[Position]:
    """Parse positions from Alpaca MCP text response."""
    if not text.strip() or "no open positions" in text.lower() or "no positions" in text.lower():
        return []

    positions = []
    current_block = []

    for line in text.splitlines():
        stripped = line.strip()
        if (stripped.startswith("Symbol:") or stripped.startswith("---")) and current_block:
            block_text = "\n".join(current_block)
            if _extract_field(block_text, "Symbol"):
                positions.append(_parse_single_position(block_text))
            current_block = []
        if stripped and not stripped.startswith("---"):
            current_block.append(line)

    if current_block:
        block_text = "\n".join(current_block)
        if _extract_field(block_text, "Symbol"):
            positions.append(_parse_single_position(block_text))

    return positions


def _parse_single_position(text: str) -> Position:
    """Parse a single position block."""
    return Position(
        symbol=_extract_field(text, "Symbol", "unknown"),
        qty=_safe_float(_extract_field(text, "Quantity", _extract_field(text, "Qty", "0"))),
        side=_extract_field(text, "Side", "long").lower(),
        market_value=_safe_float(_extract_field(text, "Market Value")),
        avg_entry_price=_safe_float(_extract_field(text, "Avg Entry Price", _extract_field(text, "Average Entry", "0"))),
        current_price=_safe_float(_extract_field(text, "Current Price")),
        unrealized_pl=_safe_float(_extract_field(text, "Unrealized P/L", _extract_field(text, "Unrealized PL", "0"))),
        unrealized_plpc=_safe_float(_extract_field(text, "Unrealized P/L %", _extract_field(text, "Unrealized PL %", "0"))),
    )


def _parse_clock(text: str) -> MarketClock:
    """Parse market clock from Alpaca MCP text response."""
    is_open_str = _extract_field(text, "Is Open", "No")
    return MarketClock(
        is_open="yes" in is_open_str.lower() or "true" in is_open_str.lower(),
        next_open=_extract_field(text, "Next Open", ""),
        next_close=_extract_field(text, "Next Close", ""),
        timestamp=_extract_field(text, "Current Time", ""),
    )


def _parse_order_type(value: str) -> OrderType:
    """Parse an order type string into the enum."""
    mapping = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
        "stop_limit": OrderType.STOP_LIMIT,
        "trailing_stop": OrderType.TRAILING_STOP,
    }
    return mapping.get(value.lower().strip(), OrderType.MARKET)


def _parse_order_status(value: str) -> OrderStatus:
    """Parse an order status string into the enum."""
    mapping = {
        "new": OrderStatus.NEW,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELED,
        "cancelled": OrderStatus.CANCELED,
        "expired": OrderStatus.EXPIRED,
        "rejected": OrderStatus.REJECTED,
        "pending_new": OrderStatus.PENDING_NEW,
        "accepted": OrderStatus.ACCEPTED,
    }
    return mapping.get(value.lower().strip(), OrderStatus.NEW)
