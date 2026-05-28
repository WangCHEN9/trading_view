# Trading Toolkit — Documentation

This folder explains each strategy and screener: what it does, why, and what to watch out for. Read the matching `.md` before adjusting parameters or running on a new universe.

## Strategies (entry + exit + sizing)

| Doc | Pine file | Timeframe | Direction |
|---|---|---|---|
| [Consolidation Breakout](strategies/consolidation_breakout.md) | `scripts/consolidation_breakout.pine` | Weekly | LONG |
| [Minervini SEPA](strategies/minervini_sepa.md) | `scripts/minervini_sepa.pine` | Daily | LONG |
| [Overvalued Growth Breakdown Short](strategies/overvalued_growth_short.md) | `scripts/overvalued_growth_short.pine` | Daily | SHORT |
| [Anchored VWAP Pullback](strategies/avwap_pullback.md) | `scripts/avwap_pullback.pine` | Daily | LONG |
| [Backside Reversion Short](strategies/backside_reversion_short.md) | `scripts/backside_reversion_short.pine` | Intraday | SHORT |
| [Day 2 Continuation (Power Play)](strategies/day2_continuation.md) | (Python only so far) `backtest/strategies/day2_continuation.py` | Daily | LONG |
| [MTF Structure + Value (hybrid)](strategies/mtf_structure_value.md) | `scripts/mtf_structure_value.pine` | Hourly+Daily | LONG |
| [Liquidity Sweep Reversal (LTF-delta)](strategies/liquidity_sweep_reversal.md) | `scripts/liquidity_sweep_reversal.pine` | Intraday | LONG+SHORT |

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

## Fundamental filters — which strategies use TradingView's request.financial

TradingView exposes FactSet fundamentals via `request.financial(syminfo.tickerid, "FIELD", "TTM")`. We use them in 4 of 5 long-side strategies:

| Strategy | Net Income > 0 | NI YoY ↑ | Rev YoY ↑ | Min OPM | Min ROE | Min ROC |
|---|---|---|---|---|---|---|
| `consolidation_breakout` | — | ✓ | ✓ | 10% | 10% | 10% |
| `minervini_sepa` (new) | ✓ | ✓ | ✓ | 5% | — | — |
| `avwap_pullback` (new) | ✓ | — | ✓ | 0% (off by default) | — | — |
| `overvalued_growth_short` | flips logic — flags **negative** NI or rich P/S | — | — | — | — | — |

All four use `ignore_invalid_symbol=true` so non-stock symbols (crypto/forex/ETFs) don't crash the script. Each has a `i_fund_na_ok` toggle that lets signals through when FactSet has no data (e.g., recent IPOs).

**Python backtest caveat:** The Python harness in `backtest/` does NOT replicate the fundamental filters — yfinance fundamental history is unreliable and not point-in-time. Pine backtests + live trading get the full filter; Python harness measures the **technical-only** edge as a lower bound on real performance.

## ⭐ Discretionary Playbook — how to actually use this toolkit

After testing everything, the durable conclusion is that no mechanical setup beats buy-and-hold SPY in large caps. The toolkit's real value is as a **disciplined funnel + risk framework for discretionary trading**. **[discretionary_playbook.md](discretionary_playbook.md)** is the operating manual: weekly routine, per-candidate review, execution/risk rules, what not to do, and honest expectations. Read it before trading real money.

## Backtest methodology — read before tuning

See [backtest_methodology.md](backtest_methodology.md) for the full discussion of how to make backtests honest and avoid overfitting. The 10 practices to apply (and 10 traps to avoid) summarize down to: **fewer parameters, broader universe, longer history, harsher frictions** — the strategy that survives all four is worth trading.

## Strategy performance numbers — what's measured vs estimated

**Honest scorecard** (single $100K account, max 6 concurrent positions, 5bps + $1/fill frictions, SP500 universe, 10y, vs SPY buy-and-hold):

| Strategy | CAGR | vs SPY | Max DD | vs SPY | Recommendation |
|---|---|---|---|---|---|
| **SPY buy-and-hold (benchmark)** | **15.5%** | — | −32% | — | The yardstick |
| consolidation_breakout | 13.5% | −2 pp | **−23%** | **+9 pp** | 🟡 marginal — DD edge only |
| minervini_sepa | 6.2% | −9 pp | −37% | −4 pp | 🔴 do not trade |
| avwap_pullback | 4.7% | −10 pp | **−4.5%** | **+29 pp** (Sharpe better too) | 🟢 risk-control sleeve only |
| overvalued_growth_short | ≈0 | — | small | — | 🟡 insurance — 2022 made $337 |

**Honest takeaway:** none of these strategies beat passive SPY on absolute returns. Only `avwap_pullback` is risk-adjusted-superior, and only as a low-volatility sleeve. **For most retail traders, SPY-and-chill is the right answer.** See [backtest_results.md](backtest_results.md) for full caveats.

All four are reproducible with one command — see each strategy doc for the exact invocation. The two ⚠️ rows are not strategy failures, they're honest measurements telling us what needs fixing before risking real money.

**Consolidated results report:** [backtest_results.md](backtest_results.md) — full comparison table, per-strategy interpretation, action items derived from the measurements.

## Where to go next

`ROADMAP.md` at the repo root tracks all layers (strategies, screening, backtest, risk, execution, journal) with completed-vs-pending status.
