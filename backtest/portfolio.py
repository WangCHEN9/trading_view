"""Portfolio-mode backtest: single equity pool shared across symbols, with a
cap on concurrent positions.  Iterates the date axis, not the symbol axis.

The N parallel single-symbol simulations in `runner.py` overstate $-returns
because each symbol independently risks 2.5% of its OWN $100K.  In real life
a single account allocates 2.5% of the SHARED equity, and capacity is finite
(typically 5–8 concurrent positions).  This module models that constraint.

Usage:
    uv run python -m backtest.portfolio \
        --strategy consolidation_breakout --universe sp500 \
        --period 10y --interval 1wk --max-positions 6 \
        --slippage-bps 5 --commission 1

The strategy module must expose Params + a vectorized signal computation.
For now we extract signals by running each strategy's backtest()
independently to get the `trades` list, then RE-SIMULATE the trades
against a shared equity pool with the position cap.
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from . import data, universe, metrics
from . import fundamentals as fund_lib
from .runner import STRATEGY_BENCHMARKS, STRATEGY_USES_FUNDAMENTALS, _fetch_benchmarks


RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--universe", required=True)
    ap.add_argument("--interval", default="1wk")
    ap.add_argument("--period",   default="10y")
    ap.add_argument("--refresh",  action="store_true")
    ap.add_argument("--initial-equity", type=float, default=100_000.0)
    ap.add_argument("--max-positions",  type=int,   default=6,
                    help="Max concurrent open positions (default 6)")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end",   default=None)
    ap.add_argument("--slippage-bps", type=float, default=0.0)
    ap.add_argument("--commission",   type=float, default=0.0)
    ap.add_argument("--no-fund", action="store_true")
    args = ap.parse_args()

    symbols = universe.get(args.universe)
    print(f"\n=== Portfolio backtest: {args.strategy} on {len(symbols)} symbols "
          f"({args.interval}, max {args.max_positions} concurrent) ===\n")

    strat = importlib.import_module(f"backtest.strategies.{args.strategy}")
    params = strat.Params(initial_equity=args.initial_equity)

    needed_bench = STRATEGY_BENCHMARKS.get(args.strategy, [])
    benchmarks   = _fetch_benchmarks(needed_bench, args.interval, args.period, args.refresh)
    bars         = data.load_many(symbols, interval=args.interval, period=args.period,
                                  force_refresh=args.refresh)

    fundamentals_by_sym: dict[str, "pd.DataFrame"] = {}
    fund_enabled = (args.strategy in STRATEGY_USES_FUNDAMENTALS) and not args.no_fund
    if fund_enabled:
        print(f"[portfolio] fetching fundamentals for {len(symbols)} symbols...")
        fundamentals_by_sym = fund_lib.load_fundamentals(symbols)
        print(f"[portfolio] fundamental coverage: {len(fundamentals_by_sym)} / {len(symbols)}")

    # ─── Step 1: collect all candidate trades per symbol ──────────────────────
    all_candidates: list[dict] = []
    for sym, df in bars.items():
        sym_fund = fundamentals_by_sym.get(sym)
        try:
            result = strat.backtest(df, params, benchmarks=benchmarks, fundamentals=sym_fund)
        except TypeError:
            try:
                result = strat.backtest(df, params, benchmarks=benchmarks)
            except TypeError:
                result = strat.backtest(df, params)
        for t in result["trades"]:
            t["symbol"] = sym
            all_candidates.append(t)

    # Apply date filter to entries
    if args.start:
        s = pd.Timestamp(args.start)
        all_candidates = [t for t in all_candidates if t["entry_date"] >= s]
    if args.end:
        e = pd.Timestamp(args.end)
        all_candidates = [t for t in all_candidates if t["entry_date"] <= e]

    print(f"[portfolio] candidate trades from independent sims: {len(all_candidates)}")

    # ─── Step 2: shared-equity simulation with concurrent-position cap ────────
    candidates = sorted(all_candidates, key=lambda t: t["entry_date"])
    equity = args.initial_equity
    open_positions: list[dict] = []          # active trades, sorted by exit_date
    executed_trades: list[dict] = []
    rejected = 0
    slip = args.slippage_bps / 10_000.0

    # We need to know per-share risk to compute single-account size.  Use the
    # recorded (entry_price, stop) from the independent sim — they reflect the
    # strategy's stop placement that bar.
    cand_idx = 0
    # Iterate on a unified date timeline so we close exits before checking entries
    all_dates = sorted(set(t["entry_date"] for t in candidates) |
                       set(t["exit_date"]  for t in candidates))

    for date in all_dates:
        # 1) Close positions that exit today (or before)
        still_open = []
        for pos in open_positions:
            if pos["exit_date"] <= date:
                # Apply position-level friction here in case it wasn't yet
                pnl = pos["pnl_resized"]
                equity += pnl
                executed_trades.append(pos)
            else:
                still_open.append(pos)
        open_positions = still_open

        # 2) Process new entries on this date — pick top-N if multiple fire
        new_today = [t for t in candidates if t["entry_date"] == date]
        # Sort by some "quality" proxy; absent a real ranker, use smaller stop_pct first (tighter risk)
        new_today.sort(key=lambda t: abs((t["entry_price"] - t["stop"]) / t["entry_price"]))

        for t in new_today:
            if len(open_positions) >= args.max_positions:
                rejected += 1
                continue
            # Resize position to current shared equity at the trade's risk%
            qty_orig    = abs(t["qty"])
            risk_per_sh = (t["entry_price"] - t["stop"]) if t["qty"] > 0 \
                          else (t["stop"] - t["entry_price"])
            if risk_per_sh <= 0:
                rejected += 1
                continue
            risk_dollars = equity * params.risk_pct / 100
            new_qty = int(risk_dollars / risk_per_sh)
            # Apply notional cap
            cap_qty = int(equity * params.max_pos_pct / 100 / t["entry_price"]) \
                      if t["entry_price"] > 0 else 0
            new_qty = min(new_qty, cap_qty)
            if new_qty <= 0:
                rejected += 1
                continue

            # Rescale pnl proportionally
            scale = new_qty / qty_orig if qty_orig else 0
            scaled_pnl = t["pnl"] * scale
            # Apply frictions
            friction = slip * (t["entry_price"] + t["exit_price"]) * new_qty \
                     + 2 * args.commission
            scaled_pnl -= friction

            open_positions.append({
                "symbol":       t["symbol"],
                "entry_date":   t["entry_date"],
                "exit_date":    t["exit_date"],
                "entry_price":  t["entry_price"],
                "exit_price":   t["exit_price"],
                "qty":          new_qty if t["qty"] > 0 else -new_qty,
                "stop":         t["stop"],
                "pnl_resized":  round(scaled_pnl, 2),
                "r_multiple":   round(scaled_pnl / (risk_per_sh * new_qty), 2)
                                if risk_per_sh > 0 else float("nan"),
            })

    # Close any positions still open at end of horizon (use their pnl as-is)
    for pos in open_positions:
        equity += pos["pnl_resized"]
        executed_trades.append(pos)

    # ─── Step 3: aggregate ────────────────────────────────────────────────────
    df_trades = pd.DataFrame(executed_trades)
    if df_trades.empty:
        print("[portfolio] no executed trades")
        return

    df_trades = df_trades.sort_values("exit_date").reset_index(drop=True)

    # ─── Equity curve at each trade close (realized basis) ───────────────────
    # Group by exit_date so multiple closes on the same date sum into one step
    daily_pnl = df_trades.groupby("exit_date")["pnl_resized"].sum().sort_index()
    equity_curve = pd.Series(
        index=pd.to_datetime(daily_pnl.index),
        data=(args.initial_equity + daily_pnl.cumsum()).values,
        name="equity"
    )
    # Peak-to-trough max drawdown from this realized series
    peaks  = equity_curve.cummax()
    dd     = (equity_curve - peaks) / peaks * 100
    max_dd = float(dd.min())

    # Daily-equivalent returns for Sharpe.  Approx: forward-fill equity to a
    # daily index covering the period, then pct_change.
    period_start = equity_curve.index.min()
    period_end   = equity_curve.index.max()
    daily_idx = pd.date_range(period_start, period_end, freq="B")
    daily_eq  = equity_curve.reindex(daily_idx, method="ffill").bfill()
    daily_ret = daily_eq.pct_change().dropna()
    sharpe    = (daily_ret.mean() / daily_ret.std() * (252 ** 0.5)) if daily_ret.std() > 0 else float("nan")
    neg_ret   = daily_ret[daily_ret < 0]
    sortino   = (daily_ret.mean() / neg_ret.std() * (252 ** 0.5)) if len(neg_ret) > 1 and neg_ret.std() > 0 else float("nan")

    # ─── SPY buy-and-hold over the same period ───────────────────────────────
    spy_df = data.load("SPY", interval=args.interval, period=args.period)
    spy_slice = spy_df.loc[period_start:period_end]
    spy_ret_total = float(spy_slice["close"].iloc[-1] / spy_slice["close"].iloc[0] - 1)
    spy_final = args.initial_equity * (1 + spy_ret_total)
    spy_daily = spy_slice["close"].pct_change().dropna()
    spy_peaks = spy_slice["close"].cummax()
    spy_dd_series = (spy_slice["close"] - spy_peaks) / spy_peaks * 100
    spy_max_dd = float(spy_dd_series.min())
    spy_sharpe = (spy_daily.mean() / spy_daily.std() * (252 ** 0.5)) if spy_daily.std() > 0 else float("nan")
    spy_neg = spy_daily[spy_daily < 0]
    spy_sortino = (spy_daily.mean() / spy_neg.std() * (252 ** 0.5)) if len(spy_neg) > 1 and spy_neg.std() > 0 else float("nan")

    n   = len(df_trades)
    wins   = int((df_trades["pnl_resized"] > 0).sum())
    losses = int((df_trades["pnl_resized"] < 0).sum())
    wr = wins / n * 100
    avg_r = df_trades["r_multiple"].mean()
    net = float(df_trades["pnl_resized"].sum())
    pf = (df_trades.loc[df_trades["pnl_resized"] > 0, "pnl_resized"].sum() /
          -df_trades.loc[df_trades["pnl_resized"] < 0, "pnl_resized"].sum()) \
         if (df_trades["pnl_resized"] < 0).any() else float("inf")
    years = (period_end - period_start).days / 365.25
    cagr  = ((equity / args.initial_equity) ** (1 / years) - 1) * 100 if years > 0 else 0
    spy_cagr = ((1 + spy_ret_total) ** (1 / years) - 1) * 100 if years > 0 else 0

    print(f"\n--- Strategy ---")
    print(tabulate([
        ["Initial equity",   f"${args.initial_equity:,.0f}"],
        ["Final equity",     f"${equity:,.0f}"],
        ["Net profit",       f"${net:,.0f}"],
        ["CAGR",             f"{cagr:.2f}%"],
        ["Max drawdown",     f"{max_dd:.1f}%"],
        ["Sharpe",           f"{sharpe:.2f}"],
        ["Sortino",          f"{sortino:.2f}"],
        ["Years",            f"{years:.1f}"],
        ["Executed trades",  n],
        ["Rejected (cap)",   rejected],
        ["Acceptance rate",  f"{n / (n + rejected) * 100:.1f}%" if (n + rejected) else "n/a"],
        ["Win rate",         f"{wr:.1f}%"],
        ["Avg R",            f"{avg_r:.2f}"],
        ["Profit factor",    f"{pf:.2f}" if pf != float('inf') else "inf"],
        ["Max concurrent",   args.max_positions],
    ], tablefmt="github"))

    print(f"\n--- SPY buy-and-hold (same period) ---")
    print(tabulate([
        ["Final equity",  f"${spy_final:,.0f}"],
        ["CAGR",          f"{spy_cagr:.2f}%"],
        ["Max drawdown",  f"{spy_max_dd:.1f}%"],
        ["Sharpe",        f"{spy_sharpe:.2f}"],
        ["Sortino",       f"{spy_sortino:.2f}"],
    ], tablefmt="github"))

    print(f"\n--- Verdict ---")
    print(tabulate([
        ["CAGR delta",        f"{cagr - spy_cagr:+.2f} pp"],
        ["Max DD delta",      f"{max_dd - spy_max_dd:+.1f} pp",
                              "(strategy better)" if max_dd > spy_max_dd else "(strategy worse)"],
        ["Sharpe delta",      f"{sharpe - spy_sharpe:+.2f}",
                              "(strategy better)" if sharpe > spy_sharpe else "(strategy worse)"],
        ["Sortino delta",     f"{sortino - spy_sortino:+.2f}",
                              "(strategy better)" if sortino > spy_sortino else "(strategy worse)"],
    ], tablefmt="github"))

    out = RESULTS_DIR / f"portfolio_{args.strategy}_{args.universe}.csv"
    df_trades.to_csv(out, index=False)
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
