import csv
from decimal import Decimal
from pathlib import Path

import pytest

from engine.providers.closed_trades import compute_closed_trades_performance

HEADER = ["Date", "Action", "Symbol", "Description", "Quantity", "Price", "Fees & Comm", "Amount"]


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)


def test_simple_round_trip_profit(tmp_path):
    # Newest-first order, matching real Schwab exports: one deposit, one win.
    rows = [
        ["09/05/2026", "Sell", "TEST", "TEST CORP", "10", "$110.00", "$0.01", "$1099.99"],
        ["09/01/2026", "Buy", "TEST", "TEST CORP", "10", "$100.00", "", "-$1000.00"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$1000.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    data = compute_closed_trades_performance(csv_path)

    assert data["metrics"]["closed_trades"] == 1
    assert data["metrics"]["win_rate_pct"] == 100.0
    assert data["metrics"]["avg_holding_days"] == 4.0
    # profit = 1099.99 - 1000.00 = 99.99; contributed = 1000.00 -> 9.999%
    assert abs(data["metrics"]["total_return_pct"] - 9.999) < 0.001
    assert data["as_of"] == "2026-09-05"


def test_no_dollar_amounts_leak_into_output(tmp_path):
    rows = [
        ["09/05/2026", "Sell", "TEST", "TEST CORP", "10", "$110.00", "$0.01", "$1099.99"],
        ["09/01/2026", "Buy", "TEST", "TEST CORP", "10", "$100.00", "", "-$1000.00"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$1000.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    compute_closed_trades_performance(csv_path)
    import json
    raw = json.dumps(compute_closed_trades_performance(csv_path))

    assert "$" not in raw
    assert "1000.00" not in raw
    assert "1099.99" not in raw
    assert "TEST" not in raw  # no symbol-level detail


def test_losing_trade_lowers_win_rate(tmp_path):
    rows = [
        ["09/05/2026", "Sell", "LOSS", "LOSS CORP", "10", "$90.00", "", "$900.00"],
        ["09/01/2026", "Buy", "LOSS", "LOSS CORP", "10", "$100.00", "", "-$1000.00"],
        ["09/10/2026", "Sell", "WIN", "WIN CORP", "10", "$110.00", "", "$1100.00"],
        ["09/06/2026", "Buy", "WIN", "WIN CORP", "10", "$100.00", "", "-$1000.00"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$2000.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    data = compute_closed_trades_performance(csv_path)

    assert data["metrics"]["closed_trades"] == 2
    assert data["metrics"]["win_rate_pct"] == 50.0


def test_open_position_excluded_from_closed_trades(tmp_path):
    rows = [
        ["09/01/2026", "Buy", "OPEN", "OPEN CORP", "5", "$50.00", "", "-$250.00"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$500.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    data = compute_closed_trades_performance(csv_path)

    assert data["metrics"]["closed_trades"] == 0
    assert data["as_of"] is None
    # Critically: an open position must NOT drag the return negative.
    assert data["metrics"]["total_return_pct"] == 0.0


def test_dividends_and_transfers_do_not_count_as_trades(tmp_path):
    rows = [
        ["09/05/2026", "Cash Dividend", "DIV", "DIVIDEND CORP", "", "", "", "$5.00"],
        ["09/01/2026", "NRA Tax Adj", "DIV", "DIVIDEND CORP", "", "", "", "-$0.50"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$1000.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    data = compute_closed_trades_performance(csv_path)

    assert data["metrics"]["closed_trades"] == 0
    assert data["metrics"]["distinct_symbols_traded"] == 0


def test_open_position_does_not_produce_large_negative_return(tmp_path):
    """Regression test for the exact failure mode that made the old
    realized_pnl.py provider unsafe to publish: heavy buying of a still-open
    position must not read as a large loss.
    """
    rows = [
        ["09/01/2026", "Buy", "HOLD", "HOLD CORP", "500", "$100.00", "", "-$50000.00"],
        ["08/01/2026", "MoneyLink Transfer", "", "Tfr BANK", "", "", "", "$50000.00"],
    ]
    csv_path = tmp_path / "in.csv"
    _write_csv(csv_path, rows)
    data = compute_closed_trades_performance(csv_path)

    assert data["metrics"]["closed_trades"] == 0
    assert data["metrics"]["total_return_pct"] == 0.0
    assert data["daily_cumulative_return_pct"] == []


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        compute_closed_trades_performance(tmp_path / "does_not_exist.csv")
