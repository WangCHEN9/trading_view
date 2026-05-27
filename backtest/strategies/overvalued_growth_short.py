"""Python port of scripts/overvalued_growth_short.pine — TECHNICAL-ONLY VARIANT.

⚠️ IMPORTANT LIMITATION
This Python port DOES NOT implement Layer 1 (valuation) or the
fundamental sub-rules of Layer 2 (revenue decel, neg op income).
Reason: yfinance fundamentals are unreliable and not aligned to historical
trading dates.  Only the price-derivable parts are ported:

  • Layer 2 (partial): relative strength vs IGV over 63 bars (REQUIRED here)
  • Layer 3 (full):    technical breakdown below 50/200 SMA with volume
  • Macro override:    skip if SPY > 200-DMA AND VIX < 16

This is therefore a "technical breakdown short with macro override and
relative-weakness filter" — the universe selection (passing it
hand-curated IGV/expensive-software names) substitutes for the missing
valuation filter.  For a fully-faithful backtest including Layer 1 you'd
need a point-in-time fundamentals database (FactSet, S&P Compustat).

Sizing: Van Tharp 1.5% risk, 15% notional cap (tighter than long strats).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma, atr as _atr, aligned


@dataclass
class Params:
    rs_lb:           int   = 63
    ma_slope_lb:     int   = 50
    break_lb:        int   = 20
    vol_mult:        float = 1.5
    use_macro:       bool  = True
    vix_calm:        float = 16.0
    macro_ma:        int   = 200
    atr_len:         int   = 14
    atr_mult:        float = 2.0
    swing_lb:        int   = 10
    buffer_pct:      float = 1.0
    max_stop_pct:    float = 15.0
    trail_lb:        int   = 10
    risk_pct:        float = 1.5
    max_pos_pct:     float = 15.0
    initial_equity:  float = 100_000.0


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict[str, pd.DataFrame] | None = None) -> dict:
    if len(df) < 250:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    sma50  = sma(c, 50)
    sma200 = sma(c, 200)
    atr_w  = _atr(df, p.atr_len)

    # ─── Layer 2 (price-derivable): relative strength vs IGV ──────────────────
    if benchmarks and "IGV" in benchmarks:
        igv_close = aligned(benchmarks["IGV"]["close"], df.index)
        stk_ret   = c / c.shift(p.rs_lb) - 1
        igv_ret   = igv_close / igv_close.shift(p.rs_lb) - 1
        d_rs_weak = stk_ret < igv_ret
    else:
        d_rs_weak = pd.Series(True, index=df.index)   # if no IGV, don't gate on RS

    # ─── Layer 3: technical breakdown ─────────────────────────────────────────
    t_below_both   = (c < sma50) & (c < sma200)
    t_death_cross  = sma50 < sma200
    t_ma_declining = sma200 <= sma200.shift(p.ma_slope_lb)
    t_break_low    = c < l.shift(1).rolling(p.break_lb, min_periods=p.break_lb).min()
    vol_avg        = v.rolling(50, min_periods=50).mean()
    t_vol_spike    = v > vol_avg * p.vol_mult

    technical_ok = t_below_both & t_death_cross & t_ma_declining & t_break_low & t_vol_spike

    # ─── Macro override: skip new shorts if SPY > 200-DMA AND VIX < 16 ────────
    if p.use_macro and benchmarks and "SPY" in benchmarks and "VIX" in benchmarks:
        spy_close = aligned(benchmarks["SPY"]["close"], df.index)
        spy_sma_n = aligned(benchmarks["SPY"]["close"].rolling(p.macro_ma, min_periods=p.macro_ma).mean(), df.index)
        vix_close = aligned(benchmarks["VIX"]["close"], df.index)
        macro_calm = (spy_close > spy_sma_n) & (vix_close < p.vix_calm)
        macro_ok   = ~macro_calm
    else:
        macro_ok = pd.Series(True, index=df.index)

    # ─── Stop placement + signal ──────────────────────────────────────────────
    swing_high    = h.rolling(p.swing_lb, min_periods=p.swing_lb).max()
    atr_stop      = c + atr_w * p.atr_mult
    swing_stop    = swing_high * (1 + p.buffer_pct / 100)
    stop_at_entry = np.minimum(atr_stop, swing_stop)
    stop_pct      = (stop_at_entry - c) / c * 100
    stop_ok       = stop_pct <= p.max_stop_pct

    short_signal = technical_ok & d_rs_weak & macro_ok & stop_ok

    # ─── Stateful loop ────────────────────────────────────────────────────────
    trades: list[dict] = []
    equity = p.initial_equity
    equity_history: list[tuple[pd.Timestamp, float]] = []

    in_pos = False
    qty = 0
    entry_price = 0.0
    entry_date: pd.Timestamp | None = None
    entry_stop = 0.0
    cur_stop = 0.0
    pending = False
    pending_stop = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_o = float(o.iloc[i])
        bar_h = float(h.iloc[i])
        bar_c = float(c.iloc[i])
        date  = idx[i]

        if pending and not in_pos:
            risk_per_share = pending_stop - bar_o
            if risk_per_share > 0:
                risk_dollars = equity * p.risk_pct / 100
                qty_by_risk  = int(risk_dollars / risk_per_share)
                qty_by_cap   = int(equity * p.max_pos_pct / 100 / bar_o) if bar_o > 0 else 0
                qty          = min(qty_by_risk, qty_by_cap)
                if qty > 0:
                    in_pos      = True
                    entry_price = bar_o
                    entry_date  = date
                    entry_stop  = pending_stop
                    cur_stop    = entry_stop
            pending = False

        if in_pos:
            # Stop above price; hit when bar_h >= cur_stop
            if bar_h >= cur_stop:
                exit_price = cur_stop
                pnl    = (entry_price - exit_price) * qty
                r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
                trades.append({
                    "entry_date":  entry_date,  "entry_price": round(entry_price, 4),
                    "exit_date":   date,        "exit_price":  round(exit_price, 4),
                    "qty":         -qty,        "stop":        round(entry_stop, 4),
                    "pnl":         round(pnl, 2),
                    "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held":   i - df.index.get_loc(entry_date),
                })
                equity += pnl
                in_pos = False
            else:
                # Trail: tighten stop to recent N-bar high; only lowers
                trail_hh = float(h.iloc[max(0, i - p.trail_lb + 1): i + 1].max())
                if trail_hh < cur_stop:
                    cur_stop = trail_hh
                # 50-DMA reclaim → cover at next bar open (manual close on close > sma50)
                sm = float(sma50.iloc[i])
                if not np.isnan(sm) and bar_c > sm:
                    # Cover at this bar's close (or next open if we wanted to be strict)
                    pnl    = (entry_price - bar_c) * qty
                    r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
                    trades.append({
                        "entry_date":  entry_date, "entry_price": round(entry_price, 4),
                        "exit_date":   date,       "exit_price":  round(bar_c, 4),
                        "qty":         -qty,       "stop":        round(entry_stop, 4),
                        "pnl":         round(pnl, 2),
                        "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                        "bars_held":   i - df.index.get_loc(entry_date),
                        "exit_reason": "50-DMA reclaim",
                    })
                    equity += pnl
                    in_pos = False

        if (not in_pos and not pending and bool(short_signal.iloc[i])
                and not np.isnan(stop_at_entry.iloc[i])):
            pending = True
            pending_stop = float(stop_at_entry.iloc[i])

        mtm = equity + ((entry_price - bar_c) * qty if in_pos else 0)
        equity_history.append((date, mtm))

    if in_pos:
        last = float(c.iloc[-1])
        pnl    = (entry_price - last) * qty
        r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
        trades.append({
            "entry_date":  entry_date, "entry_price": round(entry_price, 4),
            "exit_date":   idx[-1],    "exit_price":  round(last, 4),
            "qty":         -qty,       "stop":        round(entry_stop, 4),
            "pnl":         round(pnl, 2),
            "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
            "bars_held":   len(df) - 1 - df.index.get_loc(entry_date),
            "open_at_eod": True,
        })
        equity += pnl

    eq_curve = pd.Series([v for _, v in equity_history],
                         index=[d for d, _ in equity_history], name="equity")
    return {"trades": trades, "equity_curve": eq_curve, "final_equity": equity}
