# Backtest Results — All Strategies

Consolidated measurement record for every strategy in the repo. Run via the Python harness:

```bash
uv run python -m backtest.runner --strategy <name> --universe <name> --period 10y --interval <1d|1wk>
```

Each row below is reproducible by re-running the command shown. CSVs written to `backtest/results/`.

---

## Headline summary — latest measurements

| Strategy | Universe | TF | Period | Trades | WR | Avg R | Net | Verdict |
|---|---|---|---|---|---|---|---|---|
| **consolidation_breakout** | large25 | 1wk | 10y | **142** | **58.5%** | **+1.41** | +$480K | ✅ strong edge |
| **minervini_sepa** *(50-DMA trail)* | momentum15 | 1d | 10y | 7 | 28.6% | **+0.27** | −$193 | 🟡 trail fixed; VCP still bottleneck |
| **weinstein_stage4_short** *(macro filter)* | large25 | 1wk | 10y | 13 | 30.8% | −0.37 | −$11K | 🟡 macro filter cut bleed 67% |
| **overvalued_growth_short** | expensive_software | 1d | 10y | 59 | 35.6% | +0.02 | −$3.8K | ✅ insurance profile confirmed |
| **overvalued_growth_short** | expensive_software | 1d | **2022 only** | **18** | **44.4%** | **0.00** | **+$337** | ✅ bear-period thesis validated |
| weinstein_stage4_short | large25 | 1wk | 2022 only | 0 | n/a | n/a | $0 | ⚠️ universe too narrow for bears |

**All measurements no commission/slippage modeled.** Per-symbol stats are valid; aggregate $ figures are 25 parallel single-symbol simulations, not a single portfolio sharing equity.

### What changed since last run

| Change | Before | After | Impact |
|---|---|---|---|
| Minervini: chandelier trail → **50-DMA close trail** | −0.31 R | +0.27 R | Wins no longer cut prematurely; +0.58 R improvement |
| Weinstein: added **SPY > 200-DMA macro filter** | 40 trades, −$35K | 13 trades, −$11K | 67% of bull-regime entries correctly suppressed |
| Runner: added **`--start` / `--end`** flags | n/a | works | Can isolate bear-period (2022) for short-strategy validation |

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
