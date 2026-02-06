#!/usr/bin/env python3
"""
Alpaca Paper Trading Connection Test

Connects to the Alpaca MCP server, verifies the connection,
and runs a basic workflow: get account → get clock → get positions.

Requires ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.

Usage:
    uv run python scripts/test_alpaca_connection.py
"""

import asyncio
import sys

sys.path.insert(0, "src")

from execution.alpaca_client import AlpacaExecutionClient, AlpacaClientError


async def main():
    print("=" * 60)
    print("Alpaca Paper Trading Connection Test")
    print("=" * 60)

    try:
        async with AlpacaExecutionClient(paper=True) as client:
            # 1. Get account info
            print("\n1. Fetching account info...")
            account = await client.get_account()
            print(f"   Account ID:      {account.account_id}")
            print(f"   Cash:            ${account.cash:,.2f}")
            print(f"   Portfolio Value:  ${account.portfolio_value:,.2f}")
            print(f"   Buying Power:    ${account.buying_power:,.2f}")
            print(f"   Equity:          ${account.equity:,.2f}")

            # 2. Get market clock
            print("\n2. Fetching market clock...")
            clock = await client.get_clock()
            print(f"   Market Open:     {'Yes' if clock.is_open else 'No'}")
            print(f"   Next Open:       {clock.next_open}")
            print(f"   Next Close:      {clock.next_close}")

            # 3. Get positions
            print("\n3. Fetching positions...")
            positions = await client.get_positions()
            if positions:
                for pos in positions:
                    print(f"   {pos.symbol}: {pos.qty} shares @ ${pos.avg_entry_price:.2f}"
                          f" (P&L: ${pos.unrealized_pl:+,.2f})")
            else:
                print("   No open positions")

            # 4. Get open orders
            print("\n4. Fetching open orders...")
            orders = await client.get_orders(status="open")
            if orders:
                for order in orders:
                    print(f"   {order.side.value.upper()} {order.qty} {order.symbol}"
                          f" ({order.status.value})")
            else:
                print("   No open orders")

            print("\n" + "=" * 60)
            print("Connection test PASSED")
            print("=" * 60)

    except AlpacaClientError as e:
        print(f"\nConnection test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("\nMake sure:")
        print("  1. ALPACA_API_KEY and ALPACA_SECRET_KEY are set")
        print("  2. alpaca-mcp-server is installed (uvx alpaca-mcp-server)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
