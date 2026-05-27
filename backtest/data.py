"""Data layer: download OHLCV via yfinance with parquet on-disk cache.

Cached files live in backtest/cache/{symbol}_{interval}.pkl.  Re-downloads
when the cache file is older than the staleness threshold or missing.
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

STALENESS_SECONDS = 6 * 60 * 60  # re-download if cache > 6h old


def _cache_path(symbol: str, interval: str) -> Path:
    safe = symbol.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}_{interval}.pkl"


def load(
    symbol: str,
    interval: str = "1wk",
    period: str = "10y",
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Return a DataFrame with columns: open, high, low, close, volume.

    Index is timezone-naive datetime.  Empty DataFrame if download fails.
    """
    path = _cache_path(symbol, interval)
    if path.exists() and not force_refresh:
        age = time.time() - path.stat().st_mtime
        if age < STALENESS_SECONDS:
            return pd.read_pickle(path)

    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as e:
        print(f"[data] {symbol}: download failed — {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # yfinance returns MultiIndex columns when a single ticker is passed with
    # newer versions; flatten to lowercase plain names.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df.to_pickle(path)
    return df


def load_many(
    symbols: list[str],
    interval: str = "1wk",
    period: str = "10y",
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        df = load(s, interval=interval, period=period, force_refresh=force_refresh)
        if not df.empty:
            out[s] = df
        else:
            print(f"[data] {s}: skipped (no data)")
    return out
