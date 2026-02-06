"""
Tests for the simulated UK stock ledger.
"""

import json
import pytest
from pathlib import Path

from execution.models import OrderRequest, OrderSide, OrderType, OrderStatus
from execution.simulated_ledger import SimulatedLedger


@pytest.fixture
def ledger(tmp_path):
    """Create a ledger with a temporary file."""
    return SimulatedLedger(ledger_path=str(tmp_path / "test_ledger.json"))


@pytest.fixture
def ledger_path(tmp_path):
    """Return just the path for a ledger file."""
    return str(tmp_path / "test_ledger.json")


class TestSubmitOrder:
    def test_buy_creates_position(self, ledger):
        request = OrderRequest(
            symbol="BARC.L",
            side=OrderSide.BUY,
            qty=100,
        )
        order = ledger.submit_order(request, current_price=2.50)

        assert order.status == OrderStatus.FILLED
        assert order.symbol == "BARC.L"
        assert order.side == OrderSide.BUY
        assert order.qty == 100
        assert order.filled_avg_price == 2.50

    def test_buy_reduces_cash(self, ledger):
        initial_cash = ledger.cash
        request = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(request, current_price=2.50)

        assert ledger.cash == initial_cash - 250.0

    def test_sell_increases_cash(self, ledger):
        # Buy first
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.50)
        cash_after_buy = ledger.cash

        # Sell at higher price
        sell = OrderRequest(symbol="BARC.L", side=OrderSide.SELL, qty=100)
        ledger.submit_order(sell, current_price=3.00)

        assert ledger.cash == cash_after_buy + 300.0

    def test_sell_removes_position(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.50)

        sell = OrderRequest(symbol="BARC.L", side=OrderSide.SELL, qty=100)
        ledger.submit_order(sell, current_price=3.00)

        positions = ledger.get_positions()
        assert len(positions) == 0

    def test_partial_sell(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.50)

        sell = OrderRequest(symbol="BARC.L", side=OrderSide.SELL, qty=50)
        ledger.submit_order(sell, current_price=3.00)

        positions = ledger.get_positions()
        assert len(positions) == 1
        assert positions[0].qty == 50

    def test_buy_insufficient_cash(self, ledger):
        request = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=1000000)
        with pytest.raises(ValueError, match="Insufficient cash"):
            ledger.submit_order(request, current_price=100.0)

    def test_sell_no_position(self, ledger):
        request = OrderRequest(symbol="BARC.L", side=OrderSide.SELL, qty=100)
        with pytest.raises(ValueError, match="No position"):
            ledger.submit_order(request, current_price=2.50)

    def test_sell_more_than_held(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=50)
        ledger.submit_order(buy, current_price=2.50)

        sell = OrderRequest(symbol="BARC.L", side=OrderSide.SELL, qty=100)
        with pytest.raises(ValueError, match="Cannot sell"):
            ledger.submit_order(sell, current_price=2.50)

    def test_buy_averages_in(self, ledger):
        buy1 = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy1, current_price=2.00)

        buy2 = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy2, current_price=3.00)

        positions = ledger.get_positions()
        assert len(positions) == 1
        assert positions[0].qty == 200
        assert positions[0].avg_entry_price == 2.50  # Average of 2.00 and 3.00


class TestGetPositions:
    def test_empty_positions(self, ledger):
        assert ledger.get_positions() == []

    def test_positions_with_price_lookup(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.00)

        positions = ledger.get_positions(price_lookup={"BARC.L": 2.50})
        assert len(positions) == 1
        pos = positions[0]
        assert pos.current_price == 2.50
        assert pos.unrealized_pl == 50.0  # (2.50 - 2.00) * 100
        assert pos.unrealized_plpc == pytest.approx(25.0)  # 50/200 * 100

    def test_positions_without_price_lookup(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.00)

        positions = ledger.get_positions()
        assert positions[0].unrealized_pl == 0.0

    def test_multiple_positions(self, ledger):
        for symbol, price in [("BARC.L", 2.00), ("LLOY.L", 0.50), ("BP.L", 5.00)]:
            buy = OrderRequest(symbol=symbol, side=OrderSide.BUY, qty=100)
            ledger.submit_order(buy, current_price=price)

        positions = ledger.get_positions()
        assert len(positions) == 3
        symbols = {p.symbol for p in positions}
        assert symbols == {"BARC.L", "LLOY.L", "BP.L"}


class TestClosePosition:
    def test_close_position(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.00)

        order = ledger.close_position("BARC.L", current_price=2.50)
        assert order.status == OrderStatus.FILLED
        assert order.side == OrderSide.SELL
        assert order.qty == 100

        assert ledger.get_positions() == []

    def test_close_nonexistent_position(self, ledger):
        with pytest.raises(ValueError, match="No position"):
            ledger.close_position("BARC.L", current_price=2.50)


class TestCloseAllPositions:
    def test_close_all(self, ledger):
        for symbol, price in [("BARC.L", 2.00), ("LLOY.L", 0.50)]:
            buy = OrderRequest(symbol=symbol, side=OrderSide.BUY, qty=100)
            ledger.submit_order(buy, current_price=price)

        orders = ledger.close_all_positions({"BARC.L": 2.50, "LLOY.L": 0.60})
        assert len(orders) == 2
        assert ledger.get_positions() == []


class TestPersistence:
    def test_state_persists(self, ledger_path):
        # Create ledger, buy, then discard
        ledger1 = SimulatedLedger(ledger_path=ledger_path)
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger1.submit_order(buy, current_price=2.50)

        # Load new ledger from same file
        ledger2 = SimulatedLedger(ledger_path=ledger_path)
        positions = ledger2.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "BARC.L"
        assert positions[0].qty == 100

    def test_cash_persists(self, ledger_path):
        ledger1 = SimulatedLedger(ledger_path=ledger_path)
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger1.submit_order(buy, current_price=2.50)
        expected_cash = ledger1.cash

        ledger2 = SimulatedLedger(ledger_path=ledger_path)
        assert ledger2.cash == expected_cash


class TestReset:
    def test_reset_clears_everything(self, ledger):
        buy = OrderRequest(symbol="BARC.L", side=OrderSide.BUY, qty=100)
        ledger.submit_order(buy, current_price=2.50)

        ledger.reset()
        assert ledger.get_positions() == []
        assert ledger.cash == 10000.0
