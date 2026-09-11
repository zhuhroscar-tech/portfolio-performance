"""DEPRECATED as the site's default provider — kept only for its test
coverage and as a documented cautionary example. See
engine/providers/closed_trades.py for the current default.

Realized trading P&L provider: derives a cumulative REALIZED P&L
series from a Schwab-style "Transactions" CSV export.

IMPORTANT — why this is no longer the default:

  This computes cumulative net cash flow from trading activity only
  (buys, sells, dividends, fees, interest), excluding "MoneyLink
  Transfer" rows. That produces a materially misleading number whenever
  the account holds substantial OPEN positions: money spent on a stock
  still held shows up as a cash outflow with no offsetting value, so
  the cumulative figure can look like a large loss (e.g. deeply
  negative) even when the account is simply invested and doing fine.
  That is the wrong number to put in front of a hiring manager.

  engine/providers/closed_trades.py fixes this by only scoring
  positions that have fully closed (a definite, realized outcome), and
  by reporting everything as a percentage of contributed capital rather
  than a raw dollar cash-flow figure. Use that provider by default;
  this module is retained for its tests and as a documented pitfall.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

_EXCLUDED_ACTIONS = {"moneylink transfer"}


def _parse_date(raw: str) -> date:
    # Schwab sometimes writes "MM/DD/YYYY as of MM/DD/YYYY" for settled
    # transfers; the settlement (first) date is what we bucket by.
    first = raw.split(" as of ")[0].strip()
    return datetime.strptime(first, "%m/%d/%Y").date()


def _parse_amount(raw: str) -> float:
    raw = (raw or "").strip()
    if not raw:
        return 0.0
    negative = raw.startswith("-")
    raw = raw.lstrip("-").replace("$", "").replace(",", "")
    if not raw:
        return 0.0
    value = float(raw)
    return -value if negative else value


def fetch_realized_pnl_points(csv_path: str | Path) -> list[dict]:
    """Read a Schwab transactions CSV and return one
    {"date": "YYYY-MM-DD", "cumulative_pnl": float} point per
    day-with-activity, cumulative realized trading P&L with deposits
    and withdrawals excluded. Values are signed (can be negative) on
    purpose -- unlike EquitySnapshot, which forbids negative values
    because it represents actual account equity.
    """
    csv_path = Path(csv_path)
    daily_net: dict[date, float] = defaultdict(float)

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = (row.get("Action") or "").strip().lower()
            if action in _EXCLUDED_ACTIONS:
                continue
            raw_date = (row.get("Date") or "").strip()
            raw_amount = (row.get("Amount") or "").strip()
            if not raw_date or not raw_amount:
                continue
            try:
                day = _parse_date(raw_date)
            except ValueError:
                continue  # skip malformed/footer rows defensively
            daily_net[day] += _parse_amount(raw_amount)

    if not daily_net:
        raise ValueError(f"No usable non-transfer transaction rows found in {csv_path}")

    cumulative = 0.0
    points: list[dict] = []
    for day in sorted(daily_net):
        cumulative += daily_net[day]
        points.append({"date": day.isoformat(), "cumulative_pnl": round(cumulative, 2)})
    return points
