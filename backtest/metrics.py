"""Performance metrics for a list of round-trip trades.

A trade is a dict with:
    entry_date, entry_price, exit_date, exit_price, qty, stop, pnl, r_multiple
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class PerfStats:
    symbol: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win: float
    avg_loss: float
    avg_r: float           # average R-multiple (winners + losers)
    expectancy: float      # $ expectancy per trade
    profit_factor: float
    net_profit: float
    net_profit_pct: float  # net profit as % of starting equity
    max_dd_pct: float

    def as_dict(self) -> dict:
        return asdict(self)


def compute(
    symbol: str,
    trades: list[dict],
    initial_equity: float,
    equity_curve: pd.Series | None = None,
) -> PerfStats:
    n = len(trades)
    if n == 0:
        return PerfStats(symbol, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                         float("nan"), 0.0, 0.0, 0.0)

    pnls = np.array([t["pnl"] for t in trades])
    rs   = np.array([t.get("r_multiple", np.nan) for t in trades])

    wins   = int((pnls > 0).sum())
    losses = int((pnls < 0).sum())
    win_rate = wins / n * 100 if n else 0.0

    avg_win  = pnls[pnls > 0].mean() if wins   else 0.0
    avg_loss = pnls[pnls < 0].mean() if losses else 0.0   # negative number

    gross_win  = pnls[pnls > 0].sum()
    gross_loss = -pnls[pnls < 0].sum()
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")

    valid_r = rs[~np.isnan(rs)]
    avg_r = float(valid_r.mean()) if len(valid_r) else 0.0

    net = float(pnls.sum())
    expectancy = net / n if n else 0.0
    net_pct = net / initial_equity * 100 if initial_equity else 0.0

    if equity_curve is not None and len(equity_curve) > 1:
        peaks = equity_curve.cummax()
        dd    = (equity_curve - peaks) / peaks * 100
        max_dd = float(dd.min())
    else:
        # Approximate max DD from cumulative trade PnL
        equity = initial_equity + pnls.cumsum()
        peaks  = np.maximum.accumulate(np.concatenate([[initial_equity], equity]))
        running = np.concatenate([[initial_equity], equity])
        dd = (running - peaks) / peaks * 100
        max_dd = float(dd.min())

    return PerfStats(
        symbol=symbol,
        trades=n,
        wins=wins,
        losses=losses,
        win_rate=round(win_rate, 1),
        avg_win=round(float(avg_win), 2),
        avg_loss=round(float(avg_loss), 2),
        avg_r=round(avg_r, 2),
        expectancy=round(expectancy, 2),
        profit_factor=round(pf, 2) if pf != float("inf") else float("inf"),
        net_profit=round(net, 2),
        net_profit_pct=round(net_pct, 1),
        max_dd_pct=round(max_dd, 1),
    )


def aggregate(stats: list[PerfStats]) -> dict:
    """Roll multiple per-symbol PerfStats into portfolio-level summary."""
    if not stats:
        return {}
    total_trades = sum(s.trades for s in stats)
    if total_trades == 0:
        return {"symbols": len(stats), "trades": 0}
    total_wins   = sum(s.wins   for s in stats)
    total_losses = sum(s.losses for s in stats)
    total_net    = sum(s.net_profit for s in stats)
    avg_r_w      = (sum(s.avg_r * s.trades for s in stats if s.trades) / total_trades)
    avg_dd       = float(np.mean([s.max_dd_pct for s in stats if s.trades]))
    profitable   = sum(1 for s in stats if s.net_profit > 0)
    return {
        "symbols":           len(stats),
        "symbols_profitable": profitable,
        "trades":            total_trades,
        "win_rate":          round(total_wins / total_trades * 100, 1),
        "avg_r":             round(avg_r_w, 2),
        "net_profit":        round(total_net, 2),
        "avg_max_dd_pct":    round(avg_dd, 1),
    }
