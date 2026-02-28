import pytest
from game.engine import advance_day, initialize_new_game
from game.models import GameState, Rack, Contract, Server


def test_initialize_new_game_normal():
    state = initialize_new_game("Acme DC", "normal")
    assert state.company_name == "Acme DC"
    assert state.cash == 50000.0
    assert len(state.racks) == 1
    assert state.day == 0
    assert len(state.pending_contracts) >= 1
    assert len(state.market_prices) == 12


def test_initialize_new_game_easy():
    state = initialize_new_game("Easy Corp", "easy")
    assert state.cash == 75000.0


def test_initialize_new_game_hard():
    state = initialize_new_game("Hard LLC", "hard")
    assert state.cash == 25000.0


def test_advance_day_increments_day():
    state = initialize_new_game("Test", "normal")
    state = advance_day(state)
    assert state.day == 1


def test_savings_interest_applied_daily():
    state = initialize_new_game("Test", "normal")
    state.savings = 10000.0
    state = advance_day(state)
    assert state.savings > 10000.0


def test_monthly_rent_charged_on_day_30():
    state = initialize_new_game("Test", "normal")
    state.day = 29  # next advance_day call will be day 30
    cash_before = state.cash
    state = advance_day(state)
    assert state.cash < cash_before  # rack rent charged


def test_contract_revenue_paid_on_day_30():
    state = initialize_new_game("Test", "normal")
    server = Server(
        id="s1", name="Srv", components=[], total_cores=8, total_ram_gb=32,
        total_storage_gb=1000, nic_speed_gbps=1, size_u=1, health=1.0
    )
    state.servers.append(server)
    contract = Contract(
        id="c1", client_name="ACME", required_cores=4, required_ram_gb=16,
        required_storage_gb=100, sla_tier="99.0", monthly_revenue=1000.0,
        duration_days=30, days_remaining=30, server_id="s1", status="active"
    )
    state.active_contracts.append(contract)
    state.day = 29
    state = advance_day(state)
    assert state.total_revenue >= 1000.0


def test_market_prices_change_each_day():
    state = initialize_new_game("Test", "normal")
    old_prices = dict(state.market_prices)
    state = advance_day(state)
    changed = sum(1 for t in old_prices if state.market_prices[t] != old_prices[t])
    assert changed > 0


def test_event_log_is_updated():
    state = initialize_new_game("Test", "normal")
    state.day = 29
    state = advance_day(state)
    assert len(state.event_log) > 0  # rent charge logged


def test_contract_days_remaining_decremented():
    state = initialize_new_game("Test", "normal")
    server = Server(
        id="s1", name="Srv", components=[], total_cores=8, total_ram_gb=32,
        total_storage_gb=1000, nic_speed_gbps=1, size_u=1, health=1.0
    )
    state.servers.append(server)
    contract = Contract(
        id="c1", client_name="Client", required_cores=4, required_ram_gb=16,
        required_storage_gb=100, sla_tier="99.0", monthly_revenue=500.0,
        duration_days=60, days_remaining=60, server_id="s1", status="active"
    )
    state.active_contracts.append(contract)
    state = advance_day(state)
    assert state.active_contracts[0].days_remaining == 59
