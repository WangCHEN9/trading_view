"""Diagnose which Weinstein Stage 4 entry condition is blocking signals.

For each of the 10 conditions, compute the share of bars where it is True
across the SP500 universe over a chosen date range.  Then compute pairwise
AND-pass rates to find the dominant constraint.

Run:
    uv run python -m backtest.diagnose_weinstein --period 10y --start 2022-01-01 --end 2022-12-31
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from tabulate import tabulate

from . import data, universe
from .strategies._common import sma, macd, atr as _atr, aligned


def conditions_for_symbol(df: pd.DataFrame, spy: pd.DataFrame | None) -> dict[str, pd.Series]:
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    ma30       = sma(c, 30)
    ma_falling = ma30 <= ma30.shift(4)
    macd_line, sig_line = macd(c)
    natr       = _atr(df, 14) / c * 100

    c_res = c.shift(1).rolling(6, min_periods=6).max()
    c_sup = c.shift(1).rolling(6, min_periods=6).min()
    c_rng = c_res - c_sup
    stop_at_entry = c_res - c_rng / 3

    pct_drop    = (c.shift(1) - c) / c.shift(1) * 100
    lower_wick  = np.where((h - l) > 0, (c - l) / (h - l) * 100, 0.0)

    cond = {
        "below_30W":     c < ma30,
        "ma_falling":    ma_falling,
        "macd_bear":     macd_line < sig_line,
        "breakdown":     c < c_sup,
        "valid_size":    (pct_drop >= 3.0) & (pct_drop <= 20.0),
        "valid_wick":    pd.Series(lower_wick, index=df.index) <= 50.0,
        "vol_ok":        v > v.shift(1) * 1.3,
        "new_10wk_lo":   c <= c.shift(1).rolling(10, min_periods=10).min(),
        "natr_ok":       natr < 8.0,
        "stop_ok":       (c_rng > 0) & ((stop_at_entry - c) / c * 100 <= 20.0),
    }
    if spy is not None:
        spy_close = aligned(spy["close"], df.index)
        spy_sma   = aligned(spy["close"].rolling(200, min_periods=200).mean(), df.index)
        cond["macro_ok"] = ~(spy_close > spy_sma)
    return cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default="10y")
    ap.add_argument("--start",  default=None)
    ap.add_argument("--end",    default=None)
    ap.add_argument("--universe", default="sp500")
    args = ap.parse_args()

    symbols = universe.get(args.universe)
    spy = data.load("SPY", interval="1wk", period=args.period)
    bars = data.load_many(symbols, interval="1wk", period=args.period)

    # Aggregate per-condition pass counts and full-AND pass counts
    cond_names = ["below_30W","ma_falling","macd_bear","breakdown","valid_size",
                  "valid_wick","vol_ok","new_10wk_lo","natr_ok","stop_ok","macro_ok"]
    sums   = {k: 0 for k in cond_names}
    total_bars = 0
    full_pass  = 0
    sym_with_signal = 0

    for sym, df in bars.items():
        c = conditions_for_symbol(df, spy)
        mask = pd.Series(True, index=df.index)
        if args.start: mask &= df.index >= pd.Timestamp(args.start)
        if args.end:   mask &= df.index <= pd.Timestamp(args.end)
        sub_bars = int(mask.sum())
        if sub_bars == 0:
            continue
        total_bars += sub_bars

        per_sym_full = pd.Series(True, index=df.index)
        for name in cond_names:
            s = c.get(name, pd.Series(True, index=df.index))
            sums[name] += int((s & mask).sum())
            per_sym_full &= s
        sym_signal_count = int((per_sym_full & mask).sum())
        full_pass += sym_signal_count
        if sym_signal_count > 0:
            sym_with_signal += 1

    print(f"\n=== Weinstein condition pass-rates on {args.universe} "
          f"({args.start or 'all'} -> {args.end or 'all'}) ===\n")
    print(f"Total bar-symbols evaluated: {total_bars:,}")
    print(f"Full-AND signal bars:        {full_pass:,}")
    print(f"Symbols with >=1 signal bar: {sym_with_signal}\n")

    rows = []
    for name in cond_names:
        passes = sums[name]
        pct = passes / total_bars * 100 if total_bars else 0
        rows.append({"condition": name, "pass_count": passes, "pct": round(pct, 2)})
    rows.sort(key=lambda r: r["pct"])
    print(tabulate(rows, headers="keys", tablefmt="github"))

    # Identify the binding constraint(s): conditions that pass <5%
    bottlenecks = [r["condition"] for r in rows if r["pct"] < 5.0]
    print(f"\nBottleneck conditions (< 5% pass-rate): {bottlenecks}")


if __name__ == "__main__":
    main()
