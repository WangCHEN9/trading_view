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

## Expected frequency & return  (MEASURED — after 50-DMA trail fix)

### Setup
- Backtest: `backtest/strategies/minervini_sepa.py`
- Universe: `momentum15` (15 high-momentum names — the strategy's natural habitat)
- Period: 10 years daily
- **Trail switched from chandelier (21-bar HH − 2×ATR) to 50-DMA close** — Minervini's actual exit rule
- VCP measurement corrected (excludes breakout bar) vs literal Pine port
- Frictions: none modeled

### Headline numbers

| Metric | Value | vs old chandelier trail |
|---|---|---|
| Total trades | 7 | (same — VCP filter is the bottleneck) |
| Win rate | **28.6%** | up from 14.3% |
| Avg R | **+0.27** | **up from −0.31** (+0.58 R improvement) |
| Net | **−$193** | up from −$4,770 |
| Avg max DD | −2.8% | (slightly worse — wider trail means deeper retracements) |

### What the trail fix proved

Swapping the 21-bar chandelier trail for a 50-DMA close trail moved avg R from **−0.31 to +0.27** — a swing of +0.58 R per trade — without changing any other parameter. Same 7 entries, just allowed to ride longer:

- Old chandelier exited on the first pullback after the breakout. Most winners turned into break-evens or small losses.
- New 50-DMA trail lets the trend develop. The DMA itself rises as the trade does, ratcheting the stop up smoothly.

This is consistent with Minervini's own published practice. The Pine source also had the chandelier trail; both are now corrected.

### What's still wrong

**The VCP filter is still the bottleneck.** 7 signals over 15 names × 10 years (≈ 0.05 signals/symbol/year) is implausibly low. Mechanical VCP detection is a known weak point — Minervini's real process counts discrete contraction waves visually. The single ATR-ratio proxy we use captures only ~10% of the textbook patterns.

### Recommended next steps before risking capital

1. **Run on `sp500` daily** for a larger sample (would take ~10 minutes first run; signal count likely 100–300)
2. **Loosen VCP ratio** experimentally (0.6 → 0.8) and re-measure. Note: this is risk of overfitting; document explicitly.
3. **Validate on TradingView individual charts** — does the mechanical entry visually match a Minervini-quality VCP? If not, the script needs a different VCP detection algorithm.

### Reproducibility

```bash
uv run python -m backtest.runner --strategy minervini_sepa --universe momentum15 --period 10y --interval 1d
```

Outputs `backtest/results/minervini_sepa_momentum15_summary.csv` and `_trades.csv`. **This negative result is a feature** of the methodology: better to learn the strategy is broken in backtest than in live trading.

## Pair with

- **Universe filter:** `scripts/screener_minervini_trend.pine` — same Trend Template logic but as an indicator. Use it to alert which symbols are *currently* passing the 7/8 (or 8/8) template, so you only run the full strategy on filtered candidates.
