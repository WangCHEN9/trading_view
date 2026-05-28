# Trading Toolkit — Roadmap

Tracks what we've built and what's still missing before going live with real money.

Legend:  ✅ done · 🟡 partial · ❌ not started

---

## Layer 1 — Strategy Logic

| Item | Status | File / Notes |
|---|---|---|
| Weekly consolidation breakout (LONG) | ✅ | `scripts/consolidation_breakout.pine` — w/ fundamental filters |
| Minervini SEPA + VCP (LONG, daily) | ✅ | `scripts/minervini_sepa.pine` |
| Weinstein Stage 4 breakdown (SHORT, weekly) | 🗑️ REMOVED | Strategy fundamentally broken (−0.50 R, 22% WR even in 2022 bear). Files deleted commit pending. Pure technical breakdown without fundamental thesis = catching falling knives. Replace with a proper short-side strategy when designed. |
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
| Loosen VCP filter (sensitivity sweep) | ✅ | Default 0.6 → 0.8 after sweep showed wide plateau across 0.8–1.0. Avg R improved from +0.27 to +0.69 on momentum15 / +0.33 on sp500. |
| Run all 4 strategies on `sp500` universe | ✅ | Massive reality check: consolidation_breakout 1.41 R → 0.30 R (survivorship bias was 4×). All numbers in docs/backtest_results.md. |
| Slippage + commission in engine | ✅ | `--slippage-bps` and `--commission` CLI flags on runner.py. Applied post-trade. Long-hold strategies absorb frictions; short strategies more sensitive. |
| Loosen Weinstein entry conditions | ❌ | 0 trades in 2022 on SP500 means the 10-condition filter is too restrictive. Likely culprit: NATR + wick filter conflict with bear-market high-vol candles. |
| Implement VWAP-related strategy | ✅ | `scripts/avwap_pullback.pine` + Python port. Brian Shannon anchored-VWAP framework with mechanical lowest-low anchor. SP500/10y/frictions result: 486 trades, 43.4% WR, +0.04 R — marginal. aVWAP-break exit too sensitive; needs 2-bar confirmation tuning. |
| Improve aVWAP exit (2-bar confirmation) | ✅ | Default avwap_exit_bars=2 in both Pine and Python. Result: +0.04 → +0.05 R — minimal impact. Entry quality is the real bottleneck, not exit. |
| Weinstein diagnostic (find blocking condition) | ✅ | Found the bug: macro_ma=200 on weekly chart = 200 WEEKS (~4y), wrong. Pine has same bug. Fixed to 40 (= ~200 days). After fix: strategy fires 507 trades over 10y but still −0.50 R / 21.9% WR. Strategy is fundamentally broken — shorts at 10-week lows = catching falling knives. Marked DO NOT TRADE. |
| Portfolio mode (shared equity + concurrent cap) | ✅ | `backtest/portfolio.py` — single equity pool, max-N concurrent positions, frictions. CAGR results: consolidation_breakout 13.1%, minervini_sepa 6.2%, avwap_pullback 4.7%. Honest single-account numbers replace inflated parallel-sim aggregates. |
| Redesign Weinstein OR remove it | ✅ removed | All files deleted; doc/memory updated. Future short strategy must combine fundamentals + technicals, not pure technical breakdowns. |
| Backside reversion short (Assan S2) | 🟡 daily=no edge, intraday=untested | Daily Python version measured: no robust edge (best +0.13R isolated noise). Diagnostic: edge is in intraday execution. Pine intraday version written for TradingView validation. |
| Day 2+ Continuation (Assan S3) | ❌ | Power-play momentum continuation. Codeable on daily approximation; not yet built. |
| Intraday data source for harness | ❌ | yfinance gives only 60d intraday. To backtest Assan-style intraday strategies in Python, need a paid intraday source (Polygon, Databento) or accept TradingView-only validation. |
| Fundamental filters on remaining long strategies | ✅ | Added Minervini-style quality gate to `minervini_sepa.pine` (NI>0, NI/Rev YoY+, OPM≥5%) and lighter gate to `avwap_pullback.pine` (NI>0, Rev YoY+). Uses TradingView `request.financial`. |
| Fundamental filters in Python harness | ✅ | `backtest/fundamentals.py` — yfinance quarterly income statements with disk cache. Wired into 3 long strategies + runner + portfolio. CLI flag `--no-fund` disables. **Measurement caveat**: yfinance has only ~4y history so 60% of backtest bars have no data; effect is small (+0.01R on Minervini, ≈0 elsewhere). Real validation must happen in Pine via TradingView Strategy Tester. |
| Drawdown comparison vs buy-and-hold SPY | ✅ | Built into `backtest/portfolio.py`. Results: SPY 10y CAGR 15.5%, max DD −32%, Sharpe 1.98. NONE of the strategies beat SPY on CAGR. Only avwap_pullback beats SPY on risk-adjusted (Sharpe +0.25, DD −4.5% vs −32%). |
| 2008-style bear test (longer / deeper bear) | ❌ | This 10y window had only one short bear (2022). Strategies' true value emerges in 2008-style drawdowns. Need point-in-time index data + 2007-2009 history. |
| Cash-during-inactive accrual | ❌ | Strategies hold cash most of the time. Real-world T-bill yield (4-5%) would add 1-2pp to CAGR. Currently modeled as 0% cash return. |
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
