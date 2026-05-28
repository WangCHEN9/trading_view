# MTF Structure + Value Swing (Hybrid, Daily HTF / Hourly entry)

**File:** `scripts/mtf_structure_value.pine`
**Direction:** LONG · **Timeframe:** Hourly entry, Daily direction · **Asset class:** Stocks (Premium intraday data)
**Type:** Hybrid — mechanical setup detection + discretionary order-flow confirmation

## What this is

A multi-timeframe swing strategy that fixes the "one timeframe only" limitation of the earlier scripts. Direction is read from the **Daily** chart; entries execute on the **Hourly**. It combines the codeable parts of an order-flow / Smart-Money methodology and hands off the un-codeable parts to you.

## The hard data boundary (read this first)

Pine Script cannot access order-flow data. So this strategy splits cleanly:

| Component | Who does it | How |
|---|---|---|
| HTF direction (Daily structure + MA stack) | 🤖 Script | `request.security` |
| Anchored VWAP | 🤖 Script | native `ta.vwap` |
| Approximated POC (volume-by-price) | 🤖 Script | rolling bucketed-volume estimate ⚠️ not true VP |
| Supply & Demand zones | 🤖 Script | pivot-low base that preceded a rally |
| Market structure (HH/HL) | 🤖 Script | pivot detection |
| Entry trigger (pullback to value + reversal) | 🤖 Script | flags setup + fires alert |
| **Footprint reading** | 🧑 You | not in Pine — read on Premium chart |
| **True delta / delta divergence** | 🧑 You | not in Pine — read on Premium chart |
| **True Volume Profile POC** | 🧑 You | TV's VP indicator (Premium), by eye |

**Why the split:** footprint and delta require bid/ask volume per price level. Pine has only total `volume` — no signed delta, no order-flow. TradingView's Volume Profile indicator exists (Premium) but its values are not exposed to Pine scripts. So the script approximates POC by bucketing bar volume across price; treat it as a guide and trust the real VP indicator visually.

## The workflow (hybrid)

1. Script runs on your 1H chart, watches Daily direction
2. When a setup forms (daily uptrend + price pulled back to value/demand + hourly bullish reversal), it:
   - plots a "SETUP" arrow + a label with entry/stop/target/VWAP/POC
   - fires an alert: *"check footprint + delta divergence before entry"*
3. **You** look at the footprint and delta on the chart:
   - Is there delta divergence (price down, delta flipping positive) at the value zone? → confirms
   - Is the POC acting as support (fair value holding)? → confirms
   - Absorbing volume at the demand zone? → confirms
4. Confirm → take the trade. No confirmation → skip. The script's stop/target/sizing still apply.

## Mechanical logic detail

**HTF direction (Daily):**
- Daily close > daily 50-SMA AND daily 20-SMA > 50-SMA (trend stack), OR
- Daily higher-low structure intact (most recent daily pivot low > prior pivot low)

**Value references:**
- Anchored VWAP (anchored at the running cycle low)
- Approximated POC = price bucket holding the most volume over the last 80 hourly bars

**Demand zone:**
- A swing-low base (hourly pivot low) that preceded a rally of ≥ 8% becomes a demand zone (band from the pivot low up by half the rally trigger), kept active for 60 bars

**Entry (all true):**
- HTF uptrend
- price within 2% of anchored VWAP OR approx POC, OR inside an active demand zone
- hourly bullish reversal bar (close > open AND close > prior close)
- stop ≤ 12%, reward:risk ≥ 2:1

**Exit:**
- Higher-low trailing stop (raises to recent swing low, only ratchets up)
- Target = 2× risk (proxy for next structure level)
- Hard exit if HTF trend is lost

**Sizing:** Van Tharp 2% risk, 20% notional cap.

## Status

🟡 **Experimental — needs TradingView Premium validation.** This script is NOT backtested in the Python harness — it uses intraday data, multi-timeframe `request.security`, and array-based volume bucketing that the harness can't reproduce. Backtest it in TradingView Premium on the 1H chart.

### Validation steps

1. Open a 1H chart of a liquid stock in a daily uptrend
2. Add `mtf_structure_value.pine`, open Strategy Tester
3. Check trade count and the usual stats (WR, PF, avg R, max DD) over the available intraday history
4. Manually inspect 5-10 flagged setups: does the demand zone / VWAP / POC line up with where you'd actually want to buy?
5. Overlay TradingView's real Volume Profile and compare its POC to the script's approx POC — calibrate `i_vp_lookback` / `i_vp_buckets` if they diverge badly

## Honest expectations

Given every *fully* mechanical strategy we've measured fails to beat buy-and-hold SPY, do not expect this one to be a money-printer on its mechanical signals alone. **Its value proposition is the hybrid**: the mechanical layer narrows 500 stocks down to a handful of high-quality structural setups at value, and your discretionary order-flow reading provides the edge that can't be mechanized. That's the realistic role — a discretionary-assist, not an autopilot.

## Pair with

- TradingView's real **Volume Profile** indicator (Premium) — overlay it; trust it over the script's approx POC
- Footprint / delta chart types (Premium) — your confirmation layer
- The screeners — to pre-filter which symbols are worth putting on the 1H chart
