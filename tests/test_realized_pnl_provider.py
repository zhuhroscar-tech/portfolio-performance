from pathlib import Path

import pytest

from engine.providers.realized_pnl import fetch_realized_pnl_points

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transactions.csv"


def test_excludes_moneylink_transfers():
    points = fetch_realized_pnl_points(FIXTURE)
    dates = [p["date"] for p in points]
    # 08/18 (the transfer-only day) must not appear at all once excluded,
    # since transfers were the ONLY row on that date.
    assert "2026-08-17" not in dates  # settlement date of the "as of" transfer
    assert "2026-08-18" not in dates


def test_cumulative_pnl_matches_hand_computed_value():
    points = fetch_realized_pnl_points(FIXTURE)
    by_date = {p["date"]: p["cumulative_pnl"] for p in points}
    # 09/03: -2000.00 (buy) + 4117.13 (sell) - 0.73 (tax adj) = 2116.40
    assert by_date["2026-09-03"] == pytest.approx(2116.40)
    # 09/08 cumulative: 2116.40 + 30379.32 = 32495.72
    assert by_date["2026-09-08"] == pytest.approx(32495.72)


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch_realized_pnl_points(tmp_path / "does_not_exist.csv")


def test_transfer_only_csv_raises_valueerror(tmp_path):
    p = tmp_path / "only_transfers.csv"
    p.write_text(
        'Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount\n'
        '"09/01/2026","MoneyLink Transfer","","Tfr BANK","","","","$100.00"\n'
    )
    with pytest.raises(ValueError, match="No usable"):
        fetch_realized_pnl_points(p)
