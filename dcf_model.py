from typing import Any, Dict, Mapping, Optional


def _first_number(
    data: Mapping[str, Any],
    *keys: str,
) -> Optional[float]:
    for key in keys:
        value = data.get(key)

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)

    return None


def calculate_dcf(
    company_data: Optional[Mapping[str, Any]] = None,
    growth_rate: Optional[float] = None,
    discount_rate: Optional[float] = None,
    terminal_growth_rate: Optional[float] = None,
    years: int = 5,
    *,
    free_cash_flow: Optional[float] = None,
    shares_outstanding: Optional[float] = None,
    total_cash: Optional[float] = None,
    total_debt: Optional[float] = None,
    forecast_years: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate a discounted cash flow valuation.

    Supports both:
    1. A company-data dictionary from app.py
    2. Separate legacy keyword inputs used by scenario/sensitivity modules
    """

    if company_data is not None:
        free_cash_flow = _first_number(
            company_data,
            "free_cash_flow",
            "freeCashflow",
            "fcf",
        )

        shares_outstanding = _first_number(
            company_data,
            "shares_outstanding",
            "sharesOutstanding",
            "implied_shares_outstanding",
        )

        total_cash = _first_number(
            company_data,
            "total_cash",
            "totalCash",
            "cash",
        )

        total_debt = _first_number(
            company_data,
            "total_debt",
            "totalDebt",
            "debt",
        )

    if forecast_years is not None:
        years = int(forecast_years)

    if free_cash_flow is None or free_cash_flow <= 0:
        raise ValueError(
            "Free cash flow is unavailable or must be greater than zero."
        )

    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError(
            "Shares outstanding are unavailable or must be greater than zero."
        )

    if growth_rate is None:
        raise ValueError("A growth rate is required.")

    if discount_rate is None:
        raise ValueError("A discount rate is required.")

    if terminal_growth_rate is None:
        raise ValueError("A terminal growth rate is required.")

    if years <= 0:
        raise ValueError("Projection years must be greater than zero.")

    if discount_rate <= terminal_growth_rate:
        raise ValueError(
            "Discount rate must be greater than terminal growth rate."
        )

    cash = total_cash or 0
    debt = total_debt or 0

    projected_cash_flows = []
    present_values = []

    projected_fcf = float(free_cash_flow)

    for year in range(1, years + 1):
        projected_fcf *= 1 + growth_rate

        discount_factor = (1 + discount_rate) ** year
        present_value = projected_fcf / discount_factor

        projected_cash_flows.append(
            {
                "year": year,
                "projected_fcf": projected_fcf,
                "present_value": present_value,
            }
        )

        present_values.append(present_value)

    final_projected_fcf = projected_cash_flows[-1]["projected_fcf"]

    terminal_value = (
        final_projected_fcf
        * (1 + terminal_growth_rate)
        / (discount_rate - terminal_growth_rate)
    )

    discounted_terminal_value = (
        terminal_value
        / ((1 + discount_rate) ** years)
    )

    enterprise_value = (
        sum(present_values)
        + discounted_terminal_value
    )

    net_cash = cash - debt
    equity_value = enterprise_value + net_cash
    fair_value_per_share = equity_value / shares_outstanding

    return {
        "fair_value_per_share": fair_value_per_share,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "terminal_value": terminal_value,
        "discounted_terminal_value": discounted_terminal_value,
        "net_cash": net_cash,
        "starting_free_cash_flow": free_cash_flow,
        "shares_outstanding": shares_outstanding,
        "growth_rate": growth_rate,
        "discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "projection_years": years,
        "projected_cash_flows": projected_cash_flows,
    }
