"""SMC Structure-Break strategy — the tradeable core of Smart Money Concepts.

Distills LuxAlgo's Smart Money Concepts (BOS / CHoCH) into a real strategy.
SMC is 100% price geometry (swing structure + order blocks + FVGs); the
tradeable essence is the structure break:

  • Swing pivots define structure (last confirmed swing high / low)
  • Bullish BOS  = close breaks above the last swing high (uptrend continuation)
  • Bearish CHoCH = close breaks below the last swing low (trend flips down)

LONG on bullish BOS, stop below the last swing low (the structure that must
hold), trail by raising the stop to each new higher swing low. Exit on a
bearish structure break (close < last swing low) or the stop.

This is essentially structure-following / Donchian breakout in SMC clothing —
expect results in the same family as consolidation_breakout.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Params:
    swing_len:      int   = 10     # pivot lookback/lookforward for swings
    buffer_pct:     float = 0.5    # stop buffer below the swing low
    max_stop_pct:   float = 15.0
    rr_target:      float = 2.0    # target = entry + rr_target × risk
    require_uptrend: bool = True   # only long when structure is making higher lows
    risk_pct:       float = 2.0
    max_pos_pct:    float = 20.0
    initial_equity: float = 100_000.0


def _pivots(s_high: pd.Series, s_low: pd.Series, n: int):
    """Confirmed swing high/low: extremum of the (2n+1) window centered n bars back.
    Returns two boolean Series marking the bar where the pivot is CONFIRMED (n bars late)."""
    idx = s_high.index
    ph = pd.Series(False, index=idx)
    pl = pd.Series(False, index=idx)
    hi = s_high.values
    lo = s_low.values
    for i in range(2 * n, len(idx)):
        c = i - n
        if hi[c] == hi[i - 2 * n:i + 1].max():
            ph.iloc[i] = True
        if lo[c] == lo[i - 2 * n:i + 1].min():
            pl.iloc[i] = True
    return ph, pl


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    p = params
    n = p.swing_len
    if len(df) < 3 * n + 20:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": p.initial_equity}

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ph_conf, pl_conf = _pivots(h, l, n)

    trades: list[dict] = []
    equity = p.initial_equity
    equity_history: list[tuple[pd.Timestamp, float]] = []

    last_swing_high = np.nan       # price of most recent confirmed swing high
    last_swing_low  = np.nan       # price of most recent confirmed swing low
    higher_low      = False        # is the latest swing low above the prior one?
    prev_swing_low  = np.nan

    in_pos = False
    qty = 0
    entry_price = 0.0
    entry_date = None
    entry_stop = 0.0
    cur_stop = 0.0
    target = 0.0
    pending = False
    pending_stop = 0.0
    pending_tgt = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_o = float(o.iloc[i]); bar_h = float(h.iloc[i])
        bar_l = float(l.iloc[i]); bar_c = float(c.iloc[i])
        date = idx[i]

        # Update confirmed swing points (value is from n bars ago)
        if bool(ph_conf.iloc[i]):
            last_swing_high = float(h.iloc[i - n])
        if bool(pl_conf.iloc[i]):
            new_low = float(l.iloc[i - n])
            higher_low = (not np.isnan(prev_swing_low)) and (new_low > prev_swing_low)
            prev_swing_low = last_swing_low if not np.isnan(last_swing_low) else new_low
            last_swing_low = new_low

        # ── Fill pending entry at this bar's open ────────────────────────────
        if pending and not in_pos:
            risk_per_share = bar_o - pending_stop
            if risk_per_share > 0:
                rd = equity * p.risk_pct / 100
                qty = min(int(rd / risk_per_share),
                          int(equity * p.max_pos_pct / 100 / bar_o) if bar_o > 0 else 0)
                if qty > 0:
                    in_pos = True
                    entry_price = bar_o
                    entry_date = date
                    entry_stop = pending_stop
                    cur_stop = entry_stop
                    target = pending_tgt
            pending = False

        # ── Manage open position ─────────────────────────────────────────────
        if in_pos:
            exit_price = None
            reason = None
            if bar_l <= cur_stop:
                exit_price = cur_stop; reason = "stop"
            elif bar_h >= target:
                exit_price = target; reason = "target"
            if exit_price is not None:
                pnl = (exit_price - entry_price) * qty
                rmult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
                trades.append({
                    "entry_date": entry_date, "entry_price": round(entry_price, 4),
                    "exit_date": date, "exit_price": round(exit_price, 4),
                    "qty": qty, "stop": round(entry_stop, 4), "pnl": round(pnl, 2),
                    "r_multiple": round(float(rmult), 2) if not np.isnan(rmult) else np.nan,
                    "bars_held": i - df.index.get_loc(entry_date), "exit_reason": reason,
                })
                equity += pnl
                in_pos = False
            else:
                # Trail: raise stop to the latest higher swing low
                if not np.isnan(last_swing_low):
                    trail = last_swing_low * (1 - p.buffer_pct / 100)
                    if trail > cur_stop:
                        cur_stop = trail

        # ── Entry: bullish BOS (close breaks last swing high) ────────────────
        if (not in_pos and not pending and not np.isnan(last_swing_high)
                and not np.isnan(last_swing_low)):
            bullish_bos = bar_c > last_swing_high
            trend_ok = (not p.require_uptrend) or higher_low
            if bullish_bos and trend_ok:
                stop_lvl = last_swing_low * (1 - p.buffer_pct / 100)
                risk = bar_c - stop_lvl
                stop_pct = risk / bar_c * 100 if bar_c > 0 else 999
                if risk > 0 and stop_pct <= p.max_stop_pct:
                    pending = True
                    pending_stop = stop_lvl
                    pending_tgt = bar_c + risk * p.rr_target

        mtm = equity + ((bar_c - entry_price) * qty if in_pos else 0)
        equity_history.append((date, mtm))

    if in_pos:
        last = float(c.iloc[-1])
        pnl = (last - entry_price) * qty
        rmult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
        trades.append({
            "entry_date": entry_date, "entry_price": round(entry_price, 4),
            "exit_date": idx[-1], "exit_price": round(last, 4),
            "qty": qty, "stop": round(entry_stop, 4), "pnl": round(pnl, 2),
            "r_multiple": round(float(rmult), 2) if not np.isnan(rmult) else np.nan,
            "bars_held": len(df) - 1 - df.index.get_loc(entry_date), "open_at_eod": True,
        })
        equity += pnl

    eq = pd.Series([x for _, x in equity_history],
                   index=[d for d, _ in equity_history], name="equity")
    return {"trades": trades, "equity_curve": eq, "final_equity": equity}
