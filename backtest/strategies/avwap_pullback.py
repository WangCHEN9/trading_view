"""Python port of scripts/avwap_pullback.pine.

Anchored VWAP Pullback (LONG, daily). The aVWAP anchor moves when a new
lowest-low is made; otherwise it stays at the cycle low and the VWAP rises
as more bars accumulate.

Entry conditions (all true on signal bar):
  1. Trend: close > 50-DMA, close > 200-DMA, 50-DMA > 200-DMA
  2. Price > aVWAP (trend-aligned)
  3. Pullback occurred: low within `pullback_pct` of aVWAP in last `pullback_lb` bars
  4. Bounce candle: close > open AND close > prior close AND close > prior high

Stop: anchor_low × (1 − buffer%) — below the cycle low
Exit: stop hit, OR close < aVWAP (regime change), OR trail to trailing-MA
Sizing: Van Tharp 2.5% risk, 25% notional cap
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma


@dataclass
class Params:
    pullback_pct:    float = 2.0
    pullback_lb:     int   = 5
    buffer_pct:      float = 1.0
    max_stop_pct:    float = 20.0
    trail_ma_len:    int   = 20
    avwap_exit_bars: int   = 2     # require N consecutive closes below aVWAP before exit
    risk_pct:        float = 2.5
    max_pos_pct:     float = 25.0
    initial_equity:  float = 100_000.0


def _anchored_vwap(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (avwap_series, anchor_low_series).

    Anchor = the running lowest low.  Resets cumulative pv/v when a new low is set.
    """
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    pv   = hlc3 * df["volume"]
    avwap_arr  = np.full(len(df), np.nan)
    anchor_arr = np.full(len(df), np.nan)
    cum_pv = 0.0
    cum_v  = 0.0
    cur_anchor_low = np.inf
    for i in range(len(df)):
        lo = float(df["low"].iloc[i])
        vol = float(df["volume"].iloc[i])
        if lo < cur_anchor_low:
            cur_anchor_low = lo
            cum_pv = float(pv.iloc[i])
            cum_v  = vol
        else:
            cum_pv += float(pv.iloc[i])
            cum_v  += vol
        if cum_v > 0:
            avwap_arr[i] = cum_pv / cum_v
        anchor_arr[i] = cur_anchor_low
    return pd.Series(avwap_arr, index=df.index), pd.Series(anchor_arr, index=df.index)


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None) -> dict:
    if len(df) < 200:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    sma50  = sma(c, 50)
    sma200 = sma(c, 200)
    sma_t  = sma(c, p.trail_ma_len)
    avwap, anchor_low = _anchored_vwap(df)

    uptrend     = (c > sma50) & (c > sma200) & (sma50 > sma200)
    above_avwap = c > avwap

    # Pullback detection: did the low come within p.pullback_pct of avwap in last N bars?
    pct_above_avwap = (l - avwap) / avwap * 100
    pullback_touched = pct_above_avwap.rolling(p.pullback_lb, min_periods=1).min() <= p.pullback_pct

    bounce_candle = (c > o) & (c > c.shift(1)) & (c > h.shift(1))

    stop_at_entry = anchor_low * (1 - p.buffer_pct / 100)
    stop_pct      = (c - stop_at_entry) / c * 100
    stop_ok       = (stop_pct <= p.max_stop_pct) & (stop_at_entry > 0)

    long_signal = uptrend & above_avwap & pullback_touched & bounce_candle & stop_ok

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
        bar_l = float(l.iloc[i])
        bar_c = float(c.iloc[i])
        date  = idx[i]

        if pending and not in_pos:
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
            pending = False

        if in_pos:
            # Hard stop hit
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
                    "exit_reason": "stop",
                })
                equity += pnl
                in_pos = False
            else:
                # Trail to trailing MA (only ratchets up)
                sm = float(sma_t.iloc[i])
                if not np.isnan(sm) and sm > cur_stop:
                    cur_stop = sm
                # aVWAP break — require N consecutive closes below aVWAP to exit
                av = float(avwap.iloc[i])
                below_count = 0
                if not np.isnan(av):
                    for k in range(int(p.avwap_exit_bars)):
                        if i - k < 0:
                            break
                        ck = float(c.iloc[i - k])
                        avk = float(avwap.iloc[i - k])
                        if np.isnan(avk) or ck >= avk:
                            break
                        below_count += 1
                if below_count >= int(p.avwap_exit_bars):
                    pnl    = (bar_c - entry_price) * qty
                    r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
                    trades.append({
                        "entry_date":  entry_date, "entry_price": round(entry_price, 4),
                        "exit_date":   date,       "exit_price":  round(bar_c, 4),
                        "qty":         qty,        "stop":        round(entry_stop, 4),
                        "pnl":         round(pnl, 2),
                        "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                        "bars_held":   i - df.index.get_loc(entry_date),
                        "exit_reason": "aVWAP break",
                    })
                    equity += pnl
                    in_pos = False

        if (not in_pos and not pending and bool(long_signal.iloc[i])
                and not np.isnan(stop_at_entry.iloc[i])):
            pending = True
            pending_stop = float(stop_at_entry.iloc[i])

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
