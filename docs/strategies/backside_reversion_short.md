# Backside Mean-Reversion Short (SHORT)

**Files:**
- Pine (intraday): `scripts/backside_reversion_short.pine`
- Python (daily approximation): `backtest/strategies/backside_reversion_short.py`

**Source:** "Assan" Strategy 2 — Mean Reversion / Backside Swing Short (user-provided methodology breakdown).
**Direction:** SHORT · **Timeframe:** Intraday (5-15 min) with daily context · **Asset class:** Volatile mid/small caps, squeeze names

## Philosophy

A parabolic stock — extended far above its mean on climax (blow-off) volume — traps buyers near the top. After the peak, a "dead-cat bounce" back into the **supply zone** (where the peak volume traded) that then FAILS (lower high, rejection, loses intraday VWAP) marks the momentum shift. Short the failed bounce; target reversion to the daily mean.

This is the **short-term reversal anomaly** — one of the most documented edges in academic finance — applied with discretionary intraday timing.

## ⚠️ Critical finding: daily version has NO edge — intraday is the whole point

We built and tested a **daily-bar approximation** in the Python harness first. Result across SP500 / 10y / frictions:

| ext_pct | trades | WR | avg R |
|---|---|---|---|
| 15 | 119 | 22.7% | −0.04 |
| 20 | 77 | 29.9% | +0.13 |
| 25 | 55 | 27.3% | −0.01 |
| 30 | 35 | 28.6% | +0.04 |
| 40 | 24 | 16.7% | −0.28 |

No plateau, no robust edge — the +0.13 at ext_pct=20 is an isolated noise spike (neighbors are negative). **The daily version does not work.**

**Why this matters:** the failure is diagnostic, not damning. Assan's actual entry is a 5-min lower-high rejection at the supply zone with VWAP confirmation. By the time a *daily* bar confirms the rejection, the precise entry is a day gone and the fill is far worse. **The edge — if real — lives in the intraday execution timeframe**, which the daily harness cannot capture. This is a *data/timeframe* gap, not a "judgment can't be mechanized" gap.

## The fair test: intraday in TradingView

The Pine version runs natively on a 5-min/15-min chart and pulls daily context via `request.security`:

- **Daily layer:** overextension (close > 30% above 50-DMA) + climax volume (> 2× daily 50-day avg)
- **Intraday layer:** intraday VWAP, high-of-day tracking, supply-zone proximity, lower-high rejection trigger
- **RVOL ≥ 1.5** on the trigger bar (Assan's liquidity/institutional-attention filter)
- **3:1 reward:risk minimum** (Assan's baseline)
- **Stop** above HOD + buffer; **target** = daily mean (`request.security` 50-DMA)

### How to validate it

1. Open a **5-min or 15-min chart** in TradingView of a stock that went parabolic and reversed: SMCI 2024, GME/AMC 2021, any recent squeeze
2. Add `backside_reversion_short.pine`
3. Read the Strategy Tester results
4. **Compare to the daily Python result (no edge).** If the intraday version shows a real edge, that PROVES the edge was in the execution timeframe — and validates that Assan's method IS mechanizable, just at the right resolution.

### Honest caveats

- **Unverified** — this Pine script has NOT been validated (the Python harness has no intraday data). It needs your TradingView testing.
- **TradingView intraday backtest depth is limited by plan** — you may only get a few months of 5-min history. Test across multiple known blow-off events rather than one long backtest.
- **Shorting squeeze names is dangerous** — unlimited tail risk, violent reversals, hard-to-borrow, high fees. Keep risk % low (default 1.5%) and never override the stop.
- `request.security` uses `lookahead_off` to avoid look-ahead bias — do not change.

## Status

🟡 **Experimental — needs intraday validation in TradingView.** The daily version is confirmed edge-less; the intraday version is the actual test of whether the methodology mechanizes. This is the open experiment.

## Pair with

- `screener_overvalued_growth.pine` — to find extended candidates worth watching for the backside setup
- The other Assan strategies (Consolidation Breakout = our `consolidation_breakout.pine`; Day 2 Continuation = not yet built)
