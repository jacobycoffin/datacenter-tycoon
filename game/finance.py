def apply_daily_savings_interest(balance: float, annual_rate: float = 0.06) -> float:
    return balance * (1 + annual_rate / 365)


def apply_daily_cd_interest(balance: float, annual_rate: float = 0.15) -> float:
    return balance * (1 + annual_rate / 365)


def calculate_loan_payment(principal: float, annual_rate: float, term_months: int) -> float:
    """Standard amortization formula — returns fixed monthly payment."""
    if annual_rate == 0:
        return principal / term_months
    r = annual_rate / 12
    n = term_months
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def accrue_loan_interest(balance: float, annual_rate: float) -> float:
    return balance * (1 + annual_rate / 365)


def bond_current_value(
    face_value: float, annual_yield: float, days_remaining: int, maturity_days: int
) -> float:
    """Market value of a bond. At maturity = face_value. Early sale = discounted."""
    if days_remaining <= 0:
        return face_value
    earned_fraction = (maturity_days - days_remaining) / maturity_days
    accrued = face_value * annual_yield * (maturity_days / 365) * earned_fraction
    penalty = face_value * 0.01  # 1% liquidity penalty for early sale
    return face_value + accrued - penalty


def loan_interest_rate_for_credit_score(credit_score: int) -> float:
    """Returns APR based on credit score. 850 = 3%, 300 = 8%. Linear interpolation."""
    t = max(0.0, min(1.0, (credit_score - 300) / (850 - 300)))
    return 0.08 - (t * 0.05)
