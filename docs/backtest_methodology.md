# How to Improve the Backtest Without Overfitting

A backtest's job is to **estimate forward-looking edge**, not to "look good on the chart." Every improvement listed here pushes the result toward something believable; every habit listed below pushes it toward fantasy.

## The core trap: optimization on past data

If you keep tweaking parameters until results look great, you'll find a configuration that fits the past beautifully and **will not work going forward**. The market doesn't repeat the exact noise pattern you optimized to. This is **curve fitting / overfitting** — the single biggest reason retail systems fail in live trading.

Rule of thumb: **every parameter you tune costs degrees of freedom.** A strategy with 12 tunable inputs optimized over the same dataset is almost certainly overfit, no matter how clean the equity curve looks.

---

## Practices that make the backtest more honest

### 1. Out-of-sample (OOS) reservation
**Do once, never re-use.**

- Split data into **in-sample (IS)** ~70% and **out-of-sample (OOS)** ~30% by time (not by random sampling — markets are non-stationary).
- Tune *everything* on IS only.
- When you think you're done, run **one** test on OOS. If results degrade by >40% from IS, the strategy is curve fit — discard parameter changes and start over.
- Critical: **once you peek at OOS, it's no longer OOS.** Burn that window. If you peek, reserve a fresh OOS slice for next time.

For this repo: tune on **2015–2022**, hold out **2023–2025** untouched. Mark this explicitly in commit messages.

### 2. Walk-forward analysis (WFA)
Stronger than a single OOS split — tests stability across time.

- Rolling windows: e.g. train on 3 years, test on 6 months, slide forward 6 months, repeat.
- Concatenate all OOS slices into a synthetic "live" equity curve.
- If WFA equity curve looks similar to the IS curve, the edge is **persistent**. If WFA is a flat or noisy line while IS looks great, you've curve-fit period-specific patterns.

### 3. Parameter sensitivity
A real edge is robust to nearby parameter values. A curve-fit edge collapses if you nudge any input.

- For each parameter (e.g. `i_consol_len`, `i_natr_max`), sweep ±30% around the chosen value.
- Plot the metric (e.g. profit factor) vs parameter value.
- **You want a plateau, not a peak.** A sharp peak at exactly `i_consol_len = 6` with cliff drops at 5 and 7 = overfit. A wide plateau where 4–10 all produce profit factor 1.5–2.0 = real edge.
- Reject any parameter where the "best" value is more than 1.5× better than its neighbors.

### 4. Cross-universe robustness
Edge that exists on one universe should partially generalize.

- Run on S&P 500, then Nasdaq 100, then Russell 1000, then a non-US market.
- Won't be identical (sector composition differs), but per-symbol win rate and avg R should be in the same neighborhood.
- If a strategy works only on a hand-picked 10-stock universe and falls apart elsewhere, you've cherry-picked.

### 5. Regime testing
Markets have distinct macro environments. Test each.

| Regime | Years |
|---|---|
| Strong bull | 2017, 2019, 2020 (H2), 2021, 2023 (H2)–2024 |
| Bear / correction | Q4 2018, Mar 2020, 2022 |
| Sideways / choppy | 2015, 2016 (H1), Q1 2019 |

A trend-following strategy *should* underperform in chop — that's expected. But it must not blow up. Test each regime separately and accept that the strategy has a regime preference. Don't force it to work everywhere.

### 6. Minimum sample size
Statistical confidence requires enough trades.

| Trades | Confidence |
|---|---|
| < 30 | Garbage. Pure luck. |
| 30–100 | Suggestive. Could be edge or could be noise. |
| 100–300 | Plausible edge. Stable enough for cautious live trading. |
| 300+ | Strong statistical signal. |

The consolidation breakout currently produces ~6 trades per symbol over 10 years. To get to 300 trades you need a universe of ~50 symbols. Test across the S&P 500 (~3000+ potential trades) before claiming confidence.

### 7. Realistic frictions
Add costs to break the illusion of perfect fills.

- **Commission:** $0 at most US brokers now, but if you're elsewhere model it (typically 0.05–0.1% per trade).
- **Slippage:** for breakout entries on weekly bars, assume **0.3–0.5%** worse than the open price (limit orders may not fill at all on a runaway).
- **Bid-ask spread:** for liquid large-caps, ~1–3bps. For small caps, 20–50bps.
- **Short borrow costs:** 0.5–5% annual on easy-to-borrow names; 25%+ on hard-to-borrow. Critical for the Weinstein Stage 4 short.
- **Dividend obligation on shorts:** subtract dividends on ex-div date.

A strategy that's marginally profitable before frictions is likely a money-loser after.

### 8. Compare to dumb benchmarks
Your strategy must beat trivial baselines.

- **Buy-and-hold of the universe** — if a basket of S&P 500 returns 10% annualized, your "edge" must do meaningfully better *risk-adjusted* (not just nominal return). Compare Sharpe / Sortino, not just total return.
- **Random entries** — generate 142 random entry dates matching the strategy's trade count. Average over 1000 such random runs. Real edge should produce results clearly above the random distribution.
- **Naive momentum** — "buy when close > 50-DMA, sell when close < 50-DMA" is a respectable baseline. If your fancy 12-parameter strategy doesn't beat that, simplify.

### 9. Monte Carlo on trade order
Even with a fixed strategy on fixed data, **the order of trades affects max drawdown**. Two identical edge profiles with different trade ordering can have very different worst-case DDs.

- Take the list of 142 trades (their R-multiples), shuffle the order 1000 times, recompute the equity curve each time.
- The 5th-percentile max DD is closer to your real-world risk than the single backtest's max DD.

### 10. Keep parameter count low
The fewer tunables, the less room to curve-fit.

- Justify every input from **theory or domain knowledge**, not from "this number gave better results."
- Default values from the original source (Minervini's 50/150/200 SMAs, Weinstein's 30W MA) are *priors* — don't optimize them away.
- If you find yourself adding a new input to fix a specific backtest failure, that's a curve-fit smell. Either accept the loss or rethink the setup.

---

## Habits that destroy backtests (avoid these)

| ❌ Habit | Why it lies |
|---|---|
| **Look-ahead bias** | Using future data the strategy couldn't actually know on the signal bar. Pine v6's `[1]` shift convention is your friend — use it consistently for "prior bar" lookups. |
| **Survivorship bias** | Backtesting only stocks that still exist today. Yfinance gives you only current S&P 500 members. The actual 2015 S&P 500 included names since delisted (BBBY, FRC, SVB, etc.) which would have lost you money. Use a **point-in-time** index membership list (typically paid data) for an honest backtest. |
| **Cherry-picked universe** | "It works great on AAPL, MSFT, NVDA!" Of course — those are the survivors of the past decade. Always test on a broad index. |
| **Cherry-picked period** | "It works great from 2016 onward!" Yes, because the market mostly went up. Test bear years explicitly. |
| **Re-using OOS** | Tuning until OOS also looks good. By the third "OOS" test you've turned it into IS. |
| **Tuning to max profit** | Equity curve maximization picks the most curve-fit parameters. Tune to **profit factor + low DD** instead, which favors robustness. |
| **Single backtest = truth** | One run is a sample of one. Use walk-forward + Monte Carlo to get a distribution. |
| **Ignoring trade count** | "30% return!" — across 4 trades. Not a strategy, a coincidence. |
| **Compounding misuse** | Using `% of equity` sizing on a 10-year backtest can create exponential equity curves that look amazing but are unrealistic (you can't really get filled at scale). Fixed-fractional risk sizing (which we use) avoids this. |
| **Optimizing during live trading** | Stop changing parameters once you go live. Drawdowns are part of the strategy. Mid-trade adjustments are nearly always wrong. |

---

## Specific next steps for this repo

In priority order:

1. **Time-based train/test split** — modify `backtest/runner.py` to accept `--train-end YYYY-MM-DD` and report IS vs OOS metrics separately. Hold 2023+ untouched until v1 of every strategy is locked.
2. **Slippage + commission** — add `slippage_bps` and `commission_per_trade` to `Params`; apply at entry/exit fill prices.
3. **Walk-forward harness** — `backtest/walkforward.py` that runs the engine across rolling 3y-train / 6m-test windows.
4. **Parameter sweep** — `backtest/sweep.py` that varies one input at a time and outputs a heatmap; visual check for plateau vs peak.
5. **Random-entry benchmark** — `backtest/strategies/random_entry.py` matched trade count, run 1000 iterations, compare distributions.
6. **Monte Carlo on trade order** — `backtest/montecarlo.py` shuffling closed-trade lists for DD distribution.
7. **Point-in-time S&P 500 membership** — long-term aspiration; requires paid data source. Until then, accept survivorship bias in numbers.

These all live in `ROADMAP.md` under Layer 3.

---

## The mindset

Treat the backtest as **evidence**, not proof. An honest backtest with 200+ trades across a broad universe, with realistic costs, with stable parameters across nearby values, with comparable OOS / WFA stats — that's evidence the edge is real. Anything less is hope.

When in doubt: **fewer parameters, broader universe, longer history, harsher frictions**. The strategy that survives all four is the one worth trading.
