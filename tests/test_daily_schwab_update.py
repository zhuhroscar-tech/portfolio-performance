"""Tests for scripts/daily_schwab_update.py's core logic: history
persistence and the public-output shape. Network calls (Schwab OAuth
and account fetch) are exercised separately in test_schwab_api.py; this
file focuses on what the daily job does with the data once fetched,
especially the privacy guarantee that dollar amounts never reach the
committed docs/data/performance.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "daily_schwab_update.py"

spec = importlib.util.spec_from_file_location("daily_schwab_update", SCRIPT_PATH)
daily_schwab_update = importlib.util.module_from_spec(spec)
sys.modules["daily_schwab_update"] = daily_schwab_update
spec.loader.exec_module(daily_schwab_update)

from engine.schemas import EquitySnapshot  # noqa: E402


def test_history_round_trips_through_json(tmp_path, monkeypatch):
    history_path = tmp_path / "equity_history.json"
    monkeypatch.setattr(daily_schwab_update, "HISTORY_PATH", history_path)

    snapshots = [
        EquitySnapshot(as_of=date(2026, 9, 1), total_equity=100000.0, cash=5000.0, source="schwab"),
        EquitySnapshot(as_of=date(2026, 9, 2), total_equity=101000.0, cash=4500.0, source="schwab"),
    ]
    daily_schwab_update._save_history(snapshots)
    loaded = daily_schwab_update._load_history()

    assert loaded == snapshots


def test_load_history_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_schwab_update, "HISTORY_PATH", tmp_path / "does_not_exist.json")
    assert daily_schwab_update._load_history() == []


def test_main_output_never_contains_dollar_equity_values(tmp_path, monkeypatch):
    """Regression test for the exact privacy guarantee this whole project
    depends on: the daily job's PUBLIC output must never contain a raw
    dollar total_equity value, even though its PRIVATE history file does.
    """
    history_path = tmp_path / "equity_history.json"
    output_path = tmp_path / "performance.json"
    monkeypatch.setattr(daily_schwab_update, "HISTORY_PATH", history_path)
    monkeypatch.setattr(daily_schwab_update, "OUTPUT_PATH", output_path)

    monkeypatch.setenv("SCHWAB_APP_KEY", "KEY")
    monkeypatch.setenv("SCHWAB_APP_SECRET", "SECRET")
    monkeypatch.setenv("SCHWAB_REFRESH_TOKEN", "REFRESH")

    def fake_refresh_access_token(app_key, app_secret, refresh_token):
        return {"access_token": "ACCESS", "refresh_token": "REFRESH"}

    def fake_fetch_snapshot(access_token):
        # A distinctive, greppable dollar figure that must NEVER appear
        # in the committed public output.
        return EquitySnapshot(
            as_of=date(2026, 9, 12), total_equity=123456.78, cash=9999.99, source="schwab"
        )

    monkeypatch.setattr(daily_schwab_update.schwab_api, "refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr(daily_schwab_update.schwab_api, "fetch_snapshot", fake_fetch_snapshot)

    rc = daily_schwab_update.main()
    assert rc == 0

    public_raw = output_path.read_text()
    assert "123456.78" not in public_raw
    assert "9999.99" not in public_raw

    public = json.loads(public_raw)
    assert public["series_type"] == "total_account_equity_indexed"
    assert public["points"][0]["index"] == 100.0
    assert set(public["points"][0].keys()) == {"date", "index"}

    # The private history file DOES contain the real dollar figure --
    # that file is git-ignored and never committed.
    private_raw = history_path.read_text()
    assert "123456.78" in private_raw
