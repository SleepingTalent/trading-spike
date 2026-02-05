"""
RSI Mean-Reversion Strategy Definition

This module defines the trading strategy parameters and rules used by the backtest system.
"""

from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Type of trading signal."""
    ENTRY = "entry"
    EXIT = "exit"


@dataclass(frozen=True)
class StrategyConfig:
    """
    RSI Mean-Reversion Strategy Configuration

    Entry Logic:
        - Buy when RSI crosses BELOW the entry threshold (oversold condition)
        - This signals a potential reversal from oversold territory

    Exit Logic:
        - Sell when RSI crosses ABOVE the exit threshold (overbought condition)
        - OR when trailing stop is triggered (price drops X% from peak)

    Risk Management:
        - Trailing stop follows price up and triggers on pullback
        - Commission fees applied to all trades
    """

    # RSI Parameters
    rsi_window: int = 14
    rsi_entry_threshold: float = 30.0  # Buy when RSI crosses below this (oversold)
    rsi_exit_threshold: float = 70.0   # Sell when RSI crosses above this (overbought)

    # Trailing Stop Parameters
    trailing_stop_pct: float = 0.03    # 3% trailing stop

    # Execution Parameters
    commission_pct: float = 0.001      # 0.1% commission per trade
    initial_cash: float = 10000.0      # Default starting capital


# Default strategy configuration
DEFAULT_STRATEGY = StrategyConfig()

# Conservative strategy - tighter stops, more extreme RSI levels
CONSERVATIVE_STRATEGY = StrategyConfig(
    rsi_window=14,
    rsi_entry_threshold=25.0,   # More oversold before entry
    rsi_exit_threshold=75.0,    # More overbought before exit
    trailing_stop_pct=0.02,     # Tighter 2% trailing stop
)

# Aggressive strategy - wider stops, less extreme RSI levels
AGGRESSIVE_STRATEGY = StrategyConfig(
    rsi_window=10,              # Faster RSI
    rsi_entry_threshold=35.0,   # Earlier entry
    rsi_exit_threshold=65.0,    # Earlier exit
    trailing_stop_pct=0.05,     # Wider 5% trailing stop
)


def get_strategy_description(config: StrategyConfig) -> str:
    """Generate a human-readable description of the strategy."""
    return f"""
RSI Mean-Reversion Strategy
============================

ENTRY RULES:
- Signal: RSI({config.rsi_window}) crosses BELOW {config.rsi_entry_threshold}
- Condition: Oversold - price has fallen significantly
- Action: BUY at market price

EXIT RULES:
- Signal 1: RSI({config.rsi_window}) crosses ABOVE {config.rsi_exit_threshold}
  - Condition: Overbought - price has risen significantly
  - Action: SELL at market price

- Signal 2: Trailing Stop triggered at {config.trailing_stop_pct * 100:.1f}%
  - Condition: Price falls {config.trailing_stop_pct * 100:.1f}% from highest point since entry
  - Action: SELL at stop price (risk management)

PARAMETERS:
- RSI Window: {config.rsi_window} periods
- RSI Entry (Oversold): {config.rsi_entry_threshold}
- RSI Exit (Overbought): {config.rsi_exit_threshold}
- Trailing Stop: {config.trailing_stop_pct * 100:.1f}%
- Commission: {config.commission_pct * 100:.2f}%

RATIONALE:
The RSI (Relative Strength Index) measures momentum on a 0-100 scale.
Values below 30 typically indicate oversold conditions (potential buying opportunity).
Values above 70 typically indicate overbought conditions (potential selling opportunity).
The trailing stop protects profits by selling if price reverses from its peak.
"""
