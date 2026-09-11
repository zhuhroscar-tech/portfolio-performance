"""Manual daily-equity provider: reads a simple, hand- or
script-maintained CSV of `date,total_equity` rows.

Why this exists: Schwab's Trader API requires either a company
integration agreement or a refresh token that expires every 7 days and
needs an interactive browser login to renew (see
engine/providers/schwab_api.py for the full explanation and TODOs).
Neither is set up yet. This provider is the immediately-usable path to
a REAL total-equity curve (not just realized trading P&L): the user (or
later, a logged-in scraper/API job) appends one row per day with that
day's actual total account value, and the site's numbers are correct
mark-to-market performance from day one.

Expected CSV format (data/daily_equity.csv, NOT committed to git --
see .gitignore):

    date,total_equity,cash
    2026-09-01,214830.55,18250.10
    2026-09-02,216110.02,18250.10

`cash` is optional; if omitted it is recorded as 0.0 (unknown), which
only affects diagnostics, not the performance math (that uses
total_equity only).
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ..schemas import EquitySnapshot


def fetch_snapshot_series(csv_path: str | Path) -> list[EquitySnapshot]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Create it with a header row "
            "'date,total_equity,cash' and one row per day you record "
            "your account's total value."
        )

    snapshots: list[EquitySnapshot] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"date", "total_equity"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{csv_path} must have at least columns: date,total_equity "
                f"(got {reader.fieldnames})"
            )
        for row in reader:
            raw_date = (row.get("date") or "").strip()
            raw_equity = (row.get("total_equity") or "").strip()
            if not raw_date or not raw_equity:
                continue
            day = datetime.strptime(raw_date, "%Y-%m-%d").date()
            equity = float(raw_equity.replace("$", "").replace(",", ""))
            raw_cash = (row.get("cash") or "").strip()
            cash = float(raw_cash.replace("$", "").replace(",", "")) if raw_cash else 0.0
            snapshots.append(
                EquitySnapshot(as_of=day, total_equity=equity, cash=cash, source="manual_entry")
            )

    if not snapshots:
        raise ValueError(f"{csv_path} contained a header but zero data rows")

    return sorted(snapshots, key=lambda s: s.as_of)
