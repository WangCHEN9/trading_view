"""Parameter sensitivity sweep — vary one Params field across a list of values
and tabulate the results.  Mirrors `runner.py` but loops over the chosen field.

Usage:
    uv run python -m backtest.sweep \
        --strategy minervini_sepa --universe momentum15 --period 10y \
        --interval 1d --param vcp_ratio --values 0.5 0.6 0.7 0.8 0.9
"""
from __future__ import annotations

import argparse
import importlib
from dataclasses import replace

import pandas as pd
from tabulate import tabulate

from . import data, universe, metrics
from .runner import STRATEGY_BENCHMARKS, _fetch_benchmarks, _load_strategy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--universe", required=True)
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--period",   default="10y")
    ap.add_argument("--param",    required=True, help="Params field to vary, e.g. vcp_ratio")
    ap.add_argument("--values",   required=True, nargs="+", type=float,
                    help="Values to sweep, space-separated")
    ap.add_argument("--refresh",  action="store_true")
    args = ap.parse_args()

    strat   = _load_strategy(args.strategy)
    symbols = universe.get(args.universe)

    needed_bench = STRATEGY_BENCHMARKS.get(args.strategy, [])
    benchmarks   = _fetch_benchmarks(needed_bench, args.interval, args.period, args.refresh)
    bars         = data.load_many(symbols, interval=args.interval, period=args.period,
                                  force_refresh=args.refresh)

    rows = []
    for val in args.values:
        params = replace(strat.Params(), **{args.param: val})
        all_stats: list[metrics.PerfStats] = []
        for sym, df in bars.items():
            try:
                result = strat.backtest(df, params, benchmarks=benchmarks)
            except TypeError:
                result = strat.backtest(df, params)
            stats = metrics.compute(sym, result["trades"], params.initial_equity,
                                    equity_curve=result["equity_curve"])
            all_stats.append(stats)
        agg = metrics.aggregate(all_stats)
        rows.append({args.param: val, **agg})

    print(f"\n=== Sweep: {args.strategy} on {args.universe} — varying {args.param} ===\n")
    print(tabulate(rows, headers="keys", tablefmt="github", floatfmt=".2f"))


if __name__ == "__main__":
    main()
