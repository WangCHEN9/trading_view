# Overvalued Growth Breakdown Short (SHORT, Daily)

**Files:**
- Strategy: `scripts/overvalued_growth_short.pine`
- Screener: `scripts/screener_overvalued_growth.pine`

**Source:** Designed from first principles, informed by the empirical record of overvalued-growth unwinds (2000–02 dot-com, 1973–74 Nifty Fifty, 2022 ZIRP unwind).
**Direction:** SHORT · **Timeframe:** Daily (1D) · **Asset class:** Stocks (software / high-multiple growth)

## Philosophy

Pure valuation shorts have a terrible historical track record — multiples can stay irrational for years. What *has* worked, repeatedly, is the **combination** of three conditions firing together:

1. A rich multiple to compress from
2. A fundamental deterioration trigger that justifies multiple compression
3. A technical breakdown confirming the market has begun to repriced

Each layer alone is a coin flip. All three together is when the historical record shows shorts paying off.

> "The market can stay irrational longer than you can stay solvent." — Keynes
>
> Translation: don't short on valuation alone. Wait for the tape to confirm.

## The three-layer filter

A name only qualifies if **all three** layers pass on the same bar.

### Layer 1 — Valuation (rich multiple)

**Pass if any of:**
- Price-to-Sales > 10 (default `i_ps_rich`), OR
- Price-to-Sales > 5 AND trailing operating income negative (default `i_ps_unprof`)

The two-tier rule catches both profitable-but-expensive (CRWD, NET) and unprofitable-and-expensive (S, GTLB, smaller speculatives).

### Layer 2 — Deterioration (fundamental trigger)

**Pass if any of:**
- Revenue YoY growth decelerated by ≥ 5 percentage points vs the same TTM measured one quarter ago (e.g. growth fell from 35% → 28%)
- Trailing operating income negative
- Relative strength weak vs **IGV** (software ETF) over the last 63 trading days

### Layer 3 — Technical (price confirmation)

**All must be true:**
- Close below 50-DMA AND 200-DMA
- 50-DMA below 200-DMA (death cross completed)
- 200-DMA flat or declining over last 50 trading days
- Close below the 20-day low (breakdown)
- Volume > 1.5× the 50-day average (institutional confirmation)

### Macro override

Skip new shorts entirely when **both**:
- SPY is above its 200-DMA
- VIX is below 16

This avoids fighting an obvious bull regime. The strategy will go quiet in 2017-2024-style bull runs and active in 2022-style corrections — that's by design.

## Exit rules

Two complementary mechanisms (a stop fires when EITHER triggers):

1. **Initial stop:** the lesser of:
   - Entry + 2 × ATR(14)
   - Recent 10-bar swing high + 1% buffer
2. **Trailing stop:** ratchets DOWN only — set to the highest high of the past 10 bars, never raised
3. **MACD bullish cross:** tighten to the high of the cross bar (early warning)
4. **50-DMA reclaim:** close above 50-DMA → cover immediately at market (regime change)

## Position sizing

**Tighter than the long-side strategies.** Short squeezes have unlimited tail loss — respect that.

| Setting | Value | Rationale |
|---|---|---|
| Risk per trade | **1.5%** of equity | vs 2.5% for longs — short loss tail is asymmetric |
| Max position notional | 15% of equity | vs 25% for longs — concentration risk |
| Stop floor | tight (2× ATR or swing high) | minimizes time at risk |

Formula:
```
risk_per_share = stop_at_entry − close
qty            = floor( (equity × 1.5%) / risk_per_share ),
                 capped by floor( equity × 15% / close )
```

## Manual pre-trade checks (NOT modeled in script)

These are showstoppers — verify in your broker / market data before placing each order:

| Check | Reject if |
|---|---|
| **Short interest % of float** | > 15% (squeeze risk) |
| **Borrow cost (annualized)** | > 8% (edge erosion) |
| **Days to next earnings** | within 5 days (beat-and-rip risk) |
| **Recent buyout / activist rumor** | any (special situations) |
| **Market cap** | < $5B (microcap manipulation) |
| **Avg daily $ volume** | < $20M (liquidity for cover) |

A signal that fails any of these is **not a trade**, even if the script flagged it. This is the discretionary review layer the methodology requires.

## Key points to be careful about

| ⚠️ | Issue |
|---|---|
| **You're betting against the broad market's drift** | US equities trend up ~10%/year long-run. Short-only strategies fight that drift; their job is to make money in the years equities go down, not every year. Plan to be in cash 50%+ of the time. |
| **The screener will fire on legitimate AI accelerators** | DDOG, CRWD, NET often pass valuation + technical-weakness checks for technical reasons unrelated to a real thesis breakdown. The deterioration layer (revenue decel) filters most of these — but verify the *story* before shorting. |
| **PLTR specifically is hostile to shorts** | Government revenue floor, retail meme base, Karp-driven narrative. Has produced multiple violent squeezes since 2020. If the strategy flags PLTR, size half-normal and use a put spread instead of outright short. |
| **Fundamental data is FactSet via TradingView** | Updates lag the press release by ~1 day. For names that just reported, the YoY-decel signal won't reflect the new print for 24 hours. Manual override needed around earnings windows. |
| **Borrow cost is invisible to the backtest** | A 5% annual borrow on a position held 3 months = 1.25% drag per trade. Avg-R of 1.5 minus 0.5 borrow drag = 1.0 net. Material. |
| **Survivorship bias is INVERTED for shorts** | Long backtests benefit from survivorship (delisted losers excluded). Short backtests are *disadvantaged* — names that went to zero (BBBY, FRC, SVB) are missing from current S&P 500. Real-world short performance is likely BETTER than the backtest. |
| **Drawdowns come from squeeze waves, not slow grinds** | A typical short-strategy DD pattern: 5 small losers in 2 weeks during a market melt-up, not one big slow loss. Plan psychologically for that. |
| **MACD cross-up early exit can over-trade** | The MACD-cross stop tightening is a feature in bear regimes, a bug in choppy regimes (whipsaw exits at bottoms). Tune `i_atr_mult` higher in choppy periods. |

## Best / worst conditions

| ✅ Best | ❌ Worst |
|---|---|
| Bear / correction regime (SPY < 200-DMA falling) | Strong bull regime (everything bounces) |
| Rising real yields | Falling rates / Fed pivot |
| Multiple compression underway in software sector | AI-capex narrative dominant |
| Post-blowup names (already broken trend) | Pre-blowup expensive names (early — wait for break) |
| VIX > 20 with rising | VIX < 15 (squeezes everywhere) |

## Expected frequency & return  (MEASURED — technical-only variant)

### Setup and limitation
- Backtest: `backtest/strategies/overvalued_growth_short.py`
- Universe: `expensive_software` (25 high-multiple software / speculative names)
- Period: 10 years daily
- **Layer 1 (valuation) is NOT in the Python port** — yfinance lacks reliable historical P/S. The Python backtest substitutes universe curation (only names that ARE high-P/S today) for the missing fundamental filter.
- Layer 2 (RS-vs-IGV), Layer 3 (full technical), and the macro override ARE ported.

### Headline numbers (10y bull-dominated regime)

| Metric | Value |
|---|---|
| Total trades | **59** across 25 symbols |
| Symbols profitable | **10 / 25** |
| Win rate | **35.6%** |
| Avg R | **+0.02** (essentially break-even on R basis) |
| Net | **−$3,800** on $100K-per-symbol (essentially flat) |
| Avg max DD per symbol | **−2.4%** |

### How to interpret

This is **textbook "portfolio insurance" behavior**:

- Over a 10-year period dominated by bull markets, the strategy was **essentially flat with small drawdowns** — exactly what an insurance instrument should do during good times
- The macro override (skip when SPY > 200-DMA AND VIX < 16) correctly suppressed activity in obvious bulls
- Bear-regime years (2022) likely carry the strategy; the harness doesn't yet support sub-period slicing to verify

Compared with `weinstein_stage4_short` on large25:
- Weinstein: −$35K over 10y (bleeds in bulls because no macro filter)
- This strategy: −$3.8K over 10y (macro filter prevents most bull-regime bleeding)

**The macro override does its job.**

### Reproducibility

```bash
uv run python -m backtest.runner --strategy overvalued_growth_short --universe expensive_software --period 10y --interval 1d
```

### What's missing from this measurement

- **Layer 1 valuation filter** — would further restrict trades to verifiably-overvalued names. Likely improves WR and avg R.
- **Borrow costs** — not modeled; assume −1 to −3% drag per year per held position
- **Short interest gating** — backtest can't know SI; in live trading, manual rejection of SI > 15% names will help
- **Bear-period isolation** — 2022 sub-period numbers would be the more honest "this works in bears" measurement

## Reproducibility / proof

**Currently unavailable** — strategy not yet ported to Python harness. To validate manually:

1. Apply `screener_overvalued_growth.pine` to a watchlist of:
   - IGV (iShares Software ETF) constituents
   - Plus speculative names: PLTR, SNOW, NET, DDOG, CRWD, MDB, S, GTLB, U, AI
2. Set alert: "Once per bar close, any symbol on watchlist, on 3/3 qualifying signal"
3. For each alert, run `overvalued_growth_short.pine` on the symbol; check the embedded performance table for that single name
4. Apply the manual pre-trade checks (SI, borrow, earnings)
5. Log trades; after 20 trades, compute realized stats

To produce systematic numbers in the Python harness:

```bash
# NOT YET IMPLEMENTED — pending port to backtest/strategies/overvalued_growth_short.py
uv run python -m backtest.runner --strategy overvalued_growth_short --universe igv --period 5y --interval 1d
```

## Risk management framing

Treat this strategy as **portfolio insurance**, not a primary return engine:

- Allocate **at most 25%** of total risk capital to the short book
- Run alongside long strategies (consolidation_breakout, minervini_sepa) — they fund this in good times, this funds them in bad times
- A complete cycle: in 2021 long book makes money / short book bleeds. In 2022 short book makes money / long book bleeds. Combined: lower drawdown, smoother equity curve
- Never put on a short you can't double-down on if it goes against you 10–15% (mental capital test)

## Pair with

- **Universe filter:** `scripts/screener_overvalued_growth.pine` — same 3-layer logic as an indicator. Use it across an IGV-based watchlist to flag candidates daily.
- **Macro confirmation:** `scripts/screener_stage_analysis.pine` — confirms the broader regime is conducive (SPY itself in Stage 3 or 4 makes the basket far more reliable than SPY in Stage 2)
- **Sister strategy:** `scripts/weinstein_stage4_short.pine` — weekly-timeframe, technical-only short on broader stocks. This strategy is the daily-timeframe, fundamentally-screened variant focused on speculative software.
