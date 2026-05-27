"""Fundamental data layer using yfinance quarterly income statements.

⚠️ Important limitations:
  • yfinance quarterly data typically goes back only 4-5 years (not 10+)
  • Data is point-in-time-ISH but not strictly: restatements show as latest
  • Some small caps / recent IPOs have spotty data
  • For deep historical (2008+) or strict point-in-time backtests, paid data
    (Compustat, FactSet) is required.

For our purpose — measuring whether the fundamental filter directionally
improves results on recent data — this is good enough.  Cached to disk.

Public API:
    load_fundamentals(symbols) -> dict[symbol, pd.DataFrame]
        DataFrame columns: net_income, revenue, oper_income.  Index = report date.
    fundamental_at(fund_df, target_date) -> dict or None
        Returns the most recent quarter's data available BEFORE target_date.
        Also includes _yoy keys comparing to 4 quarters back when available.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).parent / "cache_fund"
CACHE_DIR.mkdir(exist_ok=True)

STALENESS_SECONDS = 7 * 24 * 60 * 60  # weekly refresh

# yfinance row names we care about (income statement)
ROW_ALIASES = {
    "net_income":  ["Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations"],
    "revenue":     ["Total Revenue", "Operating Revenue"],
    "oper_income": ["Operating Income", "Operating Revenue"],
}


def _cache_path(symbol: str) -> Path:
    safe = symbol.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.pkl"


def _find_row(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for name in candidates:
        if name in df.index:
            return df.loc[name]
    return None


def load_one(symbol: str, force_refresh: bool = False) -> pd.DataFrame:
    """Return a DataFrame indexed by quarterly report date with columns:
    net_income, revenue, oper_income.  Empty DataFrame on failure.
    """
    path = _cache_path(symbol)
    if path.exists() and not force_refresh:
        age = time.time() - path.stat().st_mtime
        if age < STALENESS_SECONDS:
            return pd.read_pickle(path)

    try:
        t = yf.Ticker(symbol)
        qf = t.quarterly_financials
    except Exception as e:
        print(f"[fund] {symbol}: fetch failed — {e}")
        return pd.DataFrame()

    if qf is None or qf.empty:
        # Cache empty so we don't re-fetch every run
        empty = pd.DataFrame()
        empty.to_pickle(path)
        return empty

    out_cols = {}
    for our_name, aliases in ROW_ALIASES.items():
        series = _find_row(qf, aliases)
        if series is not None:
            out_cols[our_name] = series

    if not out_cols:
        empty = pd.DataFrame()
        empty.to_pickle(path)
        return empty

    out = pd.DataFrame(out_cols).sort_index()
    out.index = pd.to_datetime(out.index)
    out.to_pickle(path)
    return out


def load_fundamentals(symbols: list[str], force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for i, s in enumerate(symbols):
        df = load_one(s, force_refresh=force_refresh)
        if not df.empty:
            out[s] = df
        if (i + 1) % 25 == 0:
            print(f"[fund] {i + 1} / {len(symbols)} fetched")
    return out


def make_pass_mask(fund_df: pd.DataFrame, bar_index: pd.DatetimeIndex,
                   require_positive_ni: bool = True,
                   require_ni_yoy_growth: bool = False,
                   require_rev_yoy_growth: bool = True,
                   min_opm: float = 0.0) -> pd.Series:
    """For each bar in `bar_index`, return True if the *most recently published*
    quarterly fundamentals passed the filter, False otherwise.

    Returns a Series aligned to bar_index.  Bars before any fundamental data is
    available default to True (na-safe — let the technicals decide).
    """
    if fund_df.empty or len(fund_df) < 5:
        # Not enough history — let signals through; technical filter handles it
        return pd.Series(True, index=bar_index)

    fund = fund_df.sort_index()

    # For each report date, compute the pass/fail of THAT quarter's fundamentals
    pass_series = pd.Series(False, index=fund.index)
    for i in range(len(fund)):
        row = fund.iloc[i]
        ok = True

        ni = row.get("net_income", float("nan"))
        if require_positive_ni and pd.notna(ni):
            ok = ok and (ni > 0)

        rev = row.get("revenue", float("nan"))
        if min_opm > 0.0:
            opi = row.get("oper_income", float("nan"))
            if pd.notna(opi) and pd.notna(rev) and rev > 0:
                opm = opi / rev * 100
                ok = ok and (opm >= min_opm)

        # YoY checks against 4 quarters back
        if i >= 4:
            row_yoy = fund.iloc[i - 4]
            if require_ni_yoy_growth and pd.notna(ni) and pd.notna(row_yoy.get("net_income", float("nan"))):
                ok = ok and (ni > row_yoy["net_income"])
            if require_rev_yoy_growth and pd.notna(rev) and pd.notna(row_yoy.get("revenue", float("nan"))):
                ok = ok and (rev > row_yoy["revenue"])

        pass_series.iloc[i] = ok

    # Forward-fill onto the bar index.  Each bar uses the most recent published
    # fundamental — that's the realistic "what was known at the time" semantic.
    aligned = pass_series.reindex(bar_index, method="ffill")
    aligned = aligned.fillna(True)  # bars before first report = pass-through
    return aligned.astype(bool)
