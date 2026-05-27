"""CLI runner.  Usage:

    uv run python -m backtest.runner --strategy consolidation_breakout --universe large25
    uv run python -m backtest.runner --strategy consolidation_breakout --symbols AAPL MSFT NVDA --period 5y

Outputs a per-symbol metrics table to stdout and writes:
    backtest/results/{strategy}_{universe}_summary.csv
    backtest/results/{strategy}_{universe}_trades.csv
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from . import data, universe, metrics


RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Strategies that need benchmark series (symbol → benchmark dict keys)
STRATEGY_BENCHMARKS: dict[str, list[str]] = {
    "consolidation_breakout":   [],
    "minervini_sepa":           ["SPY"],
    "weinstein_stage4_short":   ["SPY"],
    "overvalued_growth_short":  ["SPY", "IGV", "VIX"],
}

BENCHMARK_TICKERS = {
    "SPY": "SPY",
    "IGV": "IGV",
    "VIX": "^VIX",
}


def _load_strategy(name: str):
    mod = importlib.import_module(f"backtest.strategies.{name}")
    if not hasattr(mod, "backtest"):
        raise SystemExit(f"Strategy module '{name}' missing backtest() entry point")
    return mod


def _fetch_benchmarks(needed: list[str], interval: str, period: str,
                      refresh: bool) -> dict[str, "pd.DataFrame"]:
    out = {}
    for name in needed:
        ticker = BENCHMARK_TICKERS[name]
        df = data.load(ticker, interval=interval, period=period, force_refresh=refresh)
        if df.empty:
            print(f"[runner] WARNING: benchmark {name} ({ticker}) is empty; strategy will degrade")
        else:
            out[name] = df
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True,
                    help="strategy module name under backtest.strategies (e.g. consolidation_breakout)")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--universe", help="named universe from backtest.universe")
    grp.add_argument("--symbols", nargs="+", help="explicit symbol list")
    ap.add_argument("--interval", default="1wk", help="yfinance interval (1d, 1wk)")
    ap.add_argument("--period",   default="10y", help="yfinance period (5y, 10y, max)")
    ap.add_argument("--refresh",  action="store_true", help="force-redownload data")
    ap.add_argument("--initial-equity", type=float, default=100_000.0)
    ap.add_argument("--start", help="YYYY-MM-DD — slice bars to start on/after this date (after download)")
    ap.add_argument("--end",   help="YYYY-MM-DD — slice bars to end on/before this date (after download)")
    args = ap.parse_args()

    symbols = universe.get(args.universe) if args.universe else args.symbols
    label   = args.universe or "_".join(symbols)

    print(f"\n=== Backtest: {args.strategy}  on  {len(symbols)} symbols  ({args.interval}, {args.period}) ===\n")

    strat = _load_strategy(args.strategy)
    params = strat.Params(initial_equity=args.initial_equity)

    needed_bench = STRATEGY_BENCHMARKS.get(args.strategy, [])
    benchmarks   = _fetch_benchmarks(needed_bench, args.interval, args.period, args.refresh)
    if needed_bench:
        print(f"[runner] fetched benchmarks: {list(benchmarks)}")

    all_stats:  list[metrics.PerfStats] = []
    all_trades: list[dict]              = []

    bars = data.load_many(symbols, interval=args.interval, period=args.period,
                          force_refresh=args.refresh)

    start_ts = pd.Timestamp(args.start) if args.start else None
    end_ts   = pd.Timestamp(args.end)   if args.end   else None
    if start_ts or end_ts:
        print(f"[runner] filtering trades to entries in [{start_ts}, {end_ts}] (full history kept for warmup)")

    for sym, df in bars.items():
        # Pass benchmarks if the strategy signature accepts them
        try:
            result = strat.backtest(df, params, benchmarks=benchmarks)
        except TypeError:
            result = strat.backtest(df, params)

        # Filter trades to those that entered within the requested window
        trades = result["trades"]
        if start_ts or end_ts:
            trades = [t for t in trades
                      if (start_ts is None or t["entry_date"] >= start_ts) and
                         (end_ts   is None or t["entry_date"] <= end_ts)]

        for t in trades:
            t["symbol"] = sym
        all_trades.extend(trades)
        stats = metrics.compute(sym, trades, params.initial_equity,
                                equity_curve=result["equity_curve"])
        all_stats.append(stats)

    # Per-symbol table
    rows = [s.as_dict() for s in all_stats]
    df_stats = pd.DataFrame(rows).sort_values("net_profit", ascending=False)
    print(tabulate(df_stats, headers="keys", tablefmt="github",
                   showindex=False, floatfmt=".2f"))

    # Portfolio aggregate
    agg = metrics.aggregate(all_stats)
    print("\n--- Portfolio aggregate ---")
    print(tabulate([[k, v] for k, v in agg.items()], tablefmt="github"))

    # Write CSVs
    summary_path = RESULTS_DIR / f"{args.strategy}_{label}_summary.csv"
    trades_path  = RESULTS_DIR / f"{args.strategy}_{label}_trades.csv"
    df_stats.to_csv(summary_path, index=False)
    if all_trades:
        pd.DataFrame(all_trades).to_csv(trades_path, index=False)
    print(f"\nWrote: {summary_path}")
    print(f"Wrote: {trades_path}")


if __name__ == "__main__":
    main()
