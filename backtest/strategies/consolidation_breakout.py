"""Python port of scripts/consolidation_breakout.pine.

Faithfully mirrors the Pine v6 entry/exit logic:
  • Weekly TF, 20W MA + MACD(12,26,9) regime filter
  • Consolidation box = highest/lowest CLOSE over prior N weeks (excluding current)
  • Entry on breakout above resistance with vol spike, range cap, wick cap
  • Stop phase 1: c_sup + range/3  (lower end of middle third)
  • Stop phase 2: raised to bar low on MACD crossdown (only ever moves up)
  • Sizing: Van Tharp fixed-fractional (default 2.5% risk, 25% notional cap)

Fundamentals filter from the Pine version is intentionally NOT ported here —
yfinance's fundamentals are unreliable and TTM-historical data is hard to align.
We rely on the technical setup alone for the Python backtest.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ───────────────────────── Parameters (mirror Pine inputs) ──────────────────────
@dataclass
class Params:
    ma_len:       int   = 20
    consol_len:   int   = 6
    break_min:    float = 5.0    # %
    break_max:    float = 20.0   # %
    vol_spike:    float = 30.0   # % above prior bar
    natr_max:     float = 8.0    # %
    wick_max:     float = 50.0   # % of candle range
    max_stop_pct: float = 20.0   # %
    risk_pct:     float = 2.5    # % of equity risked per trade
    max_pos_pct:  float = 25.0   # ceiling on notional position size
    # Fundamental filter
    use_fund:            bool  = True
    fund_positive_ni:    bool  = False   # original Pine doesn't require — keeps technical-driven
    fund_ni_yoy_growth:  bool  = True
    fund_rev_yoy_growth: bool  = True
    fund_min_opm:        float = 10.0
    initial_equity: float = 100_000.0


# ───────────────────────── Indicators ───────────────────────────────────────────
def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    fast_ema = _ema(close, fast)
    slow_ema = _ema(close, slow)
    line     = fast_ema - slow_ema
    signal   = _ema(line, sig)
    return line, signal


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    # Wilder's smoothing == RMA == EMA with alpha=1/n.  Pine ta.atr uses RMA.
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


# ───────────────────────── Backtest engine ──────────────────────────────────────
def backtest(df: pd.DataFrame, params: Params = Params(),
             benchmarks: dict | None = None,
             fundamentals: pd.DataFrame | None = None) -> dict:
    """Run the strategy over a weekly OHLCV DataFrame.

    Returns: {"trades": [...], "equity_curve": pd.Series, "final_equity": float}
    """
    if len(df) < max(50, params.ma_len + params.consol_len + 5):
        return {"trades": [], "equity_curve": pd.Series(dtype=float),
                "final_equity": params.initial_equity}

    p = params
    o, h, l, c, v = df["open"], df["high"], df["low"], df["close"], df["volume"]

    ma20         = _sma(c, p.ma_len)
    macd_line, sig_line = _macd(c)
    natr         = _atr(df, 14) / c * 100

    # Consolidation box uses prior N bars excluding current bar — shift(1) before rolling
    c_res = c.shift(1).rolling(p.consol_len, min_periods=p.consol_len).max()
    c_sup = c.shift(1).rolling(p.consol_len, min_periods=p.consol_len).min()
    c_rng = c_res - c_sup
    stop_at_entry = c_sup + c_rng / 3

    pct_move    = (c - c.shift(1)) / c.shift(1) * 100
    wick_pct    = np.where((h - l) > 0, (h - c) / (h - l) * 100, 0.0)
    new_10wk_hi = c >= c.shift(1).rolling(10, min_periods=10).max()
    vol_ok      = v > v.shift(1) * (1 + p.vol_spike / 100)

    macd_bull   = macd_line > sig_line
    above_ma    = c > ma20
    breakout    = c > c_res
    valid_size  = (pct_move >= p.break_min) & (pct_move <= p.break_max)
    valid_wick  = wick_pct <= p.wick_max
    natr_ok     = natr < p.natr_max
    stop_ok     = (c_rng > 0) & ((c - stop_at_entry) / c * 100 <= p.max_stop_pct)

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

    long_signal = (above_ma & macd_bull & breakout & valid_size & valid_wick &
                   vol_ok & new_10wk_hi & natr_ok & stop_ok & fund_ok)

    macd_cross_dn = (macd_line < sig_line) & (macd_line.shift(1) >= sig_line.shift(1))

    # ─── Stateful iteration: Pine fills at next bar's open ─────────────────────
    trades: list[dict] = []
    equity = p.initial_equity
    equity_history: list[tuple[pd.Timestamp, float]] = []

    in_pos          = False
    qty             = 0
    entry_price     = 0.0
    entry_date: pd.Timestamp | None = None
    entry_stop      = 0.0
    cur_stop        = 0.0
    pending_entry   = False
    pending_stop_at_entry = 0.0

    idx = df.index
    for i in range(len(df)):
        bar_open  = float(o.iloc[i])
        bar_high  = float(h.iloc[i])
        bar_low   = float(l.iloc[i])
        bar_close = float(c.iloc[i])
        date      = idx[i]

        # ── 1. Fill pending entry at this bar's OPEN ─────────────────────────
        if pending_entry and not in_pos:
            risk_per_share = bar_open - pending_stop_at_entry
            if risk_per_share > 0:
                risk_dollars = equity * p.risk_pct / 100
                qty_by_risk  = int(risk_dollars / risk_per_share)
                qty_by_cap   = int(equity * p.max_pos_pct / 100 / bar_open) if bar_open > 0 else 0
                qty          = min(qty_by_risk, qty_by_cap)
                if qty > 0:
                    in_pos       = True
                    entry_price  = bar_open
                    entry_date   = date
                    entry_stop   = pending_stop_at_entry
                    cur_stop     = entry_stop
            pending_entry = False

        # ── 2. Stop management while in position (intrabar fill at stop) ─────
        if in_pos:
            if bar_low <= cur_stop:
                exit_price = cur_stop
                pnl        = (exit_price - entry_price) * qty
                r_mult     = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
                trades.append({
                    "entry_date":  entry_date,
                    "entry_price": round(entry_price, 4),
                    "exit_date":   date,
                    "exit_price":  round(exit_price, 4),
                    "qty":         qty,
                    "stop":        round(entry_stop, 4),
                    "pnl":         round(pnl, 2),
                    "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
                    "bars_held":   i - df.index.get_loc(entry_date),
                })
                equity += pnl
                in_pos = False
            else:
                # MACD crossdown on this bar → raise stop to this bar's low
                if bool(macd_cross_dn.iloc[i]):
                    if bar_low > cur_stop:
                        cur_stop = bar_low

        # ── 3. On bar close, place entry order for next bar if signal fires ─
        if (not in_pos and not pending_entry and bool(long_signal.iloc[i])
                and not np.isnan(stop_at_entry.iloc[i])):
            pending_entry         = True
            pending_stop_at_entry = float(stop_at_entry.iloc[i])

        mark_to_market = equity + ((bar_close - entry_price) * qty if in_pos else 0)
        equity_history.append((date, mark_to_market))

    # Force-close any open position at last bar's close
    if in_pos:
        last_close = float(c.iloc[-1])
        pnl = (last_close - entry_price) * qty
        r_mult = pnl / ((entry_price - entry_stop) * qty) if (entry_price - entry_stop) > 0 else np.nan
        trades.append({
            "entry_date":  entry_date,
            "entry_price": round(entry_price, 4),
            "exit_date":   idx[-1],
            "exit_price":  round(last_close, 4),
            "qty":         qty,
            "stop":        round(entry_stop, 4),
            "pnl":         round(pnl, 2),
            "r_multiple":  round(float(r_mult), 2) if not np.isnan(r_mult) else np.nan,
            "bars_held":   len(df) - 1 - df.index.get_loc(entry_date),
            "open_at_eod": True,
        })
        equity += pnl

    eq_curve = pd.Series(
        [v for _, v in equity_history],
        index=[d for d, _ in equity_history],
        name="equity",
    )

    return {"trades": trades, "equity_curve": eq_curve, "final_equity": equity}
