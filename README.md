# Portfolio Performance

A small, privacy-first pipeline that turns a brokerage transaction export
into a public performance page — the kind of thing you can link from a
resume, GitHub profile, or job application without exposing account details.

**Live page:** https://zhuhroscar-tech.github.io/portfolio-performance/

## What it shows

- Total realized return (% of contributed capital)
- Win rate across closed trades
- Number of closed trades
- Average holding time
- Average gain per trade
- A cumulative realized-return chart over time

**What it never shows:** dollar amounts, account numbers, brokerage account
identifiers, or symbol-level profit/loss. Everything published is a
percentage, a count, or a date. See [Privacy](#privacy) below.

## How it works

```
brokerage CSV export (kept local, never committed)
        │
        ▼
engine/providers/closed_trades.py ── FIFO-matches closed positions,
        │                             computes percentage-only metrics
        ▼
scripts/update_performance.py    ── writes the JSON
        │
        ▼
data/performance.json             ── the only file with real numbers
        │
        ▼
docs/index.html                  ── static page, fetches the JSON,
                                     renders stats + chart client-side
        │
        ▼
GitHub Pages (docs/ folder)      ── public URL
```

No server, no database, no framework. `docs/index.html` is a single static
file that fetches `data/performance.json` and draws everything with plain
SVG — it works on GitHub Pages with zero build step.

## Updating the data

Today, this is a **manual, on-demand** step (see [Why it isn't fully
automated yet](#why-it-isnt-fully-automated-yet)):

```bash
python3 scripts/update_performance.py --provider closed_trades --csv /path/to/your/export.csv
git add docs/data/performance.json
git commit -m "chore: refresh performance data"
git push
```

The script reads a Schwab-style "Transactions" CSV export (Date, Action,
Symbol, Quantity, Price, Fees & Comm, Amount columns) and never writes
anything except `docs/data/performance.json`. The source CSV itself is
git-ignored by default — never commit it.

## Methodology

- A **closed trade** is one symbol's full round trip from zero shares back
  to zero shares. Lots are matched **FIFO** (first bought, first sold).
- Same-day fill order is inferred by reversing the export's newest-first row
  order, since the export does not include execution timestamps. This is a
  reconstruction, not broker-confirmed tax-lot data.
- **Total return %** = realized profit from all closed trades ÷ total
  capital contributed to the account (sum of incoming transfers).
- **Win rate** = closed trades with positive P&L ÷ total closed trades.
- Dividends, interest, and tax adjustments are excluded from these metrics —
  they're real income, just not a trading decision.
- **Open positions are excluded** from realized return until they close.
  This is a realized-performance snapshot, not a mark-to-market account
  value, and not a time-weighted or annualized return.

## Privacy

`scripts/compute_performance.py` is written so that dollar amounts and
symbol-level detail structurally cannot reach `docs/data/performance.json` —
the per-trade dollar P&L is computed in-memory to derive a percentage, then
discarded. If you fork this for your own use, keep it that way: audit any
change to `engine/providers/closed_trades.py` for a `Decimal`/dollar value
leaking into the output dict before committing.

## Why it isn't fully automated yet

The eventual goal is a **daily automatic** update with zero manual steps.
The blocker is brokerage OAuth, not this code:

- Schwab's Trader API issues a refresh token that **expires every 7 days**,
  and renewing it requires an interactive browser login — it cannot be
  scripted end-to-end today.
- A brokerage-aggregator service (e.g. SnapTrade) handles that token
  refresh problem server-side and would let this run as an unattended daily
  job. That requires signing up for and connecting through such a service,
  which is an account-linking step only the account owner can do.

Until one of those is wired in, this repo's `scripts/update_performance.py`
is run manually against a fresh export whenever you want to refresh the
published numbers. The output format and site are already built for the
automated version — swapping the CSV read for an API pull is a small,
contained change (adding a `fetch_transactions_from_api()` step and a new
provider module alongside `engine/providers/closed_trades.py`), not a
redesign.

## License

MIT — see [LICENSE](LICENSE).
