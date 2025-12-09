from budget_db import get_budget, get_expenses

def calculate_summary():
    # -----------------------------
    # Load budget base values
    # -----------------------------
    budget = get_budget()
    if budget is None:
        return {
            "remaining": 0,
            "savings_percent": 0,
            "weekly_allowance": 0,
            "overspending": False,
            "negative_cash": False,
        }

    income, savings, cash = float(budget[0]), float(budget[1]), float(budget[2])

    # -----------------------------
    # Calculate total expenses
    # -----------------------------
    expenses = get_expenses()
    total_expenses = sum(float(row[1]) for row in expenses)

    # -----------------------------
    # Core summary calculations
    # -----------------------------
    remaining = income - total_expenses - savings
    overspending = remaining < 0
    negative_cash = cash < 0

    # Avoid division by zero
    savings_percent = (savings / income * 100) if income > 0 else 0

    weekly_allowance = remaining / 4 if remaining > 0 else 0

    return {
        "remaining": remaining,
        "savings_percent": savings_percent,
        "weekly_allowance": weekly_allowance,
        "overspending": overspending,
        "negative_cash": negative_cash,
    }
