"""Normalized data model that both brokerage providers (or a CSV import)
must produce. Keeping this small and provider-agnostic is what lets
engine/metrics.py stay correct regardless of where the numbers came from.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EquitySnapshot:
    """One day's total account value, as of market close (or as-of the
    time the daily job ran). This is the only fact the whole site is
    built on: everything else (returns, drawdown, charts) is derived
    from a time series of these.
    """

    as_of: date
    total_equity: float  # cash + market value of all positions, in account currency
    cash: float
    source: str  # "schwab" | "snaptrade" | "manual"

    def __post_init__(self) -> None:
        if self.total_equity < 0:
            raise ValueError(f"total_equity must be >= 0, got {self.total_equity}")
        if self.cash < 0:
            raise ValueError(f"cash must be >= 0, got {self.cash}")
