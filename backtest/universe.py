"""Predefined symbol universes.

Small dev lists are inlined.  Large universes (S&P 500) are read from
universes/*.txt — refresh with:  uv run python -m backtest.fetch_sp500
"""
from pathlib import Path

_UNIV_DIR = Path(__file__).parent.parent / "universes"


def _read_list(filename: str) -> list[str]:
    path = _UNIV_DIR / filename
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]

# 25 large-cap US names across sectors — starter universe for development.
LARGE_CAP_25 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "AVGO", "AMD", "CRM", "ADBE", "ORCL",
    "JPM", "V", "MA", "BRK-B",
    "UNH", "LLY", "JNJ",
    "WMT", "COST", "HD",
    "XOM", "CVX",
    "CAT",
]

# IBD-style breakout candidates (well-known momentum names; rotate over time)
MOMENTUM_15 = [
    "NVDA", "AVGO", "AMD", "PLTR", "SMCI",
    "META", "GOOGL", "MSFT",
    "TSLA", "NFLX",
    "LLY", "NOW",
    "ANET", "CRWD", "DDOG",
]

# High-multiple software / speculative growth — the natural universe for the
# Overvalued Growth Breakdown short.  Mix of IGV constituents + standalone
# speculative names.  Curated, not point-in-time — survivorship bias applies.
EXPENSIVE_SOFTWARE = [
    # AI / cloud SaaS (high P/S)
    "CRWD", "DDOG", "NET", "MDB", "SNOW", "ZS", "PANW", "OKTA",
    # Speculative / unprofitable growth
    "PLTR", "S", "GTLB", "U", "AI", "PATH",
    # Former darlings that crashed in 2022; included so backtest captures the unwind
    "SHOP", "ZM", "DOCU", "TWLO", "ROKU", "TEAM", "WDAY", "NOW",
    # AI-era leaders
    "NVDA", "AVGO", "ARM",
]

def get(name: str) -> list[str]:
    """Return symbols for a named universe.

    Static universes (large25, momentum15) are inlined.
    sp500 reads from universes/sp500_yf.txt (yfinance-compatible tickers
    with dots converted to dashes — refresh via backtest.fetch_sp500).
    """
    static = {
        "large25":    LARGE_CAP_25,
        "momentum15": MOMENTUM_15,
        "expensive_software": EXPENSIVE_SOFTWARE,
    }
    if name in static:
        return static[name]
    if name == "sp500":
        syms = _read_list("sp500_yf.txt")
        if not syms:
            raise RuntimeError(
                "universes/sp500_yf.txt is missing or empty.  Run:\n"
                "  uv run python -m backtest.fetch_sp500"
            )
        return syms
    raise ValueError(f"Unknown universe '{name}'. Options: large25, momentum15, sp500")
