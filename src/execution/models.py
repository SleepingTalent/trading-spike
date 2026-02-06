"""Domain models for the execution layer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    PENDING_NEW = "pending_new"
    ACCEPTED = "accepted"


class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


@dataclass
class OrderRequest:
    """Request to place an order."""

    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: float | None = None
    stop_price: float | None = None
    trail_percent: float | None = None


@dataclass
class Order:
    """A submitted or filled order."""

    id: str
    symbol: str
    side: OrderSide
    qty: float
    filled_qty: float
    order_type: OrderType
    status: OrderStatus
    submitted_at: str
    filled_at: str | None = None
    filled_avg_price: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None


@dataclass
class Position:
    """A current position in a symbol."""

    symbol: str
    qty: float
    side: str  # "long" or "short"
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float


@dataclass
class AccountInfo:
    """Trading account summary."""

    account_id: str
    cash: float
    portfolio_value: float
    buying_power: float
    equity: float
    currency: str = "USD"
    paper: bool = True


@dataclass
class MarketClock:
    """Market clock status."""

    is_open: bool
    next_open: str
    next_close: str
    timestamp: str
