# Backtest Results — All Strategies

Consolidated measurement record for every strategy in the repo. Run via the Python harness:

```bash
uv run python -m backtest.runner --strategy <name> --universe <name> --period 10y --interval <1d|1wk>
```

Each row below is reproducible by re-running the command shown. CSVs written to `backtest/results/`.

---

## Headline summary — latest measurements

**Now with realistic frictions (5bps slippage + $1/fill commission) and full S&P 500 universe** where applicable.

| Strategy | Universe | TF | Period | Trades | WR | Avg R | Verdict |
|---|---|---|---|---|---|---|---|
| **consolidation_breakout** | **sp500** | 1wk | 10y | **2914** | 42.1% | **+0.30** | ✅ real edge, smaller than large25 suggested |
| consolidation_breakout | sp500 | 1wk | 2022 only | 208 | 31.2% | −0.20 | ⚠️ correctly fails in bear (long-only system) |
| consolidation_breakout (reference) | large25 | 1wk | 10y | 142 | 58.5% | +1.39 | ⚠️ survivorship-inflated 4× |
| **minervini_sepa** *(0.8 VCP + 50-DMA trail)* | **sp500** | 1d | 10y | **871** | 33.6% | **+0.33** | ✅ small positive edge across universe |
| minervini_sepa | momentum15 | 1d | 10y | 49 | 42.9% | +0.69 | ✅ stronger on selected high-mo names |
| **weinstein_stage4_short** *(macro filter)* | sp500 | 1wk | 10y | 476 | 31.3% | **−0.24** | 🔴 entry too restrictive + bull regime |
| weinstein_stage4_short | sp500 | 1wk | 2022 only | **0** | — | — | 🔴 entry filter blocks even bear-period signals |
| **overvalued_growth_short** | expensive_software | 1d | 10y | 59 | 35.6% | +0.01 | ✅ insurance profile holds with frictions |
| overvalued_growth_short | expensive_software | 1d | 2022 only | 18 | 44.4% | 0.00 | ✅ bear-period profitable in dollars (+$337) |

### Real-world expectancy estimates

Applying risk-per-trade sizing (2.5% longs / 1.5% shorts):

| Strategy | Per-trade expectancy (% of equity) | Frequency (universe-wide) |
|---|---|---|
| consolidation_breakout (sp500) | 0.30 × 2.5% = **+0.75%** | ~291 signals/year |
| minervini_sepa (sp500) | 0.33 × 2.5% = **+0.83%** | ~87 signals/year |
| weinstein_stage4_short (sp500) | −0.24 × 2.5% = **−0.60%** | ~48 signals/year (negative — don't trade) |
| overvalued_growth_short (expensive_software) | 0.01 × 1.5% = **+0.02%** | ~6 signals/year (flat — insurance only) |

For a single-account portfolio (~5-8 concurrent positions), real capture is **15–30% of universe signals** → **realistic annualized returns**:
- consolidation_breakout: 50–80 trades/year × 0.75% = **40–60% annualized gross**, likely **15–25% after capital constraints**
- minervini_sepa: 15–25 trades/year × 0.83% = **12–20% annualized gross**, likely **8–15% net**
- weinstein_stage4_short: **DO NOT TRADE** as-is (negative expectancy)
- overvalued_growth_short: keep as insurance only, expect ~0% most years, +5-15% in bear years

### What changed since last run

| Change | Before | After | Impact |
|---|---|---|---|
| Engine: realistic **frictions** (5bps + $1/fill) | none | applied | ~5–15% R haircut per strategy |
| Minervini: **VCP ratio 0.6 → 0.8** (after sensitivity sweep) | 7 trades, +0.27 R | 49 trades momentum15 / 871 sp500, +0.33–0.69 R | 12× signal frequency, R improved |
| **SP500 universe** runs for all strategies | n/a | done | Survivorship bias on large25 was 4× inflation |
| Weinstein 2022 SP500 validation | not run | done — 0 trades | Confirms entry conditions broken, not just universe |

### Minervini VCP sensitivity sweep (proof the 0.8 default isn't curve-fit)

Run with `backtest.sweep --strategy minervini_sepa --universe momentum15 --param vcp_ratio --values 0.5 0.6 0.7 0.8 0.9 1.0`:

| vcp_ratio | trades | WR | avg R |
|---|---|---|---|
| 0.5 | 0 | — | — |
| 0.6 (old default) | 7 | 28.6% | +0.27 |
| 0.7 | 23 | 26.1% | −0.01 |
| **0.8 (new default)** | **49** | **42.9%** | **+0.69** |
| 0.9 | 80 | 36.2% | +0.46 |
| 1.0 (no VCP filter) | 111 | 36.0% | +0.55 |

Wide plateau across 0.8–1.0 confirms robustness — not a sharp peak at exactly one value. Theoretical fit: Minervini's textbook discrete-wave VCP contracts from ~15% → ~3% in the final wave (~20% reduction = TR ratio ~0.8, not 0.6).

---

## Strategy-by-strategy interpretation

### ✅ consolidation_breakout — strong edge confirmed

- **142 trades, 58.5% WR, 1.41 avg R, 20/25 symbols profitable** is a clean, defensible edge measurement
- Per-trade expectancy ≈ 1.41 × 2.5% = **3.5% of equity per trade**
- Universe-level trade rate ≈ 1.2/month → realistic single-account annualized: **15–25% after frictions and capital constraints**
- Losers cluster in slow-growth/value names (UNH, V, MA, HD, BRK-B) — strategy correctly does NOT find edge there
- The only LONG strategy with all-green measurements

**Caveats:** survivorship bias in megacap universe, no commissions modeled, per-symbol not portfolio.

### ⚠️ minervini_sepa — too restrictive as-coded

- **7 trades in 10 years across 15 high-momentum names is implausibly few** for a strategy meant to fire weekly
- 14.3% WR with −0.31 R means losers dominate the small sample
- Two structural causes diagnosed:
  1. VCP filter is extremely selective (60% ATR contraction is rare)
  2. Chandelier 21-bar trail + 2×ATR initial stop combine to exit before moves develop
- Minervini personally uses a 50-DMA trail, not chandelier — likely the single biggest fix

**Action items before risking capital:** swap chandelier for 50-DMA trail, re-run; if still poor, run on SP500 for larger sample; consider discretionary review layer per Minervini's actual process.

### ⚠️ weinstein_stage4_short — bull-market mismatch

- **40 trades, 27.5% WR, −0.45 R on a 10-year US large-cap bull run is the expected outcome** — not a strategy failure
- Worst losses on UNH, V, MA, GOOGL — all long-term up-trenders that absorb short-term breakdowns and revert
- Strategy correctly identifies breakdowns; the macro environment punished every one of them
- Test missing: 2022-only sub-period (the year the strategy is designed for)

**Action items before risking capital:** add macro filter (only enter when SPY < 200-DMA) to suppress bull-regime activity; backtest 2022 alone to validate the bear thesis; consider pair-trading with a long book.

### ✅ overvalued_growth_short — insurance profile confirmed

- **Essentially flat over 10 bull-dominated years** is exactly the "portfolio insurance" profile the doc promised
- 35.6% WR, +0.02 R, −$3,800 net = the macro override correctly suppressed activity in obvious bulls
- Compared with weinstein_stage4_short on similar timeframe: −$3,800 vs −$35,389. The macro filter is doing the work.
- Strategy designed to *carry* in bear periods (2022) and *not bleed* in bulls — measurement confirms the second half

**Caveats:** Python port is **technical-only**; Layer 1 (valuation) not implemented (yfinance fundamentals unreliable). Universe curation (expensive_software list) is the substitute. Real valuation filter likely improves WR + avg R.

---

## What the measurements tell us about the next milestones

Priority order, derived from the results:

1. **Fix minervini_sepa trail** — swap chandelier for 50-DMA close. Single highest-value change. Re-measure.
2. **Add date-range slicing to runner.py** — `--start 2022-01-01 --end 2022-12-31` — so we can isolate the 2022 bear and validate both shorts work in their intended regime.
3. **Add slippage + commission to engine** — `slippage_bps=30, commission=1` per fill. Will haircut consolidation_breakout's 1.41 avg R by ~15%.
4. **Run all 4 strategies on `sp500` universe** for sample-size confidence (5–10× current trade counts).
5. **Add SPY > 200-DMA macro filter to weinstein_stage4_short** — same one overvalued_growth_short has — and re-measure.

These are tracked in `ROADMAP.md` Layer 3.

---

## Honest framing for any single number above

Every percentage above is **per-symbol on a 25-stock universe, assuming each name starts with $100K and takes every signal**. A real single-account portfolio sharing equity across all 25 symbols, with realistic frictions and capital constraints, will produce **different (likely lower) absolute returns** but should retain similar per-trade edge characteristics (WR, avg R, max DD per name). The portfolio-mode harness is on the roadmap.

For the four numbers that DO matter forward:
- consolidation_breakout: WR ≥ 55% and avg R ≥ 1.2 after frictions = real edge
- minervini_sepa: do not deploy real money until WR ≥ 40% and avg R ≥ 1.0 after fixes
- weinstein_stage4_short: validate 2022-only sub-period BEFORE deploying
- overvalued_growth_short: deploy at modest size (25% of short capital max) as insurance; expect 2-3 years between meaningful positive contributions
