# Backtesting

Above are the backtesting folders including python files, json files, csv files and png files.

## Setup

Scripts that call authenticated services read their credentials from environment
variables, so no secrets are stored in this repository.

```bash
pip install requests pandas numpy matplotlib yfinance tqdm beautifulsoup4 python-dotenv
cp .env.example .env     # then fill in your own credentials
```

`.env` is git-ignored. Without `python-dotenv`, export the same variables in your
shell instead. Each script exits with a message naming the variable it needs if one
is missing.

| Folder | Variables required |
|---|---|
| `MSTR,COIN,RIOT,SQ,MARA/` | none (public sites + Yahoo Finance) |
| `QuiverStrategy/` | none (Yahoo Finance only) |
| `Seeking Alpha/` | `SEEKINGALPHA_EMAIL`, `SEEKINGALPHA_PASSWORD` for the pick backtest |
| `Whale Wisdom/` | `WHALEWISDOM_SHARED_ACCESS_KEY`, `WHALEWISDOM_SECRET_ACCESS_KEY` |

## Folders

| Folder | What it does |
|---|---|
| `MSTR,COIN,RIOT,SQ,MARA/` | BTC-treasury equity valuation — BTC Ratio, NAV Premium, BTC per Share for five listed proxies, with 7/30/90-day charts |
| `QuiverStrategy/` | Reusable risk-metrics library — returns, CAGR, max drawdown, beta, alpha, Sharpe |
| `Seeking Alpha/` | Pick-portfolio backtest against seven benchmark assets; plus a trading-volume screen |
| `Whale Wisdom/` | 13F institutional-holdings z-score mean-reversion backtest (2015–2024) |

## Known limitation: annualisation in `Whale Wisdom/`

The WhaleWisdom rows are **quarterly** 13F filings, but both scripts annualise
returns using 252 trading days, as the original revision did. That treats quarterly
observations as daily ones and inflates CAGR and the Sharpe ratio. The basis has
been left unchanged so results remain comparable with earlier runs, but these should
not be read as true annualised figures.