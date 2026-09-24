import json
from pathlib import Path

from scripts import update_performance


def test_manual_entry_output_never_includes_raw_equity_amounts(tmp_path):
    csv_path = tmp_path / "daily_equity.csv"
    csv_path.write_text(
        "date,total_equity,cash\n"
        "2026-09-01,100000.00,5000.00\n"
        "2026-09-02,101234.56,5234.56\n",
        encoding="utf-8",
    )

    output = update_performance._build_total_equity_output(csv_path)
    raw = json.dumps(output, sort_keys=True)

    assert output["series_type"] == "total_account_equity_indexed"
    assert output["points"] == [
        {"date": "2026-09-01", "index": 100.0},
        {"date": "2026-09-02", "index": 101.2346},
    ]
    assert all("equity" not in point for point in output["points"])
    assert "100000" not in raw
    assert "101234.56" not in raw
    assert "5000" not in raw
    assert "5234.56" not in raw


def test_manual_entry_main_writes_percentage_only_json(tmp_path, monkeypatch):
    csv_path = tmp_path / "daily_equity.csv"
    csv_path.write_text(
        "date,total_equity,cash\n"
        '2026-09-01,"$100,000.00","$5,000.00"\n'
        '2026-09-02,"$102,000.00","$5,500.00"\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "performance.json"
    monkeypatch.setattr(update_performance, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "update_performance.py",
            "--provider",
            "manual_entry",
            "--csv",
            str(csv_path),
        ],
    )

    assert update_performance.main() == 0
    raw = output_path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["total_return_pct"] == 2.0
    assert data["points"][-1] == {"date": "2026-09-02", "index": 102.0}
    assert all("equity" not in point for point in data["points"])
    assert "100000" not in raw
    assert "102000" not in raw
    assert "5500" not in raw
