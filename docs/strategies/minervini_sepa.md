# Minervini SEPA Trend Template (LONG, Daily)

**File:** `scripts/minervini_sepa.pine`
**Source:** Mark Minervini — *Trade Like a Stock Market Wizard* (2013) & *Think & Trade Like a Champion* (2017). 2× US Investing Champion (1997, 2021).
**Direction:** LONG · **Timeframe:** Daily (1D) · **Asset class:** Stocks

## Philosophy

SEPA = **S**pecific **E**ntry **P**oint **A**nalysis. Minervini hunts for stocks in **Stage 2 advance** that have just finished a tight **volatility contraction** under a pivot, then enters on the breakout from that pivot. The thesis is that institutional buyers absorb supply during the contraction; the pivot break is the moment supply exhausts and demand takes over.

Two layers:
1. **Trend Template** — 8 conditions that filter for stocks in a confirmed stage-2 uptrend
2. **VCP / Pivot Buy** — entry on a breakout from a volatility-contraction pivot

## Entry rules

### Trend Template (7 of 8 Minervini conditions verbatim)

1. Price > 150-SMA *and* > 200-SMA
2. 150-SMA > 200-SMA
3. 200-SMA is rising (>1 month uptrend)
4. 50-SMA > 150-SMA *and* > 200-SMA
5. Price > 50-SMA
6. Price ≥ 25% above its 52-week low
7. Price within 25% of its 52-week high
8. *RS proxy:* stock's 3-month return > SPY's 3-month return (substitutes for IBD's RS rank ≥ 70, which isn't available in Pine)

### VCP + Pivot

- **VCP:** recent 10-bar ATR < 60% of the prior 10-bar ATR (range has tightened)
- **Pivot break:** close above the highest high of the prior 15 bars
- **Volume confirmation:** today's volume > 1.5× the 50-day average
- **Stop sanity:** initial stop (entry − 2× ATR) must be ≤ 10% below entry

All conditions in **trend template + VCP + pivot break + volume + stop check** must be true on the same bar.

## Exit rules

**Chandelier trailing stop**, ratchets up only:
```
trail = highest_high(21 bars) − 2 × ATR(14)
cur_stop = max(cur_stop, trail)
```

Minervini personally favors a wider 50-day MA trail for runners; tune `i_trail_len` for your style. Tighter trail = more exits at small profits but better max DD.

## Position sizing

Same Van Tharp fixed-fractional 2.5% risk · 25% notional cap (see `consolidation_breakout.md` for details).

Initial stop distance = `2 × ATR(14)`, so position size scales inversely with the stock's recent volatility — exactly Minervini's prescription.

## Key points to be careful about

| ⚠️ | Issue |
|---|---|
| **RS rank ≠ 3-month return** | The real IBD RS rank scores a stock against ~7000 names on multi-period returns. Our 3-month-vs-SPY proxy is far cruder — a stock can outperform SPY while still being mid-pack in true RS. For high-confidence trades, manually verify the RS rank on IBD/MarketSmith before placing the order. |
| **VCP is simplified** | Minervini's real VCP counts **discrete contraction waves** (typically 2T → 4 contractions, each shallower than the last). We approximate with a single ATR ratio. The script will flag patterns Minervini wouldn't — and miss textbook VCPs that don't tighten linearly. Best used as a *filter*, then visually confirm pattern. |
| **Earnings catalyst** | Many SEPA breakouts happen on or right after earnings. The strategy ignores earnings dates entirely. **Manual rule:** if signal fires within 2 days of upcoming earnings, skip or size down to 50%. |
| **Late-stage breakouts** | Trend Template can be satisfied at a major top — e.g. a stock that ran 300% will still pass all 8 rules until it breaks down. Minervini's own answer is "**don't chase**" — prefer 1st-stage or 2nd-stage bases, not 4th-stage. The script can't tell stage depth; you must. |
| **Daily noise vs weekly** | This is the daily-timeframe counterpart to the consolidation breakout. Expect 3–5× the signal frequency and more whipsaws. The chandelier trail is wider precisely to absorb that noise. |
| **`request.security("AMEX:SPY", ...)`** | Hardcoded SPY reference. For non-US universes, change to the relevant benchmark (e.g. `TSX:XIU` for Canada, `XETR:DAX` for Germany). |
| **252-bar lookback for 52w hi/lo** | 252 = US trading days per year. For markets with different calendars (HKEX ≈ 244), the lookback is slightly off. Negligible in practice. |

## Best / worst conditions

| ✅ Best | ❌ Worst |
|---|---|
| Confirmed bull market with broad participation | Distribution / topping phases (failed breakouts cluster) |
| Sector themes with relative strength (e.g. semis 2023–24) | Index sideways but heavy rotation (whipsaws) |
| Stocks emerging from 6–12 month bases | Stocks already 50%+ extended above 50-SMA |
| Earnings beats followed by tight basing | Pre-earnings drift up — defer entry |

## Expected frequency & return  (ESTIMATED — pending Python backtest)

⚠️ **These numbers are NOT yet measured by the local harness.** They are estimates drawn from:
1. Minervini's published claims in *Trade Like a Stock Market Wizard* (1997 US Investing Champion: 155% return; 2021: 334%) — these are his *personal* numbers, not the mechanical script's.
2. Independent academic / blog backtests of trend-template + VCP variants.
3. Forward-reasoning from the strategy's structural parameters.

Treat them as **rough priors**, not proof. Replace this section with measured numbers once `backtest/strategies/minervini_sepa.py` exists.

### Frequency estimate

- **Universe basis:** S&P 500, daily timeframe
- The full 7/8 trend template typically passes for **30–80 names at any given time** in a bull market, **5–20** in a sideways tape, near **zero** in a confirmed bear market.
- Of currently-passing names, VCP + pivot break + volume fires roughly **0.5–2% per day**.
- Estimated signal rate: **3–10 signals per week** across the S&P 500 in a bull market; **0–2 per week** in choppy / bear conditions.
- Per-symbol trade rate: **1–4 trades per year** for actively-trending names; many names will produce zero signals their entire backtest.

### Return estimate

| Metric | Estimate | Confidence |
|---|---|---|
| Win rate | 45–55% | medium |
| Avg R | 1.5–2.5 (winners run much longer than losers) | medium-low |
| Per-trade expectancy (at 2.5% risk) | 1.5R × 2.5% ≈ **3.75% per trade** | low |
| Annualized return (bull market) | **30–60%** | low |
| Annualized return (bear market) | **−5% to +5%** (sits flat in cash) | medium |
| Max drawdown | **15–25%** typical | medium |

The wide ranges reflect that *we have not measured this yet*. Minervini's strategy has unusually fat-tailed winners (single trades up 100%+ that drive total return), so the avg-R figure is highly path-dependent.

### Proof — currently unavailable in this repo

To produce real numbers:

```bash
# NOT YET IMPLEMENTED
uv run python -m backtest.runner --strategy minervini_sepa --universe sp500 --period 10y --interval 1d
```

Pending: port of the strategy from Pine to Python in `backtest/strategies/minervini_sepa.py`. Tracked in `ROADMAP.md` Layer 3.

**Interim "proof":** run the `.pine` strategy in TradingView on individual liquid large-caps (AAPL, NVDA, AMD, META, COST) over 5–10 years. The embedded performance table reports per-symbol win rate, profit factor, avg R, and max DD. Log results across 10–20 names and compare to the estimates above. If your single-symbol numbers cluster within these ranges, the priors are reasonable; if they're systematically worse, adjust expectations down.

## Pair with

- **Universe filter:** `scripts/screener_minervini_trend.pine` — same Trend Template logic but as an indicator. Use it to alert which symbols are *currently* passing the 7/8 (or 8/8) template, so you only run the full strategy on filtered candidates.
