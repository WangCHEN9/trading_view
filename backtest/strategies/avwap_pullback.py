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
    # Fundamental filter
    use_fund:            bool  = True
    fund_positive_ni:    bool  = True
    fund_rev_yoy_growth: bool  = True
    fund_min_opm:        float = 0.0    # off by default; set 5+ to filter unprofitable growth
    # VWAP deviation bands (Order Flow VWAP concept): require pullback to the
    # lower sigma-band instead of just "near VWAP"
    use_vwap_bands:  bool  = False
    vwap_band_mult:  float = 2.0    # sigma multiplier for the lower band
    vwap_band_lb:    int   = 30     # rolling window for the band VWAP (recent value)
    initial_equity:  float = 100_000.0


def _anchored_vwap(df: pd.DataFrame, band_mult: float = 2.0):
    """Return (avwap, anchor_low, lower_band) series.

    Anchor = the running lowest low.  Resets cumulative stats on a new low.
    Bands use the volume-weighted variance of (price - vwap), the same method
    as TradingView's ta.vwap std-dev bands:
        var = sum(p^2 v)/sum(v) - vwap^2 ; std = sqrt(var)
    """
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    pv   = hlc3 * df["volume"]
    pv2  = hlc3 * hlc3 * df["volume"]
    avwap_arr  = np.full(len(df), np.nan)
    anchor_arr = np.full(len(df), np.nan)
    lower_arr  = np.full(len(df), np.nan)
    cum_pv = 0.0
    cum_v  = 0.0
    cum_pv2 = 0.0
    cur_anchor_low = np.inf
    for i in range(len(df)):
        lo = float(df["low"].iloc[i])
        vol = float(df["volume"].iloc[i])
        if lo < cur_anchor_low:
            cur_anchor_low = lo
            cum_pv  = float(pv.iloc[i])
            cum_v   = vol
            cum_pv2 = float(pv2.iloc[i])
        else:
            cum_pv  += float(pv.iloc[i])
            cum_v   += vol
            cum_pv2 += float(pv2.iloc[i])
        if cum_v > 0:
            vw = cum_pv / cum_v
            avwap_arr[i] = vw
            var = max(cum_pv2 / cum_v - vw * vw, 0.0)
            std = var ** 0.5
            lower_arr[i] = vw - band_mult * std
        anchor_arr[i] = cur_anchor_low
    return (pd.Series(avwap_arr, index=df.index),
            pd.Series(anchor_arr, index=df.index),
            pd.Series(lower_arr, index=df.index))


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    if len(df) < 200:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    sma50  = sma(c, 50)
    sma200 = sma(c, 200)
    sma_t  = sma(c, p.trail_ma_len)
    avwap, anchor_low, vwap_lower = _anchored_vwap(df, p.vwap_band_mult)

    uptrend     = (c > sma50) & (c > sma200) & (sma50 > sma200)
    above_avwap = c > avwap

    # Pullback detection: two modes
    if p.use_vwap_bands:
        # Rolling VWAP (recent value) + sigma band — reachable on a pullback,
        # unlike the cycle-anchored VWAP whose lower band sits far below price.
        n = p.vwap_band_lb
        hlc3 = (h + l + c) / 3
        cum_v   = v.rolling(n, min_periods=n).sum()
        rvwap   = (hlc3 * v).rolling(n, min_periods=n).sum() / cum_v
        rvar    = ((hlc3 * hlc3 * v).rolling(n, min_periods=n).sum() / cum_v) - rvwap * rvwap
        rstd    = np.sqrt(rvar.clip(lower=0))
        roll_lower = rvwap - p.vwap_band_mult * rstd
        touched_band = (l <= roll_lower)
        pullback_touched = touched_band.rolling(p.pullback_lb, min_periods=1).max().astype(bool)
    else:
        # Original: low came within p.pullback_pct of avwap in last N bars
        pct_above_avwap = (l - avwap) / avwap * 100
        pullback_touched = pct_above_avwap.rolling(p.pullback_lb, min_periods=1).min() <= p.pullback_pct

    bounce_candle = (c > o) & (c > c.shift(1)) & (c > h.shift(1))

    stop_at_entry = anchor_low * (1 - p.buffer_pct / 100)
    stop_pct      = (c - stop_at_entry) / c * 100
    stop_ok       = (stop_pct <= p.max_stop_pct) & (stop_at_entry > 0)

    if p.use_fund and fundamentals is not None and not fundamentals.empty:
        from ..fundamentals import make_pass_mask
        fund_ok = make_pass_mask(
            fundamentals, df.index,
            require_positive_ni    = p.fund_positive_ni,
            require_ni_yoy_growth  = False,
            require_rev_yoy_growth = p.fund_rev_yoy_growth,
            min_opm                = p.fund_min_opm,
        )
    else:
        fund_ok = pd.Series(True, index=df.index)

    long_signal = uptrend & above_avwap & pullback_touched & bounce_candle & stop_ok & fund_ok

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
