import random
from game.models import GameState, Rack, Server, Contract
from game.finance import apply_daily_savings_interest, apply_daily_cd_interest, accrue_loan_interest
from game.market import initialize_market, advance_market_day, portfolio_value
from game.contracts import generate_contract, generate_gigs

STARTING_CASH = {"easy": 75000.0, "normal": 50000.0, "hard": 25000.0}


def _get(obj, key, default=None):
    """Get an attribute from either a dataclass instance or a dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _set(obj, key, value):
    """Set an attribute on either a dataclass instance or a dict."""
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


def initialize_new_game(company_name: str, difficulty: str) -> GameState:
    prices, history = initialize_market()
    state = GameState(
        company_name=company_name,
        difficulty=difficulty,
        cash=STARTING_CASH[difficulty],
        market_prices=prices,
        price_history=history,
    )
    state.racks.append(Rack(id="rack_1", name="Rack 1"))
    state.pending_contracts = [generate_contract(state) for _ in range(3)]
    state.available_gigs = generate_gigs()
    return state


def _log(state: GameState, msg: str) -> None:
    state.event_log.append(f"[Day {state.day}] {msg}")
    state.event_log = state.event_log[-50:]


def advance_day(state: GameState) -> GameState:
    state.day += 1

    # 1. Daily savings interest
    if state.savings > 0:
        state.savings = apply_daily_savings_interest(state.savings)

    # 2. Daily CD interest
    for cd in state.cds:
        new_balance = apply_daily_cd_interest(
            _get(cd, "balance"), _get(cd, "annual_rate", 0.15)
        )
        _set(cd, "balance", new_balance)
        _set(cd, "days_remaining", _get(cd, "days_remaining", 0) - 1)

    # 3. Daily loan interest
    for loan in state.loans:
        new_balance = accrue_loan_interest(
            _get(loan, "remaining_balance"), _get(loan, "annual_rate")
        )
        _set(loan, "remaining_balance", new_balance)
        _set(loan, "days_remaining", _get(loan, "days_remaining", 0) - 1)

    # 4. Bond maturity
    matured = [b for b in state.bonds if _get(b, "days_remaining", 0) <= 1]
    for bond in matured:
        face_value = _get(bond, "face_value")
        state.cash += face_value
        _log(state, f"Bond matured — received ${face_value:,.2f}")
    state.bonds = [b for b in state.bonds if _get(b, "days_remaining", 0) > 1]
    for bond in state.bonds:
        _set(bond, "days_remaining", _get(bond, "days_remaining", 0) - 1)

    # 5. Monthly billing (every 30 days)
    if state.day % 30 == 0:
        total_rent = sum(_get(r, "monthly_rent", 0.0) for r in state.racks)
        state.cash -= total_rent
        state.total_expenses += total_rent
        _log(state, f"Monthly rack rent: -${total_rent:,.2f}")

        for contract in state.active_contracts:
            if _get(contract, "server_id"):
                revenue = _get(contract, "monthly_revenue", 0.0)
                client_name = _get(contract, "client_name", "Unknown")
                state.cash += revenue
                state.total_revenue += revenue
                _log(state, f"Revenue from {client_name}: +${revenue:,.2f}")

        for loan in state.loans:
            payment = _get(loan, "monthly_payment", 0.0)
            state.cash -= payment
            new_balance = _get(loan, "remaining_balance", 0.0) - payment
            _set(loan, "remaining_balance", new_balance)
            _log(state, f"Loan payment: -${payment:,.2f}")

    # 6. Contract tick — decrement days_remaining
    for contract in state.active_contracts:
        current_remaining = _get(contract, "days_remaining", 0)
        _set(contract, "days_remaining", current_remaining - 1)
        new_remaining = _get(contract, "days_remaining", 0)
        status = _get(contract, "status", "active")
        if new_remaining <= 0 and status == "active":
            _set(contract, "status", "complete")
            client_name = _get(contract, "client_name", "Unknown")
            state.reputation = min(100, state.reputation + 5)
            _log(state, f"Contract with {client_name} completed. +5 rep")

    state.active_contracts = [
        c for c in state.active_contracts if _get(c, "status") == "active"
    ]

    # 7. Advance market
    new_prices, new_history, mkt_events = advance_market_day(
        state.market_prices, state.price_history
    )
    state.market_prices = new_prices
    state.price_history = new_history
    for evt in mkt_events:
        _log(state, evt)

    # 8. Random hardware failure (~1.5% per server per day)
    for server in state.servers:
        health = _get(server, "health", 1.0)
        name = _get(server, "name", "Unknown")
        if health > 0.4 and random.random() < 0.015:
            _set(server, "health", 0.5)
            _log(state, f"WARNING: {name} hardware degraded!")

    # 9. Refresh gigs every 7 days
    if state.day % 7 == 0:
        state.available_gigs = generate_gigs()

    # 10. Add new pending contract occasionally
    if state.day % 5 == 0 and len(state.pending_contracts) < 5:
        state.pending_contracts.append(generate_contract(state))

    # 11. Bankruptcy check
    net_worth = (
        state.cash
        + state.savings
        + portfolio_value(state.portfolio, state.market_prices)
        + sum(_get(b, "face_value", 0.0) for b in state.bonds)
    )
    total_debt = sum(_get(l, "remaining_balance", 0.0) for l in state.loans)
    if net_worth <= 0 and total_debt > 0:
        _log(state, "BANKRUPTCY: Net worth gone negative.")
        state.cash = -1.0

    return state
