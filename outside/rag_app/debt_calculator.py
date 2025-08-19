from pydantic import BaseModel

class PayoffResult(BaseModel):
    years: int
    months: int
    total_paid: float

class InsufficientPaymentError(Exception):
    """Custom exception for when a payment is too low to cover interest."""
    pass

def calculate_debt_payoff(principal: float, annual_interest_rate: float, monthly_payment: float) -> PayoffResult:
    """
    Calculates the time to pay off a debt and the total amount paid.

    Raises:
        InsufficientPaymentError: If the monthly payment is too low.
    """
    monthly_interest_rate = annual_interest_rate / 100 / 12
    balance = principal
    months = 0
    total_paid = 0

    if monthly_payment <= balance * monthly_interest_rate:
        raise InsufficientPaymentError("Your monthly payment is too low to cover interest. Debt will grow indefinitely.")

    while balance > 0:
        interest = balance * monthly_interest_rate
        principal_payment = monthly_payment - interest
        balance -= principal_payment
        total_paid += monthly_payment
        months += 1

        if balance < 0:
            total_paid += balance  # reduce extra payment
            balance = 0

    years = months // 12
    remaining_months = months % 12

    return PayoffResult(years=years, months=remaining_months, total_paid=round(total_paid, 2))

def calculate_monthly_payment(debt_amount: float, interest_rate: float, months: int) -> float:
    """Calculates the monthly payment needed to pay off a debt in a given number of months."""
    if months <= 0:
        return float('inf')
    if interest_rate == 0:
        return debt_amount / months
    monthly_rate = interest_rate / 100 / 12
    return (debt_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -months)
