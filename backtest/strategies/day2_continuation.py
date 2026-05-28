"""Day 2+ Continuation (Power Play) — daily version of Assan's Strategy 3.

Thesis: a high-quality stock breaks out of a base on Day 1 on explosive volume
(a monumental catalyst), closing near the high.  Day 2 dips on profit-taking but
holds Day-1 support; buyers step back in.  Buy that first pullback to ride the
continuation.  Documented edge: post-catalyst momentum / PEAD.

Daily approximation (intraday morning-dip-then-reversal not modeled):

  DAY 1 power bar:
    • gain > min_gain %  (big move)
    • volume > vol_mult × 50-day average  (explosive)
    • close in top (1 - close_strong) of the day's range  (closed strong)
    • close > highest close of prior base_lb bars  (breakout from a base)

  ENTRY (within entry_window bars after Day 1):
    • pullback: bar low <= Day-1 close  (dipped into the pocket)
    • held structure: bar low >= Day-1 low × (1 - structure_tol%)
    • reversal: close > open  (buyers stepped in)
    → enter next bar's open

  STOP:  trigger bar's low × (1 - buffer%)
  TRAIL: highest of (rolling N-bar low) — higher-low logic, only ratchets up
  SIZING: Van Tharp 2.5% risk, 25% notional cap
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma, aligned


@dataclass
class Params:
    use_macro:       bool  = False  # regime filter tested — cut CAGR without fixing DD, default off
    macro_ma:        int   = 200
    base_lb:         int   = 40
    min_gain:        float = 8.0
    vol_mult:        float = 2.0
    close_strong:    float = 0.30   # close must be in top 30% of the bar's range
    entry_window:    int   = 3      # bars after Day 1 to look for the pullback entry
    structure_tol:   float = 3.0    # % below Day-1 low still counts as "held"
    buffer_pct:      float = 1.0
    max_stop_pct:    float = 12.0
    trail_lb:        int   = 10
    risk_pct:        float = 2.5
    max_pos_pct:     float = 25.0
    initial_equity:  float = 100_000.0


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    if len(df) < params.base_lb + 60:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    gain         = (c - c.shift(1)) / c.shift(1) * 100
    vol_avg      = sma(v, 50)
    rng          = (h - l).replace(0, np.nan)
    close_pos    = (c - l) / rng                      # 1.0 = closed at high
    base_high    = c.shift(1).rolling(p.base_lb, min_periods=p.base_lb).max()

    power_bar = (
        (gain > p.min_gain) &
        (v > vol_avg * p.vol_mult) &
        (close_pos >= (1 - p.close_strong)) &
        (c > base_high)
    )

    # Market regime: only allow entries when SPY > its 200-DMA
    if p.use_macro and benchmarks and "SPY" in benchmarks:
        spy_close = aligned(benchmarks["SPY"]["close"], df.index)
        spy_sma_n = aligned(benchmarks["SPY"]["close"].rolling(p.macro_ma, min_periods=p.macro_ma).mean(), df.index)
        macro_ok = (spy_close > spy_sma_n)
    else:
        macro_ok = pd.Series(True, index=df.index)

    # ─── Stateful loop ────────────────────────────────────────────────────────
    trades: list[dict] = []
    equity = p.initial_equity
    equity_history: list[tuple[pd.Timestamp, float]] = []

    armed = False
    d1_high = d1_low = d1_close = 0.0
    window = 0

    in_pos = False
    qty = 0
    entry_price = 0.0
    entry_date = None
    entry_stop = 0.0
    cur_stop = 0.0
    pending = False
    pending_stop = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_o = float(o.iloc[i]); bar_h = float(h.iloc[i])
        bar_l = float(l.iloc[i]); bar_c = float(c.iloc[i])
        date = idx[i]

        # ── Fill pending entry at this bar's open ────────────────────────────
        if pending and not in_pos:
            risk_per_share = bar_o - pending_stop
            if risk_per_share > 0:
                risk_dollars = equity * p.risk_pct / 100
                qty_by_risk  = int(risk_dollars / risk_per_share)
                qty_by_cap   = int(equity * p.max_pos_pct / 100 / bar_o) if bar_o > 0 else 0
                qty          = min(qty_by_risk, qty_by_cap)
                if qty > 0:
                    in_pos = True
                    entry_price = bar_o
                    entry_date = date
                    entry_stop = pending_stop
                    cur_stop = entry_stop
            pending = False

        # ── Manage open position ─────────────────────────────────────────────
        if in_pos:
            if bar_l <= cur_stop:
                pnl = (cur_stop - entry_price) * qty
                r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
                trades.append({
                    "entry_date": entry_date, "entry_price": round(entry_price, 4),
                    "exit_date": date, "exit_price": round(cur_stop, 4),
                    "qty": qty, "stop": round(entry_stop, 4),
                    "pnl": round(pnl, 2),
                    "r_multiple": round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held": i - df.index.get_loc(entry_date),
                })
                equity += pnl
                in_pos = False
            else:
                # Higher-low trail (Donchian N-bar low), only ratchets up
                trail = float(l.iloc[max(0, i - p.trail_lb + 1):i + 1].min())
                if trail > cur_stop:
                    cur_stop = trail

        # ── Setup state machine (only when flat) ─────────────────────────────
        if not in_pos and not pending:
            if bool(power_bar.iloc[i]):
                armed = True
                d1_high, d1_low, d1_close = bar_h, bar_l, bar_c
                window = 0
            elif armed:
                window += 1
                if window > p.entry_window:
                    armed = False

            if armed and window >= 1:  # entry only on bars AFTER the Day-1 bar
                pullback = bar_l <= d1_close
                held     = bar_l >= d1_low * (1 - p.structure_tol / 100)
                reversal = bar_c > bar_o
                regime_ok = bool(macro_ok.iloc[i])
                if pullback and held and reversal and regime_ok:
                    stop_lvl = bar_l * (1 - p.buffer_pct / 100)
                    stop_pct = (bar_c - stop_lvl) / bar_c * 100
                    if 0 < stop_pct <= p.max_stop_pct:
                        pending = True
                        pending_stop = stop_lvl
                        armed = False

        mtm = equity + ((bar_c - entry_price) * qty if in_pos else 0)
        equity_history.append((date, mtm))

    if in_pos:
        last = float(c.iloc[-1])
        pnl = (last - entry_price) * qty
        r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
        trades.append({
            "entry_date": entry_date, "entry_price": round(entry_price, 4),
            "exit_date": idx[-1], "exit_price": round(last, 4),
            "qty": qty, "stop": round(entry_stop, 4),
            "pnl": round(pnl, 2),
            "r_multiple": round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
            "bars_held": len(df) - 1 - df.index.get_loc(entry_date),
            "open_at_eod": True,
        })
        equity += pnl

    eq_curve = pd.Series([x for _, x in equity_history],
                         index=[d for d, _ in equity_history], name="equity")
    return {"trades": trades, "equity_curve": eq_curve, "final_equity": equity}
