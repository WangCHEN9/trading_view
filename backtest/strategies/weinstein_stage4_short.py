"""Python port of scripts/weinstein_stage4_short.pine.

Mirror of consolidation_breakout: same machinery, opposite direction.
  • Weekly TF, 30W MA flat or falling
  • Distribution box = highest/lowest close over prior N weeks
  • Entry on breakdown below support with volume confirmation
  • Stop: c_res − range/3  (above price for shorts)
  • Trail: tighten on MACD bullish cross — set stop to that bar's high
  • Stop only ever moves DOWN (closer to price) for shorts
  • Sizing: Van Tharp 2.5% risk, 25% notional cap
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ._common import sma, macd, atr as _atr, aligned


@dataclass
class Params:
    ma_len:         int   = 30
    ma_slope_lb:    int   = 4
    consol_len:     int   = 6
    break_min:      float = 3.0
    break_max:      float = 20.0
    vol_spike:      float = 30.0
    natr_max:       float = 8.0
    wick_max:       float = 50.0
    max_stop_pct:   float = 20.0
    risk_pct:       float = 2.5
    max_pos_pct:    float = 25.0
    use_macro:      bool  = True
    macro_ma:       int   = 40    # weeks (~200 days). Original default of 200 weeks (~4y) was wrong for weekly TF.
    initial_equity: float = 100_000.0


def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None) -> dict:
    if len(df) < params.ma_len + params.consol_len + 5:
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    ma         = sma(c, p.ma_len)
    ma_falling = ma <= ma.shift(p.ma_slope_lb)
    macd_line, sig_line = macd(c)
    natr       = _atr(df, 14) / c * 100
    macd_cross_up = (macd_line > sig_line) & (macd_line.shift(1) <= sig_line.shift(1))

    c_res = c.shift(1).rolling(p.consol_len, min_periods=p.consol_len).max()
    c_sup = c.shift(1).rolling(p.consol_len, min_periods=p.consol_len).min()
    c_rng = c_res - c_sup
    stop_at_entry = c_res - c_rng / 3

    below_ma     = c < ma
    macd_bear    = macd_line < sig_line
    breakdown    = c < c_sup
    pct_drop     = (c.shift(1) - c) / c.shift(1) * 100
    valid_size   = (pct_drop >= p.break_min) & (pct_drop <= p.break_max)
    lower_wick   = np.where((h - l) > 0, (c - l) / (h - l) * 100, 0.0)
    valid_wick   = lower_wick <= p.wick_max
    vol_ok       = v > v.shift(1) * (1 + p.vol_spike / 100)
    new_10wk_lo  = c <= c.shift(1).rolling(10, min_periods=10).min()
    natr_ok      = natr < p.natr_max
    stop_ok      = (c_rng > 0) & ((stop_at_entry - c) / c * 100 <= p.max_stop_pct)

    # Macro filter: skip new shorts when SPY is above its 200-DMA
    if p.use_macro and benchmarks and "SPY" in benchmarks:
        spy_close = aligned(benchmarks["SPY"]["close"], df.index)
        spy_sma_n = aligned(benchmarks["SPY"]["close"].rolling(p.macro_ma, min_periods=p.macro_ma).mean(), df.index)
        macro_ok  = ~(spy_close > spy_sma_n)
    else:
        macro_ok = pd.Series(True, index=df.index)

    short_signal = (below_ma & ma_falling & breakdown & valid_size & valid_wick &
                    vol_ok & new_10wk_lo & natr_ok & macd_bear & stop_ok & macro_ok)

    # ─── Stateful loop (short direction) ──────────────────────────────────────
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

        # Fill pending short at this bar's open
        if pending and not in_pos:
            risk_per_share = pending_stop - bar_o     # stop above entry for shorts
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
            # Stop hit: short stop is ABOVE price; trigger when bar high >= cur_stop
            if bar_h >= cur_stop:
                pnl    = (entry_price - cur_stop) * qty     # short pnl = entry − exit
                r_mult = pnl / ((entry_stop - entry_price) * qty) if (entry_stop - entry_price) > 0 else np.nan
                trades.append({
                    "entry_date":  entry_date,  "entry_price": round(entry_price, 4),
                    "exit_date":   date,        "exit_price":  round(cur_stop, 4),
                    "qty":         -qty,        "stop":        round(entry_stop, 4),
                    "pnl":         round(pnl, 2),
                    "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held":   i - df.index.get_loc(entry_date),
                })
                equity += pnl
                in_pos = False
            else:
                # MACD bullish cross → tighten stop down to this bar's high
                if bool(macd_cross_up.iloc[i]):
                    if bar_h < cur_stop:
                        cur_stop = bar_h

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
