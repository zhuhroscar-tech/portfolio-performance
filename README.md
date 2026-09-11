# Portfolio Performance

A small, privacy-first pipeline that turns a brokerage transaction export
into a public performance page — the kind of thing you can link from a
resume, GitHub profile, or job application without exposing account details.

**Live page:** https://zhuhroscar-tech.github.io/portfolio-performance/

## Demo

Watch the [project demonstration](docs/demo.mp4) to see the percentage-only
pipeline and public page workflow without exposing account or dollar data.

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

## Why it isn't fully automated *yet*

The daily-update pipeline is **fully built and tested** — see
`engine/providers/schwab_api.py` (OAuth client + account fetch, 7 passing
tests against mocked HTTP), `scripts/daily_schwab_update.py` (the job that
runs daily), and `.github/workflows/daily-update.yml` (the schedule).

What's left is **one credential step only the account owner can do**:

1. Register an Individual Developer app at
   [developer.schwab.com](https://developer.schwab.com/), requesting the
   "Trader API - Individual" product (read-only account access is enough).
2. Run `python3 scripts/schwab_login.py` once — it walks you through a
   ~30-second interactive Schwab login in your own browser and prints a
   refresh token.
3. Add `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, and `SCHWAB_REFRESH_TOKEN` as
   [GitHub Actions repository secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions).
4. The `daily-update.yml` workflow picks them up automatically on its next
   scheduled run (13:30 UTC daily) — no code changes needed.

**The catch:** Schwab's refresh token expires every **7 days** and renewing
it requires that same ~30-second interactive login — this is a hard
platform limit, not a bug. So "fully automated forever" currently means
"fully automated, with a 30-second manual check-in roughly weekly." The
workflow is written to fail loudly and specifically (not silently) when
the refresh token expires, so you'll know exactly when to re-run
`schwab_login.py`.

A brokerage-aggregator service (e.g. [SnapTrade](https://snaptrade.com/))
would remove even that weekly step by managing token refresh server-side.
That's a possible future provider module alongside `schwab_api.py`, not
implemented yet.

Until Schwab credentials are configured, `scripts/update_performance.py`
(the `closed_trades` provider) is the manual path: run it against a fresh
CSV export whenever you want to refresh the published numbers.

## License

MIT — see [LICENSE](LICENSE).
