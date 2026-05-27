"""Predefined symbol universes.  Keep small for fast iteration; expand later."""

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

UNIVERSES = {
    "large25": LARGE_CAP_25,
    "momentum15": MOMENTUM_15,
}


def get(name: str) -> list[str]:
    if name not in UNIVERSES:
        raise ValueError(f"Unknown universe '{name}'. Options: {list(UNIVERSES)}")
    return UNIVERSES[name]
