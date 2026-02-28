import json
import random
from pathlib import Path

COMPANIES_PATH = Path(__file__).parent.parent / "data" / "companies.json"

MARKET_EVENTS = [
    ("{ticker} beats earnings — analysts raise price target", 0.08, 0.15),
    ("{ticker} misses earnings — stock falls", -0.12, -0.06),
    ("Sector rally boosts {ticker}", 0.05, 0.10),
    ("Market-wide correction hits {ticker}", -0.08, -0.04),
    ("New partnership announced for {ticker}", 0.06, 0.12),
    ("{ticker} faces regulatory scrutiny", -0.10, -0.05),
    ("Analyst upgrades {ticker} to Buy", 0.07, 0.13),
    ("{ticker} reports record revenue", 0.09, 0.15),
]


def initialize_market() -> tuple[dict, dict]:
    """Load companies.json and return (prices, history) dicts."""
    companies = json.loads(COMPANIES_PATH.read_text())
    prices = {c["ticker"]: c["base_price"] for c in companies}
    history = {c["ticker"]: [c["base_price"]] for c in companies}
    return prices, history


def advance_market_day(
    prices: dict,
    history: dict,
    seed: int = None,
    event_chance: float = 0.10,
) -> tuple[dict, dict, list[str]]:
    """Advance all stock prices one day. Returns (new_prices, new_history, events)."""
    rng = random.Random(seed)
    new_prices = {}
    events = []

    for ticker, price in prices.items():
        # Brownian motion: Gaussian noise, clamped to ±5%
        pct = rng.gauss(0, 0.015)
        pct = max(-0.05, min(0.05, pct))
        new_prices[ticker] = max(1.0, round(price * (1 + pct), 2))

    # Random market event
    if rng.random() < event_chance:
        template, low, high = rng.choice(MARKET_EVENTS)
        ticker = rng.choice(list(prices.keys()))
        pct = rng.uniform(low, high)
        new_prices[ticker] = max(1.0, round(new_prices[ticker] * (1 + pct), 2))
        sign = "+" if pct > 0 else ""
        events.append(template.format(ticker=ticker) + f" ({sign}{pct*100:.1f}%)")

    # Update history, capped at 30 entries
    new_history = {}
    for ticker in prices:
        hist = history.get(ticker, []) + [new_prices[ticker]]
        new_history[ticker] = hist[-30:]

    return new_prices, new_history, events


def portfolio_value(portfolio: dict, prices: dict) -> float:
    """Calculate total market value of all stock holdings."""
    total = 0.0
    for ticker, holding in portfolio.items():
        shares = holding.get("shares", 0)
        price = prices.get(ticker, 0.0)
        total += shares * price
    return total
