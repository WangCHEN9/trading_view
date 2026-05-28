"""Fetch S&P index constituents from Wikipedia (500 large / 400 mid / 600 small).

Run:  uv run python -m backtest.fetch_index --index sp600
      uv run python -m backtest.fetch_index --index sp400

Writes under universes/:
    {index}.txt       TradingView-import format (dots preserved)
    {index}_yf.txt    yfinance format (dots -> dashes)
    {index}_meta.csv  symbol, name, sector
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
import requests

ROOT     = Path(__file__).parent.parent
UNIV_DIR = ROOT / "universes"
UNIV_DIR.mkdir(exist_ok=True)

URLS = {
    "sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "sp400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "sp600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}


def fetch(index: str) -> pd.DataFrame:
    url = URLS[index]
    print(f"[fetch] {index} from {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (backtest-toolkit)"}, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    # Find the table that has a Symbol/Ticker column
    df = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any(c in ("Symbol", "Ticker symbol", "Ticker") for c in cols):
            df = t
            break
    if df is None:
        df = tables[0]
    df = df.rename(columns={
        "Ticker symbol": "symbol", "Ticker": "symbol", "Symbol": "symbol",
        "Security": "name", "Company": "name",
        "GICS Sector": "sector", "GICS sector": "sector",
    })
    keep = [c for c in ("symbol", "name", "sector") if c in df.columns]
    df = df[keep].copy()
    df["symbol"] = df["symbol"].astype(str).str.strip()
    return df.sort_values("symbol").reset_index(drop=True)


def write(index: str, df: pd.DataFrame) -> None:
    (UNIV_DIR / f"{index}.txt").write_text("\n".join(df["symbol"]) + "\n", encoding="utf-8")
    yf = df["symbol"].str.replace(".", "-", regex=False)
    (UNIV_DIR / f"{index}_yf.txt").write_text("\n".join(yf) + "\n", encoding="utf-8")
    df.to_csv(UNIV_DIR / f"{index}_meta.csv", index=False)
    print(f"[fetch] {len(df)} symbols -> universes/{index}.txt, {index}_yf.txt, {index}_meta.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, choices=list(URLS))
    args = ap.parse_args()
    write(args.index, fetch(args.index))
