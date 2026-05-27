# Trading Toolkit — Documentation

This folder explains each strategy and screener: what it does, why, and what to watch out for. Read the matching `.md` before adjusting parameters or running on a new universe.

## Strategies (entry + exit + sizing)

| Doc | Pine file | Timeframe | Direction |
|---|---|---|---|
| [Consolidation Breakout](strategies/consolidation_breakout.md) | `scripts/consolidation_breakout.pine` | Weekly | LONG |
| [Minervini SEPA](strategies/minervini_sepa.md) | `scripts/minervini_sepa.pine` | Daily | LONG |
| [Weinstein Stage 4 Short](strategies/weinstein_stage4_short.md) | `scripts/weinstein_stage4_short.pine` | Weekly | SHORT |
| [Overvalued Growth Breakdown Short](strategies/overvalued_growth_short.md) | `scripts/overvalued_growth_short.pine` | Daily | SHORT |

All three use **Van Tharp fixed-fractional 2.5% risk sizing** with a 25% notional ceiling. See each doc's *Position sizing* section.

## Screeners (indicators for watchlist alerts)

These are pure indicators — no `strategy.entry`. They flag candidates so you only run the full strategy on filtered names.

| Pine file | Pairs with | What it flags |
|---|---|---|
| `scripts/screener_minervini_trend.pine` | Minervini SEPA | Stocks currently passing 7/8 or 8/8 of the Trend Template, with a near-miss alert at 7/8 |
| `scripts/screener_stage_analysis.pine` | Consolidation Breakout (Stage 2) + Weinstein Stage 4 Short | Tags the current Weinstein stage (1–4); alerts on Stage 2 / Stage 4 entry |
| `scripts/screener_consolidation_watch.pine` | Consolidation Breakout | Tight consolidations near resistance — *before* the breakout fires (pre-watch list) |
| `scripts/screener_overvalued_growth.pine` | Overvalued Growth Short | 3-layer filter (valuation + deterioration + technical) for short candidates; respects macro override |

### How to use screeners in TradingView

1. Import `universes/sp500.txt` as a watchlist (Watchlist panel → ⋯ → Import list…).
2. Add the screener indicator to any chart in that watchlist.
3. Right-click the indicator → *Add alert on …*
4. Set Condition to the relevant `alertcondition()` (e.g. "Trend Template Pass").
5. Set Symbol to **"Any symbol on watchlist"** and Trigger to **"Once per bar close"**.
6. Receive alerts via email / mobile push / webhook.

## Cross-cutting concerns

### Position sizing — Van Tharp fixed-fractional

Every strategy sizes positions so that a stop-out loses exactly **2.5%** of equity. Formula:

```
qty = floor( (equity × 2.5%) / |entry − stop| )
```

A 25% notional ceiling (`i_max_pos_pct`) prevents very tight stops from sizing into half the account. Both values are inputs — adjust in the strategy settings UI.

This decouples position size from price: a $10 stock with a $0.50 stop and a $500 stock with a $25 stop consume identical risk capital. Per Tharp, fixed-fractional risk is the single most important professional-vs-amateur differentiator.

### Pine v6 conventions used throughout

- `//@version=6` everywhere
- `plotshape(..., style=shape.X)` — argument is `style`, not `shape`
- All user-defined functions at global scope (never inside `if` blocks)
- Stateful `ta.*` calls (crossover, crossunder, barssince) computed at top level, never gated by `if`
- `var` reset blocks placed *before* entry blocks so entry can overwrite the reset
- `label.delete` before `label.new` to stay under the 500-label limit
- Entries fill at next bar's open (Pine default, `process_orders_on_close=false`)

Full list: `~/.claude/projects/.../memory/pinescript_v6_gotchas.md`

### Risk cautions that apply to ALL strategies

| ⚠️ | Caution |
|---|---|
| **Earnings dates not modeled** | Every strategy ignores earnings. Manually defer entries within 5 days of earnings, or trim size 50%. |
| **Slippage / commission not modeled in Pine** | Set the broker tab in TradingView strategy settings for realistic backtests. The Python harness also currently assumes free fills. |
| **Survivorship bias in any megacap universe** | A 25-stock universe of AAPL/MSFT/NVDA gives inflated stats. Validate on S&P 500 for honest per-symbol distribution. |
| **Per-symbol backtest ≠ portfolio backtest** | Both TradingView and the current Python harness run independent single-symbol simulations. A real portfolio sharing equity across symbols (and capping concurrent positions) will have different aggregate stats and lower DD. Portfolio mode is on the roadmap. |
| **No regime filter on the strategies themselves** | Breakouts fail more often in bear markets; breakdowns fail more often in bull markets. Consider gating with a market regime check (e.g. SPY > 200-DMA) before placing trades manually. |

## Python backtest harness

See `backtest/` for the multi-symbol Python implementation. Currently only `consolidation_breakout` is ported.

```bash
uv run python -m backtest.runner --strategy consolidation_breakout --universe sp500 --period 10y
```

Architecture and caveats documented in the in-code docstring of each module.

## Backtest methodology — read before tuning

See [backtest_methodology.md](backtest_methodology.md) for the full discussion of how to make backtests honest and avoid overfitting. The 10 practices to apply (and 10 traps to avoid) summarize down to: **fewer parameters, broader universe, longer history, harsher frictions** — the strategy that survives all four is worth trading.

## Strategy performance numbers — what's measured vs estimated

| Strategy | Status | Headline |
|---|---|---|
| Consolidation Breakout | **MEASURED** ✅ | 142 trades / 58.5% WR / **1.41 avg R** — strong edge in bull markets |
| Minervini SEPA | **MEASURED** ⚠️ | 7 trades / 14.3% WR / −0.31 R — strategy as-coded is too restrictive + trail too tight; needs work |
| Weinstein Stage 4 Short | **MEASURED** ⚠️ | 40 trades / 27.5% WR / −0.45 R — confirms shorts bleed in bull regimes; needs bear-period isolation |
| Overvalued Growth Short (technical-only port) | **MEASURED** ✅ | 59 trades / 35.6% WR / +0.02 R — break-even with small DD, exactly the "portfolio insurance" profile |

All four are reproducible with one command — see each strategy doc for the exact invocation. The two ⚠️ rows are not strategy failures, they're honest measurements telling us what needs fixing before risking real money.

**Consolidated results report:** [backtest_results.md](backtest_results.md) — full comparison table, per-strategy interpretation, action items derived from the measurements.

## Where to go next

`ROADMAP.md` at the repo root tracks all layers (strategies, screening, backtest, risk, execution, journal) with completed-vs-pending status.
