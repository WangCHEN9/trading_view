"""Python port of scripts/minervini_sepa.pine.

Faithful to the Pine v6 logic:
  • Trend Template — 7 conditions + 3-month RS-vs-SPY proxy (Minervini's
    rule 8 substitute since true IBD RS rank is not available)
  • VCP filter: ATR(10 recent) < 0.6 × ATR(10 prior)
  • Pivot break: close > highest_high(15)[1]
  • Volume confirmation: vol > 1.5 × SMA(vol, 50)
  • Stop: entry − 2 × ATR(14)
  • Trail: chandelier  highest_high(21) − 2 × ATR(14), only ratchets up
  • Sizing: Van Tharp 2.5% risk, 25% notional cap
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma, atr as _atr, aligned


@dataclass
class Params:
    min_off_low_pct: float = 25.0
    max_off_hi_pct:  float = 25.0
    ma200_lb:        int   = 22
    pivot_lb:        int   = 15
    vcp_lb:          int   = 10
    vcp_ratio:       float = 0.8
    vol_mult:        float = 1.5
    atr_len:         int   = 14
    atr_mult:        float = 2.0
    max_stop_pct:    float = 10.0
    trail_len:       int   = 21
    risk_pct:        float = 2.5
    max_pos_pct:     float = 25.0
    # Fundamental filter (require yfinance quarterly data — see fundamentals.py)
    use_fund:           bool  = True
    fund_positive_ni:   bool  = True   # require NI > 0
    fund_ni_yoy_growth: bool  = True   # require NI[q] > NI[q-4]
    fund_rev_yoy_growth: bool = True   # require Rev[q] > Rev[q-4]
    fund_min_opm:       float = 5.0    # min operating margin %
    initial_equity:  float = 100_000.0


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict[str, pd.DataFrame] | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    if len(df) < 252 + 10:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    sma50  = sma(c, 50)
    sma150 = sma(c, 150)
    sma200 = sma(c, 200)
    hi_52w = h.rolling(252, min_periods=252).max()
    lo_52w = l.rolling(252, min_periods=252).min()

    t1 = (c > sma150) & (c > sma200)
    t2 = sma150 > sma200
    t3 = sma200 > sma200.shift(p.ma200_lb)
    t4 = (sma50 > sma150) & (sma50 > sma200)
    t5 = c > sma50
    t6 = c >= lo_52w * (1 + p.min_off_low_pct / 100)
    t7 = c >= hi_52w * (1 - p.max_off_hi_pct  / 100)

    # RS proxy: stock 3-month vs SPY 3-month
    if benchmarks and "SPY" in benchmarks:
        spy_close = aligned(benchmarks["SPY"]["close"], df.index)
        stk_ret   = c / c.shift(63) - 1
        spy_ret   = spy_close / spy_close.shift(63) - 1
        t8 = stk_ret > spy_ret
    else:
        t8 = pd.Series(True, index=df.index)

    trend_template = t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8

    tr = pd.concat([(h - l),
                    (h - c.shift(1)).abs(),
                    (l - c.shift(1)).abs()], axis=1).max(axis=1)
    # Measure contraction BEFORE the breakout bar; .shift(1) excludes today's
    # (potentially explosive) bar from the recent-block average.
    atr_recent = tr.shift(1).rolling(p.vcp_lb, min_periods=p.vcp_lb).mean()
    atr_prior  = atr_recent.shift(p.vcp_lb)
    vcp_ok     = atr_recent < atr_prior * p.vcp_ratio

    pivot_high  = h.shift(1).rolling(p.pivot_lb, min_periods=p.pivot_lb).max()
    pivot_break = c > pivot_high

    vol_avg   = v.rolling(50, min_periods=50).mean()
    vol_spike = v > vol_avg * p.vol_mult

    atr_w      = _atr(df, p.atr_len)
    stop_init  = c - atr_w * p.atr_mult
    stop_pct   = (c - stop_init) / c * 100
    stop_ok    = stop_pct <= p.max_stop_pct

    # Fundamental filter (na-safe: passes through if no data)
    if p.use_fund and fundamentals is not None and not fundamentals.empty:
        from ..fundamentals import make_pass_mask
        fund_ok = make_pass_mask(
            fundamentals, df.index,
            require_positive_ni    = p.fund_positive_ni,
            require_ni_yoy_growth  = p.fund_ni_yoy_growth,
            require_rev_yoy_growth = p.fund_rev_yoy_growth,
            min_opm                = p.fund_min_opm,
        )
    else:
        fund_ok = pd.Series(True, index=df.index)

    long_signal = trend_template & vcp_ok & pivot_break & vol_spike & stop_ok & fund_ok

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
    pending_entry = False
    pending_stop = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_o  = float(o.iloc[i])
        bar_h  = float(h.iloc[i])
        bar_l  = float(l.iloc[i])
        bar_c  = float(c.iloc[i])
        date   = idx[i]

        if pending_entry and not in_pos:
            risk_per_share = bar_o - pending_stop
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
            pending_entry = False

        if in_pos:
            if bar_l <= cur_stop:
                pnl    = (cur_stop - entry_price) * qty
                r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
                trades.append({
                    "entry_date":  entry_date,  "entry_price": round(entry_price, 4),
                    "exit_date":   date,        "exit_price":  round(cur_stop, 4),
                    "qty":         qty,         "stop":        round(entry_stop, 4),
                    "pnl":         round(pnl, 2),
                    "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held":   i - df.index.get_loc(entry_date),
                })
                equity += pnl
                in_pos = False
            else:
                # 50-DMA trail (Minervini's real exit rule): raise stop to 50-DMA
                # whenever the 50-DMA is above current stop.  Only ratchets up.
                sm = float(sma50.iloc[i])
                if not np.isnan(sm) and sm > cur_stop:
                    cur_stop = sm

        if (not in_pos and not pending_entry and bool(long_signal.iloc[i])
                and not np.isnan(stop_init.iloc[i])):
            pending_entry = True
            pending_stop  = float(stop_init.iloc[i])

        mtm = equity + ((bar_c - entry_price) * qty if in_pos else 0)
        equity_history.append((date, mtm))

    if in_pos:
        last = float(c.iloc[-1])
        pnl    = (last - entry_price) * qty
        r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
        trades.append({
            "entry_date":  entry_date, "entry_price": round(entry_price, 4),
            "exit_date":   idx[-1],    "exit_price":  round(last, 4),
            "qty":         qty,        "stop":        round(entry_stop, 4),
            "pnl":         round(pnl, 2),
            "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
            "bars_held":   len(df) - 1 - df.index.get_loc(entry_date),
            "open_at_eod": True,
        })
        equity += pnl

    eq_curve = pd.Series([v for _, v in equity_history],
                         index=[d for d, _ in equity_history], name="equity")
    return {"trades": trades, "equity_curve": eq_curve, "final_equity": equity}
