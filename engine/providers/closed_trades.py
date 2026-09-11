"""Closed-trades performance provider: the DEFAULT, safe-to-publish metric.

Computes percentage-only performance from a Schwab-style "Transactions"
CSV export, using only CLOSED positions (flat-to-flat, FIFO-matched).

Why this replaced the raw cumulative-net-cash-flow approach
(see realized_pnl.py, kept for history but no longer the default):

  Cumulative net cash flow from trading activity (buys minus sells, signed)
  necessarily looks deeply negative whenever the account holds substantial
  OPEN positions, because the cash spent buying them is counted with no
  offsetting "value received" -- the position is still open, so there is
  no sell proceeds yet. For an account that is actively accumulating
  positions, that produces a large negative number (e.g. "-$60,000") that
  reads as a huge loss to anyone looking at the page, when in reality it
  may just mean a lot of capital is currently invested and unrealized.
  That is precisely the wrong impression to give a hiring manager.

  This provider avoids that failure mode entirely by only scoring
  positions that have fully closed (bought down to zero, or sold down to
  zero) -- i.e. trades with a definite, realized outcome -- and by
  reporting everything as a PERCENTAGE of contributed capital, never a
  raw dollar figure. Open positions are excluded from the return metric
  until they close, and that scope is stated on the page itself.

Privacy: dollar amounts and per-symbol P&L are computed only in-memory to
derive percentages, then discarded. Nothing but percentages, counts, and
dates reaches the returned dict.
"""
from __future__ import annotations

import csv
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


def _parse_money(raw: str) -> Decimal:
    raw = (raw or "").strip().replace("$", "").replace(",", "")
    if not raw:
        return Decimal(0)
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal(0)


def _parse_qty(raw: str) -> Decimal:
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return Decimal(0)
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal(0)


def _parse_date(raw: str) -> date:
    # Schwab sometimes writes "MM/DD/YYYY as of MM/DD/YYYY" for settled
    # transfers; the first (transaction) date is what we use.
    first = raw.split(" as of ")[0].strip()
    return datetime.strptime(first, "%m/%d/%Y").date()


def compute_closed_trades_performance(csv_path: str | Path) -> dict:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found")

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("Date")]

    # Total contributed capital: incoming transfers only.
    contributed = Decimal(0)
    for r in rows:
        if r.get("Action") == "MoneyLink Transfer":
            amt = _parse_money(r.get("Amount", ""))
            if amt > 0:
                contributed += amt

    # Group Buy/Sell rows by symbol, oldest first (exports are newest-first).
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("Action") in ("Buy", "Sell") and (r.get("Symbol") or "").strip():
            by_symbol[r["Symbol"].strip()].append(r)
    for txs in by_symbol.values():
        txs.reverse()

    closed_positions = []  # {open_date, close_date, days, pnl_pct}
    for txs in by_symbol.values():
        lots: deque[list] = deque()  # [qty_remaining, unit_cost]
        pos_qty = Decimal(0)
        open_date: date | None = None
        cost_open = Decimal(0)
        proceeds_open = Decimal(0)

        for tx in txs:
            qty = _parse_qty(tx.get("Quantity", ""))
            amount = _parse_money(tx.get("Amount", ""))
            if qty <= 0:
                continue
            tx_date = _parse_date(tx["Date"])

            if pos_qty == 0:
                open_date = tx_date
                cost_open = Decimal(0)
                proceeds_open = Decimal(0)

            if tx["Action"] == "Buy":
                unit_cost = (-amount) / qty
                lots.append([qty, unit_cost])
                pos_qty += qty
                cost_open += -amount
            else:  # Sell
                remaining = qty
                while remaining > 0 and lots:
                    lot_qty, _ = lots[0]
                    take = min(lot_qty, remaining)
                    lots[0][0] -= take
                    remaining -= take
                    if lots[0][0] <= 0:
                        lots.popleft()
                proceeds_open += amount
                pos_qty -= qty

                if pos_qty <= Decimal("1e-6") and open_date is not None and cost_open > 0:
                    pnl_pct = float((proceeds_open / cost_open - 1) * 100)
                    closed_positions.append(
                        {
                            "open_date": open_date,
                            "close_date": tx_date,
                            "days": (tx_date - open_date).days,
                            "pnl_pct": pnl_pct,
                            "cost": cost_open,
                            "proceeds": proceeds_open,
                        }
                    )
                    pos_qty = Decimal(0)
                    lots.clear()
                    open_date = None
                    cost_open = Decimal(0)
                    proceeds_open = Decimal(0)

    closed_positions.sort(key=lambda p: p["close_date"])
    n = len(closed_positions)
    wins = sum(1 for p in closed_positions if p["pnl_pct"] > 0)
    win_rate_pct = (wins / n * 100) if n else 0.0
    avg_days = (sum(p["days"] for p in closed_positions) / n) if n else 0.0
    avg_gain_pct_per_trade = (
        sum(p["pnl_pct"] for p in closed_positions) / n if n else None
    )

    total_realized_pnl = sum((p["proceeds"] - p["cost"] for p in closed_positions), Decimal(0))
    total_return_pct = float(
        (total_realized_pnl / contributed * 100) if contributed > 0 else Decimal(0)
    )

    # Daily cumulative realized-return series (% of contributed capital),
    # collapsing same-day closes to that day's final value.
    running = Decimal(0)
    by_day: dict[str, float] = {}
    for p in closed_positions:
        running += p["proceeds"] - p["cost"]
        pct = float((running / contributed * 100) if contributed > 0 else Decimal(0))
        by_day[p["close_date"].isoformat()] = round(pct, 4)
    daily_series = [
        {"date": d, "cumulative_return_pct": v} for d, v in sorted(by_day.items())
    ]

    return {
        "as_of": closed_positions[-1]["close_date"].isoformat() if closed_positions else None,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics": {
            "total_return_pct": round(total_return_pct, 4),
            "closed_trades": n,
            "win_rate_pct": round(win_rate_pct, 2),
            "avg_holding_days": round(avg_days, 2),
            "avg_gain_pct_per_trade": (
                round(avg_gain_pct_per_trade, 4) if avg_gain_pct_per_trade is not None else None
            ),
            "distinct_symbols_traded": len(by_symbol),
        },
        "daily_cumulative_return_pct": daily_series,
        "methodology_note": (
            "Realized-only performance from closed (flat-to-flat) positions, "
            "FIFO-matched. Total return % is realized profit from closed trades "
            "divided by total capital contributed to the account. Excludes open "
            "positions (until they close), dividends/interest, taxes, and "
            "account-level financing costs. Percentages only -- no dollar "
            "amounts, account numbers, or symbol-level detail are published."
        ),
    }
