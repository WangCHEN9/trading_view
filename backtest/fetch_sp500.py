"""Fetch the current S&P 500 constituent list from Wikipedia and write
universe files for both TradingView watchlist import and Python backtest.

Run:  uv run python -m backtest.fetch_sp500

Outputs (under universes/ at repo root):
    sp500.txt              one ticker per line, TradingView-import format
                           (dots preserved; TV auto-resolves exchange)
    sp500_yf.txt           Python/yfinance format (dots → dashes)
    sp500_meta.csv         symbol, name, sector, industry  (for reference)
"""
from __future__ import annotations

from pathlib import Path

import io

import pandas as pd
import requests

ROOT       = Path(__file__).parent.parent
UNIV_DIR   = ROOT / "universes"
UNIV_DIR.mkdir(exist_ok=True)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def fetch() -> pd.DataFrame:
    print(f"[fetch] downloading from {WIKI_URL}")
    # Wikipedia 403s the default urllib UA; use requests with a real UA.
    r = requests.get(WIKI_URL, headers={"User-Agent": "Mozilla/5.0 (backtest-toolkit)"}, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[0].rename(columns={
        "Symbol":             "symbol",
        "Security":           "name",
        "GICS Sector":        "sector",
        "GICS Sub-Industry":  "industry",
    })[["symbol", "name", "sector", "industry"]]
    df["symbol"] = df["symbol"].str.strip()
    return df.sort_values("symbol").reset_index(drop=True)


def write_outputs(df: pd.DataFrame) -> None:
    tv_path   = UNIV_DIR / "sp500.txt"
    yf_path   = UNIV_DIR / "sp500_yf.txt"
    meta_path = UNIV_DIR / "sp500_meta.csv"

    # TradingView accepts plain tickers, one per line.  Dots preserved (BRK.B).
    tv_path.write_text("\n".join(df["symbol"]) + "\n", encoding="utf-8")

    # yfinance wants dashes instead of dots (BRK.B → BRK-B).
    yf_symbols = df["symbol"].str.replace(".", "-", regex=False)
    yf_path.write_text("\n".join(yf_symbols) + "\n", encoding="utf-8")

    df.to_csv(meta_path, index=False)

    print(f"[fetch] {len(df)} symbols")
    print(f"[fetch] wrote {tv_path}  (TradingView import)")
    print(f"[fetch] wrote {yf_path}  (yfinance/Python)")
    print(f"[fetch] wrote {meta_path}")
    print(f"\nSector breakdown:")
    print(df["sector"].value_counts().to_string())


if __name__ == "__main__":
    df = fetch()
    write_outputs(df)
