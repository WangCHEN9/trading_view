# Trading Toolkit — Roadmap

Tracks what we've built and what's still missing before going live with real money.

Legend:  ✅ done · 🟡 partial · ❌ not started

---

## Layer 1 — Strategy Logic

| Item | Status | File / Notes |
|---|---|---|
| Weekly consolidation breakout (LONG) | ✅ | `scripts/consolidation_breakout.pine` — w/ fundamental filters |
| Minervini SEPA + VCP (LONG, daily) | ✅ | `scripts/minervini_sepa.pine` |
| Weinstein Stage 4 breakdown (SHORT, weekly) | ✅ | `scripts/weinstein_stage4_short.pine` |
| Overvalued growth breakdown (SHORT, daily) | ✅ | `scripts/overvalued_growth_short.pine` + matching screener — three-layer filter (valuation + deterioration + technical), macro override, tight 1.5% risk sizing |
| Mean-reversion (RSI(2) / pullback to MA) | ❌ | Larry Connors style |
| Donchian / Turtle trend follower | ❌ | Pure breakout, no fundamentals |
| Intraday strategy (ORB / VWAP reversion) | ❌ | Not on the table yet |

## Layer 2 — Screening / Universe

| Item | Status | File / Notes |
|---|---|---|
| Minervini Trend Template screener | ✅ | `scripts/screener_minervini_trend.pine` |
| Weinstein stage analysis screener | ✅ | `scripts/screener_stage_analysis.pine` — pairs LONG + SHORT |
| Tight consolidation pre-watch screener | ✅ | `scripts/screener_consolidation_watch.pine` |
| Overvalued growth short screener (3-layer filter) | ✅ | `scripts/screener_overvalued_growth.pine` — pairs with `overvalued_growth_short.pine` |
| Define the **universe** to scan | ❌ | E.g. S&P 500, Nasdaq 100, IBD 50, custom watchlist. Must commit to one before alerts are meaningful. |
| TradingView alert setup (per watchlist) | ❌ | Wire each screener as an alert on the chosen universe; "Once per bar close". |
| Liquidity / float floor | ❌ | E.g. min avg daily $ volume = $10M; add as a filter to the screeners. |
| Sector / industry classification overlay | ❌ | Useful for diversification — TV doesn't expose sector in Pine natively, may need manual tag. |

## Layer 3 — Validation / Backtesting

| Item | Status | Notes |
|---|---|---|
| Single-symbol backtest in TradingView | ✅ | Performance analytics table embedded in each `.pine` strategy |
| Python multi-symbol harness (per-symbol) | ✅ | `backtest/` — yfinance data, vectorized signals, stateful execution, R-multiples. Run via `uv run python -m backtest.runner`. Baseline result on large25 / 10y: 57.7% WR, 1.40 avg R, 20/25 symbols profitable. |
| Portfolio mode (shared equity + concurrent cap) | ❌ | Current harness runs N parallel single-symbol sims. Real portfolio needs one equity pool + max concurrent positions. |
| Other strategies ported to Python | ✅ | All 4 strategies ported. Results: `consolidation_breakout` 1.41 avg R ✅; `minervini_sepa` 14% WR / -0.31 R ⚠️; `weinstein_stage4_short` 27.5% WR / -0.45 R ⚠️ (bull regime); `overvalued_growth_short` 35.6% WR / +0.02 R ✅ insurance. See `docs/backtest_results.md`. |
| Fix minervini_sepa trail (chandelier → 50-DMA close) | ✅ | Improved avg R from −0.31 → +0.27. Trail no longer kills winners. VCP filter remains the bottleneck (next iteration). |
| Date-range slicing in runner.py (`--start`/`--end`) | ✅ | Filters trades by entry_date while preserving full-history warmup. Validated on 2022 isolation. |
| Add macro filter to weinstein_stage4_short | ✅ | SPY > 200-DMA gate. Cut bull-regime bleed by 67% (−$35K → −$11K over 10y). |
| Bear-period validation (2022) | ✅ | overvalued_growth_short profitable in 2022 (44% WR, +$337). Validates bear thesis. weinstein_stage4_short fires 0 trades on large25 in 2022 — universe too narrow; expand or loosen filters. |
| Loosen VCP filter or rework VCP detection | ❌ | Minervini's signal rate is too low (7 trades / 15 names / 10y). Either tune ratio or replace with discrete-wave detection. |
| Run all 4 strategies on `sp500` universe | ❌ | 5–10× current trade counts; needed for statistical confidence. |
| Anti-overfitting practices (OOS / WFA / sensitivity / MC / random benchmark) | ❌ | See `docs/backtest_methodology.md` for the full list. Highest priority: time-based train/test split in `runner.py`, then slippage/commission, then walk-forward harness. |
| Walk-forward / OOS split | ❌ | Reserve 2024–2025 for OOS only; train/tune on earlier years |
| Slippage + commission realism | ❌ | Add to backtest engine; TV strategy settings too |
| Robustness: regime test | ❌ | Run on bull (2017, 2020–21), bear (2022), sideways (2015) periods separately |

## Layer 4 — Risk & Position Sizing

| Item | Status | Notes |
|---|---|---|
| Per-trade risk % (Van Tharp fixed-fractional) | ✅ | **2.5% of equity** per trade — `i_risk_pct` in each strategy. `qty = floor((equity × risk%) / (entry − stop))` |
| Max position % of equity (ceiling) | ✅ | `i_max_pos_pct` default 25% — prevents tight stops from oversizing |
| Max trade stop % cap | ✅ | `i_max_stop` in each strategy |
| **Portfolio-level** cap (max concurrent positions) | ❌ | E.g. max 4 open at once = 16% × 4 = 64% deployed |
| Sector exposure cap | ❌ | Don't allow 4 semis at once |
| Correlation check | ❌ | Skip new entry if highly correlated with existing position |
| Kelly fraction calibration | 🟡 | 16% used as Kelly⅓ assumption — needs validation from actual win-rate |
| Heat / drawdown circuit breaker | ❌ | Stop trading after N losses or X% account DD |

## Layer 5 — Execution / Operations

| Item | Status | Notes |
|---|---|---|
| Broker chosen | 🟡 | **Manual workflow via TradingView alerts** (user choice). Pick the actual broker account to use. |
| Alert → order flow | ✅ | **Manual**: TradingView alert → user reviews → places order in broker UI. No webhook/API integration needed. |
| Order types | ❌ | Stop-limit recommended for breakout entries to control slippage |
| Pre-market routine | ❌ | Read alerts, check macro (SPY, VIX, rates), confirm setup quality before placing orders |
| Failure modes drilled | ❌ | What if a fill is missed? Mid-day gap through stop? Halted stock? |

## Layer 6 — Journal & Continuous Improvement

| Item | Status | Notes |
|---|---|---|
| Trade journal template | ❌ | Spreadsheet or Edgewonk / Tradervue. Log entry/exit/R/mistakes per trade. |
| Weekly review cadence | ❌ | Friday post-close: review week's signals + executed trades + missed |
| Monthly stats dashboard | ❌ | Win-rate, avg R-multiple, expectancy, max DD vs backtest expectations |
| Strategy retirement criteria | ❌ | At what point of underperformance do you turn off a strategy? |

## Layer 7 — Optional Tooling (Python side)

| Item | Status | Notes |
|---|---|---|
| `uv` venv in repo | ✅ | `pyproject.toml` at repo root |
| `pdfplumber` for strategy ingestion | ✅ | Used on `strategy/blueprint_2025.pdf` |
| Universe downloader (yfinance) | ✅ | `backtest/data.py` — pickle-cached, 6h staleness |
| Custom backtest engine | ✅ | `backtest/` — vectorized indicators + stateful execution loop. Per-symbol mode only for now. |
| Alert ingestion + journal automation | ❌ | Pipe TradingView alert emails into a Postgres / Sheets log |

---

## Next Concrete Steps  (recommended order)

1. **Commit a universe** — pick S&P 500 or Nasdaq 100 as the scan universe.
2. **Wire screeners to alerts** — set "Once per bar close" alerts on the universe for each screener.
3. **Backtest validation** (in progress) — verify edge across universe before risking capital.
4. **Portfolio risk cap** — decide max concurrent positions and write it into a checklist *before* placing trades.
5. **Pick the actual broker account** — execution flow is manual (alert → review → place order in broker UI).
6. **Paper trade for 4–8 weeks** before real money.

Update this file after each session — tick the box, link the commit.
