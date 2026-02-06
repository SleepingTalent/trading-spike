"""
Simulated Ledger for UK Stocks

Alpaca does not support LSE stocks, so we track UK positions
locally using a JSON file. Orders are "filled" instantly at
the current price fetched from yfinance.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


@dataclass
class LedgerPosition:
    """Internal ledger entry for a simulated position."""

    symbol: str
    qty: float
    avg_entry_price: float
    side: str = "long"
    opened_at: str = ""


@dataclass
class LedgerState:
    """Persisted state of the simulated ledger."""

    positions: dict[str, LedgerPosition] = field(default_factory=dict)
    orders: list[dict] = field(default_factory=list)
    cash: float = 10000.0
    initial_cash: float = 10000.0


class SimulatedLedger:
    """
    JSON-file-based position ledger for UK stocks.

    Simulates order fills against prices provided by the caller.
    Persists state to a JSON file so positions survive restarts.

    Usage:
        ledger = SimulatedLedger(ledger_path="data/uk_ledger.json")
        order = ledger.submit_order(request, current_price=150.0)
        positions = ledger.get_positions(price_lookup)
    """

    def __init__(self, ledger_path: str = "data/uk_ledger.json"):
        self._path = Path(ledger_path)
        self._state = self._load()

    def _load(self) -> LedgerState:
        """Load state from disk, or create fresh state."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                positions = {}
                for sym, pos_data in data.get("positions", {}).items():
                    positions[sym] = LedgerPosition(**pos_data)
                return LedgerState(
                    positions=positions,
                    orders=data.get("orders", []),
                    cash=data.get("cash", 10000.0),
                    initial_cash=data.get("initial_cash", 10000.0),
                )
            except (json.JSONDecodeError, TypeError, KeyError):
                return LedgerState()
        return LedgerState()

    def _save(self) -> None:
        """Persist state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "positions": {
                sym: asdict(pos) for sym, pos in self._state.positions.items()
            },
            "orders": self._state.orders,
            "cash": self._state.cash,
            "initial_cash": self._state.initial_cash,
        }
        self._path.write_text(json.dumps(data, indent=2))

    def submit_order(self, request: OrderRequest, current_price: float) -> Order:
        """
        Simulate an order fill at the given price.

        Args:
            request: The order to submit.
            current_price: Current market price for the symbol.

        Returns:
            A filled Order.

        Raises:
            ValueError: If insufficient cash for a buy, or no position for a sell.
        """
        order_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        cost = current_price * request.qty

        if request.side == OrderSide.BUY:
            if cost > self._state.cash:
                raise ValueError(
                    f"Insufficient cash: need ${cost:.2f}, have ${self._state.cash:.2f}"
                )
            self._state.cash -= cost

            # Update or create position
            if request.symbol in self._state.positions:
                pos = self._state.positions[request.symbol]
                # Average in
                total_qty = pos.qty + request.qty
                pos.avg_entry_price = (
                    (pos.avg_entry_price * pos.qty) + (current_price * request.qty)
                ) / total_qty
                pos.qty = total_qty
            else:
                self._state.positions[request.symbol] = LedgerPosition(
                    symbol=request.symbol,
                    qty=request.qty,
                    avg_entry_price=current_price,
                    opened_at=now,
                )

        elif request.side == OrderSide.SELL:
            if request.symbol not in self._state.positions:
                raise ValueError(f"No position in {request.symbol} to sell")
            pos = self._state.positions[request.symbol]
            if request.qty > pos.qty:
                raise ValueError(
                    f"Cannot sell {request.qty} shares of {request.symbol}, "
                    f"only hold {pos.qty}"
                )
            self._state.cash += cost
            pos.qty -= request.qty
            if pos.qty <= 0:
                del self._state.positions[request.symbol]

        order = Order(
            id=order_id,
            symbol=request.symbol,
            side=request.side,
            qty=request.qty,
            filled_qty=request.qty,
            order_type=request.order_type,
            status=OrderStatus.FILLED,
            submitted_at=now,
            filled_at=now,
            filled_avg_price=current_price,
        )

        # Record in order history
        self._state.orders.append({
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": order.qty,
            "price": current_price,
            "timestamp": now,
        })

        self._save()
        return order

    def get_positions(
        self, price_lookup: dict[str, float] | None = None
    ) -> list[Position]:
        """
        Get all open positions with current P&L.

        Args:
            price_lookup: Dict of symbol -> current_price for P&L calculation.
                         If not provided, P&L fields will be zero.

        Returns:
            List of Position objects.
        """
        positions = []
        for sym, ledger_pos in self._state.positions.items():
            current_price = (price_lookup or {}).get(sym, ledger_pos.avg_entry_price)
            market_value = current_price * ledger_pos.qty
            unrealized_pl = (current_price - ledger_pos.avg_entry_price) * ledger_pos.qty
            entry_value = ledger_pos.avg_entry_price * ledger_pos.qty
            unrealized_plpc = (unrealized_pl / entry_value * 100) if entry_value else 0.0

            positions.append(Position(
                symbol=sym,
                qty=ledger_pos.qty,
                side=ledger_pos.side,
                market_value=market_value,
                avg_entry_price=ledger_pos.avg_entry_price,
                current_price=current_price,
                unrealized_pl=unrealized_pl,
                unrealized_plpc=unrealized_plpc,
            ))
        return positions

    def close_position(self, symbol: str, current_price: float) -> Order:
        """Close an entire position at the given price."""
        if symbol not in self._state.positions:
            raise ValueError(f"No position in {symbol}")
        pos = self._state.positions[symbol]
        request = OrderRequest(
            symbol=symbol,
            side=OrderSide.SELL,
            qty=pos.qty,
            order_type=OrderType.MARKET,
        )
        return self.submit_order(request, current_price)

    def close_all_positions(self, price_lookup: dict[str, float]) -> list[Order]:
        """Close all positions at the given prices."""
        orders = []
        for symbol in list(self._state.positions.keys()):
            if symbol in price_lookup:
                orders.append(self.close_position(symbol, price_lookup[symbol]))
        return orders

    @property
    def cash(self) -> float:
        return self._state.cash

    @property
    def portfolio_value(self, price_lookup: dict[str, float] | None = None) -> float:
        """Total portfolio value: cash + positions market value."""
        positions_value = sum(
            pos.qty * pos.avg_entry_price
            for pos in self._state.positions.values()
        )
        return self._state.cash + positions_value

    def reset(self) -> None:
        """Reset ledger to initial state."""
        self._state = LedgerState()
        self._save()
