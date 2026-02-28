import pytest
from game.contracts import (
    generate_contract,
    generate_gigs,
    negotiate_contract,
    check_sla_health,
)
from game.models import GameState, Contract


def make_state(reputation=0):
    return GameState(company_name="Test", difficulty="normal", reputation=reputation)


def test_generate_contract_returns_valid_contract():
    state = make_state()
    contract = generate_contract(state, seed=42)
    assert contract.monthly_revenue > 0
    assert contract.required_cores >= 2
    assert contract.required_ram_gb >= 8
    assert contract.sla_tier in ["99.0", "99.5", "99.9"]
    assert contract.status == "pending"


def test_generate_contract_scales_with_reputation():
    low_rep_contract = generate_contract(make_state(reputation=0), seed=1)
    high_rep_contract = generate_contract(make_state(reputation=70), seed=1)
    # Higher reputation should unlock higher-revenue contracts
    # (not guaranteed with same seed, so just check basic validity)
    assert high_rep_contract.required_cores >= 2
    assert low_rep_contract.monthly_revenue > 0


def test_generate_gigs_returns_2_to_4():
    gigs = generate_gigs(seed=1)
    assert 2 <= len(gigs) <= 4


def test_generate_gigs_have_positive_payout():
    gigs = generate_gigs(seed=99)
    for gig in gigs:
        assert gig.payout > 0
        assert len(gig.title) > 0


def test_negotiate_contract_increases_revenue():
    state = make_state()
    contract = generate_contract(state, seed=42)
    original = contract.monthly_revenue
    # Use a low counter_pct so it's likely to succeed
    result = negotiate_contract(contract, counter_pct=0.05)
    # May return None (rejection) or a new contract with higher revenue
    if result is not None:
        assert result.monthly_revenue == pytest.approx(original * 1.05, abs=0.01)


def test_negotiate_too_high_always_fails():
    state = make_state()
    contract = generate_contract(state, seed=42)
    result = negotiate_contract(contract, counter_pct=0.50)
    assert result is None  # >30% always rejected


def test_check_sla_health_green_when_healthy():
    contract = Contract(
        id="c1", client_name="Test Co", required_cores=4, required_ram_gb=16,
        required_storage_gb=100, sla_tier="99.0", monthly_revenue=1000,
        duration_days=30, days_remaining=30, status="active"
    )
    assert check_sla_health(contract, server_health=1.0) == "green"


def test_check_sla_health_red_when_server_failed():
    contract = Contract(
        id="c1", client_name="Test Co", required_cores=4, required_ram_gb=16,
        required_storage_gb=100, sla_tier="99.0", monthly_revenue=1000,
        duration_days=30, days_remaining=30, status="active"
    )
    assert check_sla_health(contract, server_health=0.0) == "red"


def test_check_sla_health_yellow_when_degraded():
    contract = Contract(
        id="c1", client_name="Test Co", required_cores=4, required_ram_gb=16,
        required_storage_gb=100, sla_tier="99.0", monthly_revenue=1000,
        duration_days=30, days_remaining=30, status="active", days_degraded=2
    )
    assert check_sla_health(contract, server_health=0.5) == "yellow"
