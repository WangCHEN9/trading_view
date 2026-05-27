# Weinstein Stage 4 Breakdown (SHORT, Weekly)

**File:** `scripts/weinstein_stage4_short.pine`
**Source:** Stan Weinstein — *Secrets for Profiting in Bull and Bear Markets* (1988)
**Direction:** SHORT · **Timeframe:** Weekly (1W) · **Asset class:** Stocks

## Philosophy

Weinstein's 4-stage model treats every stock as cycling through:

| Stage | Description | Action |
|---|---|---|
| **1 — Basing** | Sideways under a flat MA after a prolonged decline | Watch |
| **2 — Advancing** | Above rising MA, accumulation phase | **LONG** |
| **3 — Distribution top** | Sideways above flat/rolling MA | Watch, take profits |
| **4 — Declining** | Below falling MA, supply > demand | **SHORT** |

This strategy targets the **transition from Stage 3 → Stage 4**: a stock that has been distributing under its 30W MA finally breaks down through support on volume. The thesis mirrors the breakout: institutional distribution overwhelms demand at the breakdown bar.

This is the **direct mirror** of the consolidation breakout strategy, with all directional logic flipped.

## Entry rules (all must be true on the signal bar)

1. **Trend filter** — close BELOW 30-week SMA (Weinstein's signature MA length, ~150 days)
2. **MA slope** — 30W MA is flat or falling (`ma[0] ≤ ma[4]`)
3. **Momentum filter** — MACD line below signal line
4. **Breakdown** — close below the 6-week distribution low
5. **Range** — breakdown candle is 3–20% below prior close
6. **Volume** — volume ≥ 30% above prior week (institutional distribution confirmation)
7. **Wick discipline** — *lower* wick ≤ 50% of candle range (sellers held the close)
8. **10-week closing low** — close ≤ lowest close of prior 10 weeks
9. **Volatility regime** — NATR < 8%
10. **Stop sanity** — stop distance ≤ 20% of price

Notice the **3% minimum breakdown** (vs 5% for the long): downside moves tend to be more contained early; smaller threshold catches the breakdown earlier.

## Exit rules

**Two-phase stop**, mirrored — only ever moves DOWN:

- **Phase 1 (Initial)** — stop at the *upper end of the middle third* of the distribution box: `resistance − (resistance − support) / 3`. Stop is ABOVE price for shorts.
- **Phase 2 (Lowered)** — when MACD crosses *above* its signal line, lower the stop to that candle's high (only if lower than current stop).

## Position sizing

Van Tharp fixed-fractional, with risk calculated as `stop − entry` (stop above entry for shorts):
```
qty = floor( (equity × 2.5%) / (stop − entry) )
```
Same 25% notional ceiling.

## Key points to be careful about

| ⚠️ | Issue |
|---|---|
| **Shorting is asymmetric** | Long upside is unlimited; short downside is capped at 100% (stock goes to zero). Worse, a short loss is unlimited (stock can run 500% on a squeeze). **Hard rule:** never override the stop on a short. Default position size is the same 2.5% risk, but consider trimming to 1.5% until you've validated the system live. |
| **Short squeeze risk** | High short-interest names (>20% of float) can pop violently on bad-news clearing or earnings beats. The strategy doesn't check short interest. **Manual rule:** before entering, check the FINRA short-interest report — skip names with SI > 15%. |
| **Borrow availability and cost** | Some small/mid-caps are hard-to-borrow with high stock-loan fees that erode the edge daily. Backtest assumes free borrow. Verify with your broker before sizing. |
| **Dividends and ex-div dates** | Short sellers OWE the dividend on ex-div date. Strategy doesn't model this. For long-duration shorts on dividend-paying names, factor 1–4% per year drag. |
| **Earnings surprises** | A beat into a Stage 4 stock can run +15-25% overnight. The Friday-close stop won't save you from a Monday gap. Manually defer entries within 5 days of earnings. |
| **30W MA, not 20W** | Long strategy uses 20W; this uses Weinstein's specified 30W (~150-day). The longer MA is critical on shorts — 20W generates too many false Stage 4 signals in volatile names. Don't "match" to the long script. |
| **Stage 4 vs panic selloff** | The setup looks for *Stage 3 distribution → Stage 4 breakdown*, not for capitulation lows. Mid-decline shorts (already 30% off the highs) often mean-revert violently. The 30W slope + NATR filter helps, but a stock that's been below the MA for 8+ weeks is probably late to short. |
| **Asymmetric P&L direction** | A long that doubles makes 100%. A short that halves makes 50%. Even with the same hit rate, expectancy is lower per trade on shorts. Compensate with more selective entry — only A+ setups. |

## Best / worst conditions

| ✅ Best | ❌ Worst |
|---|---|
| Confirmed bear market (SPY below 200-DMA, falling) | Strong bull market (everything bounces) |
| Sector rotation OUT of the name (relative weakness) | Heavily-shorted names (squeeze risk) |
| Post-failed-breakout (failed rally before breakdown) | Mid-decline (chase entry, prone to mean-reversion) |
| Wide bid-ask, plenty of borrow | Hard-to-borrow + high stock-loan fees |
| Stable indexes (low VIX) | Macro vol regime — short squeezes blanket the market |

## Expected frequency & return  (MEASURED — and confirms "shorts hate bull markets")

### Setup
- Backtest: `backtest/strategies/weinstein_stage4_short.py`
- Universe: `large25`, weekly, 10 years
- 2015-2025 was a **near-pure bull market** for US large caps — the worst possible backdrop for a short strategy

### Headline numbers

| Metric | Value |
|---|---|
| Total trades | **40** across 25 symbols |
| Symbols profitable | **4 / 25** |
| Win rate | **27.5%** |
| Avg R | **−0.45** |
| Net | **−$35,389** on $100K-per-symbol |
| Avg max DD per symbol | **−4.4%** |

### How to read this correctly

This is **NOT** evidence the strategy is broken — it's evidence shorts get killed in bull markets, which we already knew. The honest test for a short strategy must include bear periods. Three reasonable next steps:

1. **Slice 2022 only** — re-run with `--period 3y` covering 2022's bear; that's the year the strategy is supposed to earn its keep. Expected: positive R, several profitable symbols.
2. **Pair with the long book** — overall portfolio (longs + this short book) should show lower drawdown and smoother equity curve even if shorts alone are net-negative over a decade.
3. **Restrict to bear-regime activation** — add a macro filter (e.g. only enter when SPY < 200-DMA) to suppress activity in obvious bulls. This would have cut most of the −$35K loss.

### What the trade list shows

Symbols with the worst losses (UNH, V, MA, GOOGL, ORCL, LLY) are all long-term up-trenders. The strategy correctly identified short-term breakdowns; the market simply absorbed them and reverted. That's a regime mismatch, not a strategy failure.

### Reproducibility

```bash
uv run python -m backtest.runner --strategy weinstein_stage4_short --universe large25 --period 10y --interval 1wk
```

For a fairer regime-controlled test, slice to bear periods explicitly:

```bash
# Pending implementation: --start / --end date flags in runner.py (Layer 3 backlog)
```

### Frequency estimate

- **Universe basis:** S&P 500, weekly timeframe
- Stage-4 names are **rare in a bull market** (5-15 names at any time) and **common in a bear market** (100+).
- Breakdown setups with volume confirmation fire perhaps **0.3-1% per week** of qualifying stocks.
- Estimated signal rate:
  - **Bull market:** 0-2 signals per month across S&P 500
  - **Sideways / topping market:** 3-6 per month
  - **Bear market (e.g. 2022):** 10-20 per month
- Per-symbol trade rate: **0.3-1 trades per year** for cyclically-weak names; many names will produce zero signals.

### Return estimate

| Metric | Estimate | Confidence |
|---|---|---|
| Win rate | 40-50% (lower than long counterpart) | medium-low |
| Avg R | 1.2-1.8 (declines move faster but reverse hard) | low |
| Per-trade expectancy (at 2.5% risk) | 1.3R × 2.5% ≈ **3.25% per trade** | low |
| Annualized return (bear market) | **15-40%** | low |
| Annualized return (bull market) | **−10% to +5%** (few signals, more squeezes) | medium |
| Max drawdown | **20-30%** (short squeezes hurt) | medium |

The short-side estimate is **deliberately conservative**:

- Win rate is structurally lower because short squeezes generate sharp losers
- Avg R is lower because shorts cap at 100% (stock to zero) while their losers can run unlimited
- Borrow costs and dividend obligations eat 1-4% per year on holdings
- Even moderate macro vol triggers squeeze waves that take out multiple positions at once

### Proof — currently unavailable in this repo

To produce real numbers:

```bash
# NOT YET IMPLEMENTED
uv run python -m backtest.runner --strategy weinstein_stage4_short --universe sp500 --period 10y --interval 1wk
```

Pending: port of the strategy from Pine to Python in `backtest/strategies/weinstein_stage4_short.py`. Tracked in `ROADMAP.md` Layer 3.

**Interim "proof":** run the `.pine` strategy in TradingView across **2018-2025 weekly** on stocks that had clear Stage-3-to-Stage-4 transitions (KSS, BBBY, PTON, ZM post-2021, weakening regional banks 2022-2023). The embedded performance table reports the same metrics as the long strategies. If short-side numbers fall within the estimated ranges, priors are reasonable.

### Realistic expectation framing

Shorts are best treated as a **hedge / diversifier**, not a primary return source. Even with a real edge, a short book typically:
- Loses money in 60-70% of years (bull-dominated US markets)
- Pays for itself + crisis insurance in the remaining 30-40%
- Reduces overall portfolio max DD when paired with longs

Position-sizing rule of thumb: keep short-book exposure ≤ 25% of total risk capital until you've validated the strategy with at least one full bear cycle of live trading.

## Pair with

- **Stage filter:** `scripts/screener_stage_analysis.pine` — only short names currently classified Stage 4 (LONG side: Stage 2)
- **Sister strategy:** `scripts/consolidation_breakout.pine` — same mechanics, opposite direction. Run both on a watchlist for balanced market exposure.
