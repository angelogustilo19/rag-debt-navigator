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

def calculate_monthly_payment(principal: float, annual_interest_rate: float, months: int) -> float:
    """
    Calculates the required monthly payment to pay off a debt in a specific timeframe.
    """
    if months <= 0:
        return float('inf') # Cannot pay off in 0 or negative months

    monthly_interest_rate = annual_interest_rate / 100 / 12

    if monthly_interest_rate == 0:
        return principal / months

    # Formula for fixed monthly payments
    # M = P [ i(1 + i)^n ] / [ (1 + i)^n – 1]
    # M = monthly payment
    # P = principal loan amount
    # i = monthly interest rate
    # n = number of months
    
    numerator = monthly_interest_rate * (1 + monthly_interest_rate)**months
    denominator = (1 + monthly_interest_rate)**months - 1
    
    monthly_payment = principal * (numerator / denominator)
    
    return round(monthly_payment, 2)

# Test the credit card example
print("=== CREDIT CARD TEST ===")
try:
    principal = 5000
    annual_interest_rate = 18
    monthly_payment = 150

    result = calculate_debt_payoff(principal, annual_interest_rate, monthly_payment)
    print(f"Principal: ${principal:,}")
    print(f"Interest Rate: {annual_interest_rate}%")
    print(f"Monthly Payment: ${monthly_payment}")
    print(f"Time to pay off: {result.years} years and {result.months} months")
    print(f"Total paid: ${result.total_paid:,.2f}")
    print(f"Total interest: ${result.total_paid - principal:,.2f}")
    
    # Let's also show some month-by-month breakdown for first few months
    print("\n=== FIRST 5 MONTHS BREAKDOWN ===")
    monthly_interest_rate = annual_interest_rate / 100 / 12
    balance = principal
    for month in range(1, 6):
        interest = balance * monthly_interest_rate
        principal_payment = monthly_payment - interest
        balance -= principal_payment
        print(f"Month {month}: Interest=${interest:.2f}, Principal=${principal_payment:.2f}, Remaining=${balance:.2f}")

except InsufficientPaymentError as e:
    print(e)

# Test with your original example too
print("\n=== YOUR ORIGINAL TEST ===")
try:
    principal = 785900
    annual_interest_rate = 6.875
    monthly_payment = 5500

    result = calculate_debt_payoff(principal, annual_interest_rate, monthly_payment)
    print(f"Principal: ${principal:,}")
    print(f"Interest Rate: {annual_interest_rate}%")
    print(f"Monthly Payment: ${monthly_payment}")
    print(f"Time to pay off: {result.years} years and {result.months} months")
    print(f"Total paid: ${result.total_paid:,.2f}")
    print(f"Total interest: ${result.total_paid - principal:,.2f}")

except InsufficientPaymentError as e:
    print(e)