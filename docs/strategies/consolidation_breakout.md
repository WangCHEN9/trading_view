# Weekly Consolidation Breakout (LONG)

**File:** `scripts/consolidation_breakout.pine`
**Source:** FinancialWisdomTV — `strategy/blueprint_2025.pdf`
**Direction:** LONG · **Timeframe:** Weekly (1W) · **Asset class:** Stocks

## Philosophy

Strong stocks build a tight base under resistance, then break out on a volume expansion. The thesis: institutional accumulation compresses the range, and the first decisive close above resistance signals that demand has overwhelmed supply. The weekly timeframe filters out the daily noise that creates false breakouts.

## Entry rules (all must be true on the signal bar)

1. **Trend filter** — close above 20-week SMA
2. **Momentum filter** — MACD line above signal line
3. **Breakout** — close above the 6-week consolidation high (`ta.highest(close, 6)[1]`)
4. **Range** — breakout candle is 5–20% above prior close (not a runaway gap, not a nothing-burger)
5. **Volume** — volume ≥ 30% above prior week's volume (institutional confirmation)
6. **Wick discipline** — upper wick ≤ 50% of candle range (the rally held into the close)
7. **10-week closing high** — close ≥ highest close of prior 10 weeks
8. **Volatility regime** — NATR < 8% (was actually consolidating, not just chopping)
9. **Stop sanity** — stop distance ≤ 20% of price
10. **Fundamentals** (toggleable) — ROE ≥ 10%, ROC ≥ 10%, Operating margin ≥ 10%, YoY revenue + net income positive

## Exit rules

**Two-phase stop** that only ever moves UP:

- **Phase 1 (Initial)** — stop placed at the *lower end of the middle third* of the consolidation box: `support + (resistance - support) / 3`.
- **Phase 2 (Raised)** — when MACD crosses *below* its signal line, raise the stop to that candle's low (only if it's higher than the current stop).

There is no profit target — the trade rides until the trailing stop triggers.

## Position sizing

Van Tharp fixed-fractional risk:
```
qty = floor( (equity × i_risk_pct%) / (entry − stop) )
```
- Default risk: **2.5% of equity** per trade
- Notional ceiling: 25% of equity (`i_max_pos_pct`)

## Key points to be careful about

| ⚠️ | Issue |
|---|---|
| **Fundamentals on non-stocks** | The `request.financial()` block returns `na` for crypto/forex/ETFs. Toggle `i_use_fund` off (and `i_fund_na_ok` on) for those — otherwise every signal is rejected. |
| **Earnings surprises** | Strategy ignores earnings dates. A breakout the week before earnings has roughly 50/50 macro risk on top of the technical edge. Manually defer entries when earnings are within 5 days. |
| **Fakeouts on Friday** | Weekly bar closes Friday 4pm ET. Intraweek prints above resistance that fail by Friday close do *not* trigger entry — that's a feature, not a bug. But it also means you can miss runaways. |
| **Wide stops on volatile names** | NATR < 8% filter is calibrated for large/mid caps. On small-caps with structural 12–15% NATR, no signals ever trigger. Loosen `i_natr_max` for that universe — but recognize that wider stops shrink position sizes proportionally. |
| **Survivorship bias** | Backtests on AAPL/MSFT/NVDA give misleadingly rosy stats. Always validate on a full universe (S&P 500) to see the per-symbol distribution, not just the winners. |
| **Bear markets** | The strategy was designed for stocks in confirmed uptrends. In 2022-style bears almost nothing passes the 20W MA filter — that's correct behavior, but you'll go months without trades. Pair with the Weinstein Stage 4 short for symmetric coverage. |
| **Stop moves only up** | The `ta.crossunder(macd, signal)` raised stop logic uses the *candle low* of the crossdown bar. If the bar already had a deep wick before the cross, your new stop sits well below current price — which is desired. But you cannot tighten further from there without a new MACD crossdown. |

## Best / worst conditions

| ✅ Best | ❌ Worst |
|---|---|
| Confirmed bull market | Choppy sideways, frequent whipsaws |
| Sector rotation INTO leaders | Late-cycle, all stocks extended |
| Post-correction recovery (Q2 2020, Q4 2022) | Active geopolitical/macro shock weeks |
| Stocks with rising institutional ownership | Earnings-blackout windows |

## Expected frequency & return  (MEASURED)

### Setup of the measurement
- **Backtest engine:** `backtest/strategies/consolidation_breakout.py` (Python port of the Pine script)
- **Universe:** `large25` — 25 large-cap US names across sectors (`backtest/universe.py`)
- **Period:** 10 years (≈ 520 weekly bars / symbol)
- **Sizing:** 2.5% risk per trade, 25% notional cap
- **Frictions modeled:** none yet (no commission/slippage — results are slightly optimistic)
- **Fundamentals filter:** OFF (yfinance fundamentals unreliable; pure-technical edge)

### Headline numbers

| Metric | Value |
|---|---|
| Total trades | **142** across 25 symbols / 10 years |
| Symbols profitable | **20 / 25** (80%) |
| Universe-level trade rate | **~1.2 trades per month** (entire 25-stock universe) |
| Per-symbol trade rate | ~0.57 / year ≈ **1 trade every 21 months** per name |
| Win rate | **57.7%** |
| Avg R-multiple | **1.40** (winners + losers blended) |
| Profit factor (universe-weighted) | ~3.5 |
| Avg max drawdown (per symbol) | **−7.1%** |
| Per-trade expectancy (% of equity) | **1.4 × 2.5% = ~3.5%** per trade |

### What "expected return" actually means here

There are two ways to read it — both useful, both honest:

**Per-symbol mode (what the backtest literally measured):**
Each symbol got its own $100K. Average per-symbol net profit ≈ **+19.2% over 10 years** (≈ 1.77% / year). Sounds low because a single name fires only ~6 signals in a decade — the strategy is not designed to be the sole engine of a portfolio.

**Single-account portfolio mode (estimated, NOT yet measured):**
One $100K account taking signals across all 25 names. Math:

```
1.18 trades/month × 1.40R × 2.5% risk = ~4.1% expected return per month  (gross of frictions)
                                       ≈ 50–60% annualized BEFORE drawdowns and capital constraints
```

⚠️ This is a **theoretical ceiling**. In practice you cannot take every signal — multiple breakouts can fire the same week and one account cannot fund all of them. Realistic capture is **60–80%** of signals, giving **~25–40% annualized** in a friendly market. Bear-market years will produce few signals and modest returns.

### Proof / reproducibility

Re-run yourself in ~30 seconds (with cached data):

```bash
uv run python -m backtest.runner --strategy consolidation_breakout --universe large25 --period 10y
```

Outputs:
- Console table identical to numbers above
- `backtest/results/consolidation_breakout_large25_summary.csv` — per-symbol stats
- `backtest/results/consolidation_breakout_large25_trades.csv` — every individual trade with entry/exit dates, prices, qty, R-multiple

### What would change these numbers downward (honest caveats)

| Factor | Likely impact |
|---|---|
| Add 0.3% slippage + $1 commission | ~10–15% haircut on net |
| Switch to point-in-time S&P 500 membership (no survivorship) | Probably another 10–20% haircut — delisted losers (BBBY, FRC, SVB) are not in current universe |
| Bear-market sub-period (2022) only | Expect 0–5 trades/year, near-breakeven or modest loss |
| Tight portfolio capital constraints | Lower capture, lower compounded return |

A **realistic operating-account expectation** for this strategy in a normal-to-good market, after frictions and realistic capital constraints, is in the range of **15–25% annualized**, with max DD around **15–20%**. Promise yourself nothing more.

## Pair with

- **Pre-watch screener:** `scripts/screener_consolidation_watch.pine`
- **Stage filter:** `scripts/screener_stage_analysis.pine` (only trade Stage 2 names)
