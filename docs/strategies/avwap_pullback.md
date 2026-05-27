# Anchored VWAP Pullback (LONG, Daily)

**Files:**
- Strategy: `scripts/avwap_pullback.pine`
- Python port: `backtest/strategies/avwap_pullback.py`

**Source:** Brian Shannon's anchored VWAP framework (*Maximum Trading Gains with Anchored VWAP*, 2022) — applied with a mechanical anchor for backtestability.
**Direction:** LONG · **Timeframe:** Daily (1D) · **Asset class:** Stocks

## Philosophy

Institutional traders accumulate positions at favorable VWAPs and defend those zones in subsequent pullbacks. Brian Shannon's insight: anchoring a VWAP from a meaningful pivot (cycle low, post-earnings gap, news event) gives you the average price institutions paid since that anchor. In an uptrend, the anchored VWAP acts as **dynamic structural support**.

Buy when:
- The trend is up
- Price has pulled back to the anchored VWAP
- The pullback ends with a clearly bullish candle

The trade thesis is invalidated if price closes below the anchored VWAP — that's the **non-negotiable exit**.

## How we anchor (mechanical proxy)

Shannon's real anchor selection is discretionary — he eyeballs the chart for the meaningful pivot. To make the strategy backtestable, we use a mechanical proxy:

**Anchor = the running lowest low**

- On the first bar, the anchor is set to that bar's low
- On every subsequent bar, if a new lower low is made, the anchor re-anchors to that bar
- Otherwise, the anchor stays put and the aVWAP rises as more bars accumulate at higher prices

In a clean uptrend, the anchor stays at the cycle bottom for years. If price ever breaks the cycle low, the anchor moves down and the strategy waits for a new uptrend setup.

For **live trading**, override the mechanical anchor with discretionary judgment: anchor at the most significant pivot (52-week low, post-COVID-crash bottom, earnings-gap day) rather than the strict all-time low. The script's `anchor_low` is a starting point, not gospel.

## Entry rules

**All must be true on the signal bar:**

1. **Trend up** — close > 50-DMA AND close > 200-DMA AND 50-DMA > 200-DMA
2. **Above aVWAP** — price currently > anchored VWAP (trend-aligned)
3. **Pullback occurred** — the bar low came within `pullback_pct` (default 2%) of the aVWAP within the last `pullback_lb` bars (default 5)
4. **Bounce candle** — current bar: close > open AND close > prior close AND close > prior high
5. **Stop sanity** — distance from close to stop level ≤ `max_stop_pct` (default 20%)
6. **Fundamental gate** — positive Net Income AND positive Revenue YoY growth (optional Min Operating Margin %). Toggleable via `i_use_fund` for crypto/forex. Uses TradingView `request.financial`. Filters out unprofitable / declining-growth names where the technical pullback setup may still trigger but the business doesn't justify holding.

## Exit rules

Three independent exits — first one to fire wins:

| Exit | Trigger |
|---|---|
| Hard stop | bar low touches `anchor_low × (1 − buffer%)` (default 1% buffer) |
| **aVWAP break** | close < anchored VWAP — IMMEDIATE exit at close (the regime-change signal) |
| Trail | close < `trail_ma` (default 20-DMA) lifts cur_stop UP to that level (only ratchets) |

The aVWAP-break exit is the most important — it's "the thesis is invalidated, get out." Trail and hard stop are insurance.

## Position sizing

Standard Van Tharp 2.5% / 25% notional cap. The stop sits below the anchor low, which is often a *wide* stop in absolute terms. That's by design — the anchor low is **structural** support, so being stopped out means the structure broke. Size accordingly: a deeper anchor low gives smaller positions.

## Key points to be careful about

| ⚠️ | Issue |
|---|---|
| **Mechanical anchor ≠ Shannon's discretionary anchor** | Lowest-low-since-start works mechanically but may anchor to a meaningless low (e.g. a single bad day during COVID). Shannon would anchor to the structural pivot (cycle bottom, breakout day, gap-up). For live trades, eyeball the chart. |
| **Wide stops on volatile names** | Anchor low often 20–40% below current price. Position sizing scales it down but you'll hold fewer shares than tighter-stop strategies. |
| **aVWAP-break false exits** | A normal mid-uptrend pullback can briefly close below aVWAP and bounce — the strategy exits there and may miss the continuation. This is a real cost, visible in the +0.04 R measurement. Consider a 1-bar confirmation (require 2 consecutive closes below). |
| **Re-entry not modeled** | After an aVWAP-break exit, the strategy doesn't re-enter unless ALL conditions re-fire from scratch. Real trader would re-enter sooner if price reclaims aVWAP. |
| **Anchor "moves" during drawdowns** | If a new lower low is made mid-trade, the script's anchor moves but the trade's stop is already set at the old anchor. That's correct behavior (stop is fixed at entry), but the *new* aVWAP becomes much lower, harder for price to break below. Can mask aVWAP-break exits. |
| **Daily timeframe limits** | The strategy is designed for swing trades, not intraday. For intraday VWAP work, use a separate script (not in this repo). |

## Best / worst conditions

| ✅ Best | ❌ Worst |
|---|---|
| Clean stage-2 uptrend with regular pullbacks to aVWAP | Choppy sideways or topping action |
| Post-correction recovery (well-defined cycle low) | Mid-decline or no defined pivot |
| Liquid large-caps with smooth price action | Low-volume small caps (aVWAP noisy) |
| Names with steady institutional accumulation | Speculative names with erratic flows |

## Expected frequency & return  (MEASURED — marginal)

### Setup
- Backtest: `backtest/strategies/avwap_pullback.py`
- Universe: `sp500` (503 symbols)
- Period: 10 years daily
- Frictions: 5 bps slippage + $1/fill commission

### Headline numbers

| Metric | Value |
|---|---|
| Total trades | **486** across 503 symbols / 10 years |
| Symbols profitable | **79 / 503** (16%) |
| Win rate | **43.4%** |
| Avg R | **+0.04** (marginally positive) |
| Net | +$51,816 aggregate (across parallel sims) |
| Avg max DD per symbol | −0.7% (very tight) |

### Interpretation

**This is a borderline-tradeable strategy as-coded.** The mechanical anchor + early aVWAP-break exit produces a slightly positive expectancy but the edge is fragile — likely destroyed by any additional friction or by sloppy live execution.

Honest framing:
- **+0.04 R per trade × 2.5% risk = ~0.1% expectancy per trade** — too small for live deployment
- **43.4% WR** is acceptable but the avg win must significantly exceed avg loss to compensate; here they're nearly balanced
- **79/503 profitable** = the strategy doesn't generalize well across the universe; it likely only works on a subset of names with very clean trend structure

### What's likely limiting the strategy

1. **aVWAP-break exit is too sensitive.** Many trades exit on a single close below aVWAP, then aVWAP rises again and price continues higher. A 2-bar or volume-weighted confirmation would likely improve results materially.
2. **Mechanical anchor is sub-optimal.** Shannon's discretionary anchor selection is the real edge; the lowest-low proxy captures maybe half the value.
3. **Universe too broad.** Strategy designed for stage-2 momentum names, not the full SP500. Likely 2–4× better on `momentum15` or `large25`.

### Recommended next iteration

Before deploying capital, try:
1. **Add 2-bar confirmation to aVWAP-break exit** — likely the highest-impact single change
2. **Sweep `pullback_pct`** (default 2%) — see if 1% or 3% is better
3. **Test on momentum15 / curated universes** rather than full SP500
4. **In live trading, override the anchor manually** at known structural pivots

### Reproducibility

```bash
uv run python -m backtest.runner --strategy avwap_pullback --universe sp500 \
     --period 10y --interval 1d --slippage-bps 5 --commission 1
```

## Pair with

- **Use alongside** `consolidation_breakout.pine` and `minervini_sepa.pine` for diversified entry styles (breakout vs pullback)
- **The aVWAP can be used standalone** — even without trading the mechanical entries, having anchored VWAP plotted on a chart improves discretionary entry timing for any LONG setup
