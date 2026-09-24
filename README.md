# Portfolio Performance

[![English](https://img.shields.io/badge/English-555555?style=flat)](README.md) [![简体中文](https://img.shields.io/badge/简体中文-555555?style=flat)](README.zh-CN.md)

A static performance page backed by a Python pipeline that converts private brokerage exports into percentage-based summaries. The default path reports realized results from closed positions without publishing account balances, account identifiers, or symbol-level profit/loss.

## Demo

**Visitors:** [open the public dashboard](https://zhuhroscar-tech.github.io/portfolio-performance/). No installation, brokerage login, or API key is needed. Read the methodology alongside the figures; this is not investment advice or an audited account statement.

Watch the [project demonstration](docs/demo.mp4) to see the percentage-only pipeline and public page workflow without exposing account or dollar data.

## What the default page shows

- Realized return as a percentage of contributed capital.
- Closed-trade count, win rate, average holding days, and average trade gain.
- A cumulative realized-return chart, rendered from `docs/data/performance.json`.

The frontend is plain HTML and SVG in `docs/index.html`; there is no application server, database, or frontend build step.

## Developer quickstart

Use Python 3.12 (the CI version). The default pipeline uses the standard library; tests require pytest.

```bash
git clone https://github.com/zhuhroscar-tech/portfolio-performance.git
cd portfolio-performance
python3 -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8000`. To update **your own fork**, stop the preview and run:

```bash
python3 scripts/update_performance.py --provider closed_trades --csv /private/path/transactions.csv
```

Use a Schwab-style Transactions export with Date, Action, Symbol, Quantity, Price, Fees & Comm, and Amount columns. Inspect the generated JSON before committing **only** `docs/data/performance.json`. Keep CSV exports, raw history, credentials, and account details private; `.gitignore` is a safeguard, not a privacy audit.

## Methodology and limits

Closed trades are flat-to-flat round trips with FIFO lot matching. Same-day ordering is inferred by reversing the export's newest-first rows, not by broker-confirmed execution timestamps. Contributed capital uses positive `MoneyLink Transfer` entries; incomplete exports can distort the denominator.

Open positions, dividends, interest, taxes, and account-level financing costs are excluded. This is neither mark-to-market account performance nor a time-weighted or annualized return. Public output contains percentages, counts, durations, dates, and explanatory metadata—not monetary amounts or account numbers.

## Optional developer paths

`manual_entry` and the Schwab API path produce a **different indexed-equity schema**, not the default closed-trade metrics. They are not drop-in replacements for this page. The existing daily workflow skips updates when credentials are absent; it does not establish that live brokerage access is configured.

Before using automation, review [developer notes](docs/REFERENCE.md) for schema compatibility, private-history persistence, and credential/logging risks. Visitors should not run this pipeline or provide credentials.

## Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

[Release history](CHANGELOG.md) · [MIT license](LICENSE).
