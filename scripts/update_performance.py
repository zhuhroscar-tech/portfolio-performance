"""Compute performance.json from whichever provider is configured.

Usage:
    python scripts/update_performance.py --provider closed_trades --csv path/to/transactions.csv
    python scripts/update_performance.py --provider manual_entry --csv data/daily_equity.csv

Writes docs/data/performance.json (docs/ is the GitHub Pages source
directory). "closed_trades" is the default and recommended provider: it
publishes percentage-only, realized performance from closed positions,
safe to put on a resume without exposing account size (see
engine/providers/closed_trades.py for the full rationale).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.metrics import compute_performance  # noqa: E402
from engine.providers import closed_trades, manual_entry  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "data" / "performance.json"


def _build_closed_trades_output(csv_path: Path) -> dict:
    return closed_trades.compute_closed_trades_performance(csv_path)


def _public_indexed_points(points: list[dict]) -> list[dict]:
    """Drop private raw balances from indexed-equity chart points."""
    return [{"date": point["date"], "index": point["index"]} for point in points]


def _build_total_equity_output(csv_path: Path) -> dict:
    snapshots = manual_entry.fetch_snapshot_series(csv_path)
    summary = compute_performance(snapshots)
    return {
        "series_type": "total_account_equity_indexed",
        "methodology": (
            "Total account equity (cash + market value of all positions), "
            "indexed to 100 at inception. This IS mark-to-market portfolio "
            "performance. total_return_pct is the full-period return; "
            "max_drawdown_pct is the largest peak-to-trough decline in the "
            "indexed series. Only the index and percentage figures are "
            "published -- raw dollar equity values are never committed."
        ),
        "inception_date": summary.inception_date,
        "as_of_date": summary.as_of_date,
        "days_tracked": summary.days_tracked,
        "total_return_pct": summary.total_return_pct,
        "max_drawdown_pct": summary.max_drawdown_pct,
        "max_drawdown_date": summary.max_drawdown_date,
        "best_day_pct": summary.best_day_pct,
        "worst_day_pct": summary.worst_day_pct,
        "points": _public_indexed_points(summary.indexed_series),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default="closed_trades",
        choices=["closed_trades", "manual_entry"],
        help="Which data source to compute performance.json from (default: closed_trades).",
    )
    parser.add_argument("--csv", required=True, help="Path to the input CSV file.")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"error: input CSV not found: {csv_path}", file=sys.stderr)
        return 1

    try:
        if args.provider == "closed_trades":
            output = _build_closed_trades_output(csv_path)
        else:
            output = _build_total_equity_output(csv_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    n_points = len(output.get("daily_cumulative_return_pct") or output.get("points") or [])
    print(f"wrote {OUTPUT_PATH} ({args.provider}, {n_points} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
