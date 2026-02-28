import pytest
from game.market import initialize_market, advance_market_day, portfolio_value


def test_initialize_market_has_all_12_stocks():
    prices, history = initialize_market()
    assert len(prices) == 12
    for ticker, price in prices.items():
        assert price > 0


def test_advance_day_changes_prices():
    prices, history = initialize_market()
    old_prices = dict(prices)
    new_prices, new_history, events = advance_market_day(prices, history, seed=42)
    changed = sum(1 for t in prices if new_prices[t] != old_prices[t])
    assert changed > 0


def test_price_never_goes_below_one_dollar():
    prices, history = initialize_market()
    for _ in range(100):
        prices, history, _ = advance_market_day(prices, history)
    for price in prices.values():
        assert price >= 1.0


def test_history_capped_at_30_days():
    prices, history = initialize_market()
    for _ in range(35):
        prices, history, _ = advance_market_day(prices, history)
    for ticker, h in history.items():
        assert len(h) <= 30


def test_advance_day_returns_list_of_event_strings():
    prices, history = initialize_market()
    _, _, events = advance_market_day(prices, history)
    assert isinstance(events, list)
    for e in events:
        assert isinstance(e, str)


def test_portfolio_value_empty():
    prices, _ = initialize_market()
    assert portfolio_value({}, prices) == 0.0


def test_portfolio_value_with_holdings():
    prices = {"NVLT": 100.0, "CLOD": 50.0}
    portfolio = {
        "NVLT": {"shares": 10, "avg_cost": 90.0},
        "CLOD": {"shares": 5, "avg_cost": 45.0},
    }
    result = portfolio_value(portfolio, prices)
    assert result == pytest.approx(10 * 100.0 + 5 * 50.0)
