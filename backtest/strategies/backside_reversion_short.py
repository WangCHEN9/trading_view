"""Backside Mean-Reversion Short — daily-structure version of Assan's Strategy 2.

Thesis: a parabolic / blow-off-top stock (extended far from its mean on climax
volume) attracts trapped buyers.  After the peak, a "dead-cat bounce" back into
the supply zone that FAILS (lower high, rejection) marks the momentum shift —
short it, target reversion to the mean.

Daily approximation (intraday 5-min VWAP entry refinement not modeled):

  SETUP — climax / blow-off:
    • close > ext_pct% above the ext_ma (e.g. 40% above 50-SMA) — overextension
    • a climax-volume bar within the last climax_lb bars
      (volume > climax_vol_mult × 50-day average)

  TRIGGER — failed bounce:
    • after climax, price made at least one lower high vs the climax high
    • current bar is a rejection: close < open AND close < prior close
    • still extended above the mean (room to fall)

  STOP:  recent swing high × (1 + buffer%)
  COVER: price reverts to the mean (low <= ext_ma) OR trailing stop
  SIZING: Van Tharp 1.5% risk, 15% notional cap (short-side conservative)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma


@dataclass
class Params:
    ext_ma:          int   = 50
    ext_pct:         float = 40.0    # close must be > this % above ext_ma
    climax_lb:       int   = 10      # climax volume must be within last N bars
    climax_vol_mult: float = 2.0     # climax volume > this × 50-day avg
    setup_expiry:    int   = 15      # disarm setup if no entry within N bars of climax
    swing_lb:        int   = 10      # swing-high lookback for stop
    buffer_pct:      float = 2.0     # stop buffer above swing high
    max_stop_pct:    float = 25.0
    rvol_min:        float = 1.5     # Assan's RVOL >= 1.5 on the trigger bar
    rr_min:          float = 3.0     # minimum 3:1 reward:risk to take the trade
    risk_pct:        float = 1.5
    max_pos_pct:     float = 15.0
    initial_equity:  float = 100_000.0


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    if len(df) < params.ext_ma + 60:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    ext_ma   = sma(c, p.ext_ma)
    vol_avg  = sma(v, 50)
    rvol     = v / vol_avg
    extended = c > ext_ma * (1 + p.ext_pct / 100)
    climax   = (v > vol_avg * p.climax_vol_mult) & extended

    # ─── Stateful loop ────────────────────────────────────────────────────────
    trades: list[dict] = []
    equity = p.initial_equity
    equity_history: list[tuple[pd.Timestamp, float]] = []

    # Setup state
    armed = False
    climax_high = 0.0
    bars_since_climax = 0

    in_pos = False
    qty = 0
    entry_price = 0.0
    entry_date = None
    entry_stop = 0.0
    cur_stop = 0.0
    target = 0.0
    pending = False
    pending_stop = 0.0
    pending_target = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_o = float(o.iloc[i]); bar_h = float(h.iloc[i])
        bar_l = float(l.iloc[i]); bar_c = float(c.iloc[i])
        date = idx[i]
        ma_now = float(ext_ma.iloc[i]) if not np.isnan(ext_ma.iloc[i]) else None

        # ── Fill pending short at this bar's open ────────────────────────────
        if pending and not in_pos:
            risk_per_share = pending_stop - bar_o
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
                    target = pending_target
            pending = False

        # ── Manage open short ────────────────────────────────────────────────
        if in_pos:
            exit_price = None
            exit_reason = None
            # Stop hit (above price)
            if bar_h >= cur_stop:
                exit_price = cur_stop; exit_reason = "stop"
            # Target hit (reverted to mean)
            elif ma_now is not None and bar_l <= target:
                exit_price = target; exit_reason = "mean target"
            if exit_price is not None:
                pnl = (entry_price - exit_price) * qty
                r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
                trades.append({
                    "entry_date": entry_date, "entry_price": round(entry_price, 4),
                    "exit_date": date, "exit_price": round(exit_price, 4),
                    "qty": -qty, "stop": round(entry_stop, 4),
                    "pnl": round(pnl, 2),
                    "r_multiple": round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held": i - df.index.get_loc(entry_date),
                    "exit_reason": exit_reason,
                })
                equity += pnl
                in_pos = False
            else:
                # Trail stop down to recent swing high (only lowers)
                recent_high = float(h.iloc[max(0, i - p.swing_lb + 1):i + 1].max())
                if recent_high < cur_stop:
                    cur_stop = recent_high

        # ── Setup state machine (only when flat) ─────────────────────────────
        if not in_pos and not pending:
            if bool(climax.iloc[i]):
                armed = True
                climax_high = bar_h
                bars_since_climax = 0
            elif armed:
                bars_since_climax += 1
                climax_high = max(climax_high, bar_h)
                if bars_since_climax > p.setup_expiry:
                    armed = False

            if armed and ma_now is not None:
                lower_high   = bar_h < climax_high
                rejection    = bar_c < bar_o and bar_c < float(c.iloc[i - 1])
                still_ext    = bar_c > ma_now
                rvol_ok      = float(rvol.iloc[i]) >= p.rvol_min if not np.isnan(rvol.iloc[i]) else False
                if lower_high and rejection and still_ext:
                    swing_high = float(h.iloc[max(0, i - p.swing_lb + 1):i + 1].max())
                    stop_lvl   = swing_high * (1 + p.buffer_pct / 100)
                    tgt        = ma_now  # cover at the mean
                    risk       = stop_lvl - bar_c
                    reward     = bar_c - tgt
                    rr_ok      = risk > 0 and (reward / risk) >= p.rr_min
                    stop_pct_ok = (stop_lvl - bar_c) / bar_c * 100 <= p.max_stop_pct
                    if rvol_ok and rr_ok and stop_pct_ok:
                        pending = True
                        pending_stop = stop_lvl
                        pending_target = tgt
                        armed = False

        mtm = equity + ((entry_price - bar_c) * qty if in_pos else 0)
        equity_history.append((date, mtm))

    if in_pos:
        last = float(c.iloc[-1])
        pnl = (entry_price - last) * qty
        r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
        trades.append({
            "entry_date": entry_date, "entry_price": round(entry_price, 4),
            "exit_date": idx[-1], "exit_price": round(last, 4),
            "qty": -qty, "stop": round(entry_stop, 4),
            "pnl": round(pnl, 2),
            "r_multiple": round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
            "bars_held": len(df) - 1 - df.index.get_loc(entry_date),
            "open_at_eod": True,
        })
        equity += pnl

    eq_curve = pd.Series([x for _, x in equity_history],
                         index=[d for d, _ in equity_history], name="equity")
    return {"trades": trades, "equity_curve": eq_curve, "final_equity": equity}
