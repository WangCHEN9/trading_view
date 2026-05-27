"""Shared indicator helpers used across strategy ports."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    line   = ema(close, fast) - ema(close, slow)
    signal = ema(line, sig)
    return line, signal


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev = c.shift(1)
    tr = pd.concat([(h - l), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def aligned(target: pd.Series, on: pd.DatetimeIndex) -> pd.Series:
    """Forward-fill a benchmark series onto the target index. Returns NaN where benchmark has no prior data."""
    return target.reindex(on, method="ffill")
