import pytest
from game.finance import (
    apply_daily_savings_interest,
    apply_daily_cd_interest,
    accrue_loan_interest,
    calculate_loan_payment,
    bond_current_value,
    loan_interest_rate_for_credit_score,
)


def test_savings_interest_daily():
    # 6% annual / 365 days
    result = apply_daily_savings_interest(10000.0, annual_rate=0.06)
    assert result == pytest.approx(10000 * (1 + 0.06 / 365), rel=1e-6)


def test_cd_interest_daily():
    result = apply_daily_cd_interest(5000.0, annual_rate=0.15)
    assert result == pytest.approx(5000 * (1 + 0.15 / 365), rel=1e-6)


def test_loan_payment_calculation():
    # $10,000 loan at 5% APR, 12 months
    payment = calculate_loan_payment(10000.0, annual_rate=0.05, term_months=12)
    # Standard amortization formula result ≈ $856.07
    assert 850 < payment < 870


def test_loan_payment_zero_rate():
    # Zero interest: each payment is principal / months
    payment = calculate_loan_payment(12000.0, annual_rate=0.0, term_months=12)
    assert payment == pytest.approx(1000.0)


def test_loan_accrues_daily_interest():
    balance = accrue_loan_interest(10000.0, annual_rate=0.05)
    expected = 10000 * (1 + 0.05 / 365)
    assert balance == pytest.approx(expected, rel=1e-6)


def test_bond_value_at_maturity_equals_face():
    value = bond_current_value(
        face_value=1000.0, annual_yield=0.15, days_remaining=0, maturity_days=30
    )
    assert value == pytest.approx(1000.0)


def test_bond_value_before_maturity_is_less_than_face_plus_full_accrual():
    # Selling early: gets partial accrual minus liquidity penalty
    value = bond_current_value(
        face_value=1000.0, annual_yield=0.15, days_remaining=15, maturity_days=30
    )
    assert value < 1000.0  # less than face due to liquidity penalty
    assert value > 900.0   # but not too much less


def test_loan_rate_high_credit_score():
    # 850 credit score → lowest rate (3%)
    rate = loan_interest_rate_for_credit_score(850)
    assert rate == pytest.approx(0.03, abs=0.001)


def test_loan_rate_low_credit_score():
    # 300 credit score → highest rate (8%)
    rate = loan_interest_rate_for_credit_score(300)
    assert rate == pytest.approx(0.08, abs=0.001)


def test_loan_rate_mid_credit_score():
    # 575 credit score → middle of range (~5.5%)
    rate = loan_interest_rate_for_credit_score(575)
    assert 0.03 < rate < 0.08
