# Discretionary Trading Playbook

The honest operating manual for this toolkit. After methodically testing ~10 mechanical strategies, fundamentals, multi-timeframe, order-flow/delta, VWAP bands, and three market-cap tiers, the durable conclusion is:

> **No purely mechanical setup we built beats buy-and-hold SPY on a risk-adjusted basis in large-cap US equities. The tools' real value is as a disciplined funnel + risk framework for *discretionary* trading — the machine finds and sizes candidates, you supply the judgment the data can't.**

This playbook is how to actually use the repo for real money, given that.

---

## The core principle

| The machine is good at | You are good at |
|---|---|
| Scanning 500+ names tirelessly | Reading context the script can't see |
| Computing exact position size | Judging setup *quality* (footprint, news, story) |
| Enforcing stops + R:R math | Deciding when *not* to trade |
| Removing emotion from sizing | Adapting to a regime the backtest never saw |

Use each where it's strong. Never let the machine auto-trade (every mechanical version underperformed SPY); never trade without the machine's funnel + risk math (that's how you over-trade and over-size).

---

## The universe rule (proven)

**Trade large caps. Skip small/mid caps for these patterns.** Measured edge by tier (consolidation_breakout avg R): large +0.30, mid +0.17, small +0.06. Small caps are noisier, gappier, friction-heavier, and survivorship-biased. Your watchlist = S&P 500 (`universes/sp500.txt`), optionally filtered to liquid names (>$20M avg daily $ volume).

---

## Weekly routine (weekend prep)

1. **Set the regime.** Is SPY above its 200-DMA and rising? 
   - Above & rising → long setups are in season; be aggressive on the long screeners.
   - Below & falling → long setups fail more; stand down or trade much smaller. (Our long strategies all lose in bear slices — e.g. consolidation_breakout was −0.20 R in 2022.)
2. **Run the screeners** on the S&P 500 watchlist:
   - `screener_minervini_trend.pine` — trend-template passers (stage-2 uptrends)
   - `screener_consolidation_watch.pine` — tight bases nearing breakout
   - `screener_stage_analysis.pine` — confirm broad-market + individual stage
3. **Build a shortlist** of 5–15 names that pass. These are *candidates*, not trades.

## Per-candidate review (the discretionary layer)

For each shortlisted name, pull up the chart and apply judgment the scripts can't:

- **Structure (MTF):** add `mtf_structure_value.pine` — is the daily trend up, is price pulling back to a value zone / demand zone?
- **Value:** is price near anchored VWAP / the σ-band lower edge (Order Flow VWAP), not extended?
- **Order flow (your eyes, Premium):** open the footprint / delta. Is there absorption / positive delta divergence at the level? This is the part no script can read — it's your edge.
- **Catalyst & story:** earnings date? News? Sector strength? Don't buy into an earnings print blind.
- **Liquidity sweeps:** `liquidity_sweep_reversal.pine` or LuxAlgo Liquidity Delta Profiler as a *visual* — did price just sweep stops and reject?

Take the trade only when **structure + value + order flow + story** line up. If you're hesitating, skip it — there's always another setup.

## Execution & risk (let the machine enforce this)

- **Position size:** Van Tharp fixed-fractional. **Risk 1–2% of equity per trade**, never more. The strategy scripts compute exact share count from your stop — use that number.
- **Stop:** below the structural level (demand zone / swing low / breakout base). Non-negotiable. Set it as a hard order.
- **Target / R:R:** require ≥ 2:1 reward:risk before entering. Trail with higher-lows or the 50-DMA once in profit.
- **Portfolio caps:** max ~6 concurrent positions (our portfolio test showed avg R degrades past that as you take lower-quality fills). Max ~2 positions per sector.
- **Never average down. Never widen a stop. Never override the stop.**

## What NOT to do (learned the hard way here)

| ❌ Don't | Because |
|---|---|
| Trust an indicator's "win rate" display | LuxAlgo's Liquidity Delta Profiler showed ~65% via a no-stop time-based metric; real backtest was 42.6% WR, ~2%/yr |
| Believe "AI/ML" labels without reading code | kNN Market Architecture's "ML classifier" is a no-op (scores hardcoded to 1.0) |
| Auto-trade any mechanical strategy | All underperformed SPY risk-adjusted |
| Take these patterns to small caps | Edge halves at mid, near-zero at small |
| Add filters expecting more return | Fundamentals (≈0), VWAP bands (+WR, flat edge), delta (slightly negative) — none raised avg R |
| Short in a bull market | Every short bled; shorts need bear regime + a real thesis |

## Honest expectations

- A disciplined large-cap long book run this way should roughly **track SPY with somewhat lower drawdown** in normal-to-good markets, and **protect capital better in corrections** if you respect the regime rule and stops.
- The *discretionary order-flow read* is the only place a real edge above SPY can plausibly come from — and it's unmeasurable here, which means it's also unprovable. Trade small until your own logged results show it's real.
- **If you don't want to do the discretionary work: just buy SPY/VOO.** That's the honest default and it beat every mechanical strategy we built. This playbook only makes sense if you genuinely want to trade actively and will do the per-candidate judgment.

## The tools, mapped to their honest role

| Tool | Role |
|---|---|
| `screener_*.pine` | Funnel — find candidates |
| `mtf_structure_value.pine` | Structure + value context for review |
| Order Flow VWAP / σ-bands | "How far from value" gauge |
| Dynamic Delta FVG (real LTF delta) | Order-flow confirmation (your eyes) |
| `consolidation_breakout.pine` (sizing/stop logic) | Risk + position-size calculator |
| Backtest harness | Reject mirages cheaply before risking money |
| **Your judgment** | The actual edge |

## Trade journal (do this)

Log every trade: date, symbol, setup, why you took it, stop, target, R-multiple result, and a one-line note on what the order flow showed. After 30–50 trades, compute your *real* win rate and avg R. That — not any indicator's display — tells you whether your discretionary edge is real. If after 50 honestly-logged trades your avg R ≤ 0, stop and buy the index.
