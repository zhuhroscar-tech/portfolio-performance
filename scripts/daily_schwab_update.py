#!/usr/bin/env python3
"""Daily automated update: fetch today's account snapshot from Schwab,
append it to the tracked equity history, recompute performance.json.

Designed to run unattended in GitHub Actions once SCHWAB_APP_KEY,
SCHWAB_APP_SECRET, and SCHWAB_REFRESH_TOKEN are set as repository
secrets (see engine/providers/schwab_api.py's module docstring and
scripts/schwab_login.py for how to obtain them).

Privacy: history/equity_history.json stores raw dollar total_equity
values used to compute the index -- it must NEVER be committed (see
.gitignore: data/*.json is excluded). Only the derived, indexed,
percentage-based docs/data/performance.json is committed and published.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.metrics import compute_performance  # noqa: E402
from engine.providers import schwab_api  # noqa: E402
from engine.schemas import EquitySnapshot  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = REPO_ROOT / "data" / "equity_history.json"  # git-ignored, private
OUTPUT_PATH = REPO_ROOT / "docs" / "data" / "performance.json"  # committed, public


def _load_history() -> list[EquitySnapshot]:
    if not HISTORY_PATH.exists():
        return []
    raw = json.loads(HISTORY_PATH.read_text())
    return [
        EquitySnapshot(
            as_of=datetime.strptime(r["as_of"], "%Y-%m-%d").date(),
            total_equity=r["total_equity"],
            cash=r["cash"],
            source=r["source"],
        )
        for r in raw
    ]


def _save_history(snapshots: list[EquitySnapshot]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "as_of": s.as_of.isoformat(),
            "total_equity": s.total_equity,
            "cash": s.cash,
            "source": s.source,
        }
        for s in snapshots
    ]
    HISTORY_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    import os

    app_key = os.environ.get("SCHWAB_APP_KEY", "").strip()
    app_secret = os.environ.get("SCHWAB_APP_SECRET", "").strip()
    refresh_token = os.environ.get("SCHWAB_REFRESH_TOKEN", "").strip()

    missing = [
        name
        for name, val in [
            ("SCHWAB_APP_KEY", app_key),
            ("SCHWAB_APP_SECRET", app_secret),
            ("SCHWAB_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        print(
            "error: missing required environment variable(s): " + ", ".join(missing) + "\n"
            "This script is meant to run with Schwab credentials set as environment "
            "variables (GitHub Actions repository secrets in CI). See "
            "engine/providers/schwab_api.py and scripts/schwab_login.py to obtain them.",
            file=sys.stderr,
        )
        return 1

    try:
        tokens = schwab_api.refresh_access_token(app_key, app_secret, refresh_token)
    except RuntimeError as exc:
        print(f"error refreshing Schwab access token: {exc}", file=sys.stderr)
        print(
            "If this is an expired/invalid refresh_token (7-day limit), re-run "
            "scripts/schwab_login.py and update the SCHWAB_REFRESH_TOKEN secret.",
            file=sys.stderr,
        )
        return 1

    access_token = tokens.get("access_token")
    if not access_token:
        print(f"error: no access_token in refresh response: {tokens}", file=sys.stderr)
        return 1

    new_refresh_token = tokens.get("refresh_token", refresh_token)
    if new_refresh_token != refresh_token:
        # GitHub Actions can't update its own secrets mid-run; surface this
        # clearly so the workflow (or the user) knows to rotate it.
        print(
            "NOTICE: Schwab issued a new refresh_token. Update the "
            "SCHWAB_REFRESH_TOKEN repository secret to:\n"
            f"  {new_refresh_token}",
            file=sys.stderr,
        )

    try:
        snapshot = schwab_api.fetch_snapshot(access_token)
    except RuntimeError as exc:
        print(f"error fetching account snapshot: {exc}", file=sys.stderr)
        return 1

    history = _load_history()
    history = [s for s in history if s.as_of != snapshot.as_of]  # replace same-day entry
    history.append(snapshot)
    history.sort(key=lambda s: s.as_of)
    _save_history(history)

    summary = compute_performance(history)
    output = {
        "series_type": "total_account_equity_indexed",
        "methodology": (
            "Total account equity (cash + market value of all positions), "
            "indexed to 100 at inception. This IS mark-to-market portfolio "
            "performance, fetched daily and automatically from the Schwab "
            "Trader API. total_return_pct is the full-period return; "
            "max_drawdown_pct is the largest peak-to-trough decline in the "
            "indexed series. Only the index and percentage figures are "
            "published -- raw dollar equity values are never committed."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inception_date": summary.inception_date,
        "as_of_date": summary.as_of_date,
        "days_tracked": summary.days_tracked,
        "total_return_pct": summary.total_return_pct,
        "max_drawdown_pct": summary.max_drawdown_pct,
        "max_drawdown_date": summary.max_drawdown_date,
        "best_day_pct": summary.best_day_pct,
        "worst_day_pct": summary.worst_day_pct,
        "points": [{"date": p["date"], "index": p["index"]} for p in summary.indexed_series],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {OUTPUT_PATH}: {summary.days_tracked} days tracked, "
          f"total_return_pct={summary.total_return_pct}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
