# Liquidity Sweep Reversal (LTF-delta)

**File:** `scripts/liquidity_sweep_reversal.pine`
**Direction:** LONG + SHORT · **Timeframe:** any (intraday recommended) · **Asset class:** Stocks (Premium intraday for best delta)
**Attribution:** Concept distilled from *Liquidity Delta Profiler [LuxAlgo]* (CC BY-NC-SA 4.0). Independent implementation — not a copy of LuxAlgo source.

## Origin

Built from a LuxAlgo indicator the user runs. That indicator detects liquidity zones at swing highs/lows, fills them with volume-delta quadrants, and fires 4 reversal signals (ABS / EXH / DIV / REJ). It also shows a top-right "win rate" table.

**The win-rate table is not a backtest** (confirmed from both the source and LuxAlgo's own article): a "win" = price merely stays on the profit side for N consecutive bars within an eval window, with **no stop loss and no target**. Trades that go far against you and "run out of time" are not counted as losses. So a 65% display can be a money-losing strategy. This script replaces that display with a *real* backtest.

## What this strategy does

Distills the cleanest tradeable signal — **REJ / ABS** (sweep + opposing delta + close back inside) — into a real strategy:

- **Liquidity levels:** most recent confirmed swing high (BSL / resistance) and swing low (SSL / support) via pivots
- **Sweep + reversal:**
  - **Short:** price pokes above the BSL level, closes back below it, and the bar's delta is negative (sellers absorbed the up-sweep)
  - **Long:** price pokes below the SSL level, closes back above it, and the bar's delta is positive (buyers absorbed the down-sweep)
- **Delta — the key upgrade:** real lower-timeframe intrabar delta via `request.security_lower_tf` (buy volume on up sub-bars, sell volume on down sub-bars), instead of LuxAlgo's candle-direction proxy `vol*(close-open)/range`. Requires the sweep bar's `|delta|/volume ≥ threshold` (default 0.2) opposing the sweep.
- **Stop:** beyond the sweep extreme (if price keeps running past the sweep, the thesis is wrong)
- **Target:** R-multiple (default 2:1)
- **Sizing:** Van Tharp 1.5% risk, 15% notional cap

## How to run it

- Chart timeframe must be **larger** than the LTF delta timeframe. E.g. chart = 1H, `i_ltf` = "5". On a daily chart, set `i_ltf` = "60" or "15".
- TradingView **Premium** gives the intraday history depth for a meaningful backtest.
- **Set commission + slippage** in the Strategy Tester before reading results.

## Status

🟡 **Experimental — needs TradingView validation.** Not backtestable in the Python harness (LTF delta + intraday aren't reproducible there).

### The decisive comparison

Run this strategy on the same symbol/timeframe where you watched the LuxAlgo indicator, and compare:

| Metric | LuxAlgo indicator (top-right) | This strategy (real backtest) |
|---|---|---|
| "Win rate" | time-based, no stop/target | real WR with stop + target + costs |
| Profit factor | not shown | computed |
| Max drawdown | not shown | computed |
| Net profit | not shown | computed |

The gap between the two is the whole lesson about indicator win-rate displays.

## Honest expectation

This is **fade-the-sweep mean reversion** — the same family as our `backside_reversion_short`, which showed no edge on daily data. The differentiator here is the **LTF-delta confirmation**: the bet is that requiring real intrabar delta to oppose the sweep filters out the false reversals. Whether that actually adds edge is the open question — measure it, don't assume it. If the real numbers are far below the indicator's display (likely), that's the expected, valuable finding.

## Pair with

- The LuxAlgo indicator itself (visual zones + the delta quadrants) as a discretionary overlay
- The MTF Structure + Value hybrid — use HTF direction to only take sweeps in the HTF trend direction
