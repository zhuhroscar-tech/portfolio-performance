"""Pure functions that turn a time series of EquitySnapshot into the
performance metrics the site displays. No I/O, no network, no
brokerage-specific code here on purpose -- this is the part that gets
unit tested with synthetic data and never has to change when a provider
changes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schemas import EquitySnapshot


@dataclass(frozen=True)
class PerformanceSummary:
    inception_date: str
    as_of_date: str
    days_tracked: int
    total_return_pct: float
    max_drawdown_pct: float
    max_drawdown_date: str
    best_day_pct: float | None
    worst_day_pct: float | None
    indexed_series: list[dict]  # [{"date": "...", "index": 100.0, "equity": 12345.67}, ...]


def compute_performance(snapshots: list[EquitySnapshot]) -> PerformanceSummary:
    """Rebase the equity series to 100 at inception and derive the
    headline numbers from it. Sorting defensively by date means callers
    can pass snapshots in any order.
    """
    if not snapshots:
        raise ValueError("compute_performance requires at least one snapshot")

    ordered = sorted(snapshots, key=lambda s: s.as_of)
    base_equity = ordered[0].total_equity
    if base_equity <= 0:
        raise ValueError("first snapshot's total_equity must be > 0 to index off of")

    indexed_series: list[dict] = []
    peak_index = 100.0
    max_drawdown_pct = 0.0
    max_drawdown_date = ordered[0].as_of.isoformat()
    daily_returns: list[float] = []
    prev_index: float | None = None

    for snap in ordered:
        idx = (snap.total_equity / base_equity) * 100.0
        indexed_series.append(
            {
                "date": snap.as_of.isoformat(),
                "index": round(idx, 4),
                "equity": round(snap.total_equity, 2),
            }
        )
        if prev_index is not None and prev_index > 0:
            daily_returns.append((idx / prev_index - 1.0) * 100.0)
        prev_index = idx

        peak_index = max(peak_index, idx)
        drawdown_pct = (idx / peak_index - 1.0) * 100.0
        if drawdown_pct < max_drawdown_pct:
            max_drawdown_pct = drawdown_pct
            max_drawdown_date = snap.as_of.isoformat()

    total_return_pct = (ordered[-1].total_equity / base_equity - 1.0) * 100.0

    return PerformanceSummary(
        inception_date=ordered[0].as_of.isoformat(),
        as_of_date=ordered[-1].as_of.isoformat(),
        days_tracked=len(ordered),
        total_return_pct=round(total_return_pct, 4),
        max_drawdown_pct=round(max_drawdown_pct, 4),
        max_drawdown_date=max_drawdown_date,
        best_day_pct=round(max(daily_returns), 4) if daily_returns else None,
        worst_day_pct=round(min(daily_returns), 4) if daily_returns else None,
        indexed_series=indexed_series,
    )
