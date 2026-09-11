from datetime import date

import pytest

from engine.metrics import compute_performance
from engine.schemas import EquitySnapshot


def _snap(day: str, equity: float) -> EquitySnapshot:
    y, m, d = (int(x) for x in day.split("-"))
    return EquitySnapshot(as_of=date(y, m, d), total_equity=equity, cash=0.0, source="manual_entry")


def test_compute_performance_requires_snapshots():
    with pytest.raises(ValueError, match="at least one snapshot"):
        compute_performance([])


def test_compute_performance_rejects_zero_base_equity():
    with pytest.raises(ValueError, match="must be > 0"):
        compute_performance([EquitySnapshot(date(2026, 1, 1), 0.0, 0.0, "manual_entry")])


def test_flat_series_has_zero_return_and_drawdown():
    snaps = [_snap("2026-01-01", 100_000), _snap("2026-01-02", 100_000)]
    summary = compute_performance(snaps)
    assert summary.total_return_pct == 0.0
    assert summary.max_drawdown_pct == 0.0
    assert summary.days_tracked == 2
    assert summary.indexed_series[0]["index"] == 100.0
    assert summary.indexed_series[1]["index"] == 100.0


def test_monotonic_gain_has_correct_total_return():
    snaps = [_snap("2026-01-01", 100_000), _snap("2026-01-02", 110_000)]
    summary = compute_performance(snaps)
    assert summary.total_return_pct == pytest.approx(10.0)
    assert summary.max_drawdown_pct == 0.0
    assert summary.best_day_pct == pytest.approx(10.0)
    assert summary.worst_day_pct == pytest.approx(10.0)


def test_drawdown_is_measured_from_running_peak_not_inception():
    # 100 -> 120 (new peak) -> 90 (drop from peak, not from inception)
    snaps = [_snap("2026-01-01", 100_000), _snap("2026-01-02", 120_000), _snap("2026-01-03", 90_000)]
    summary = compute_performance(snaps)
    # peak index = 120, trough index = 90 -> (90/120 - 1) * 100 = -25%
    assert summary.max_drawdown_pct == pytest.approx(-25.0)
    assert summary.max_drawdown_date == "2026-01-03"
    # total return is from inception (100k) to final (90k) = -10%, NOT -25%
    assert summary.total_return_pct == pytest.approx(-10.0)


def test_out_of_order_input_is_sorted_before_computing():
    snaps = [_snap("2026-01-03", 90_000), _snap("2026-01-01", 100_000), _snap("2026-01-02", 120_000)]
    summary = compute_performance(snaps)
    assert summary.inception_date == "2026-01-01"
    assert summary.as_of_date == "2026-01-03"
    assert [p["date"] for p in summary.indexed_series] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]


def test_equity_snapshot_rejects_negative_values():
    with pytest.raises(ValueError):
        EquitySnapshot(date(2026, 1, 1), -1.0, 0.0, "manual_entry")
    with pytest.raises(ValueError):
        EquitySnapshot(date(2026, 1, 1), 100.0, -1.0, "manual_entry")
