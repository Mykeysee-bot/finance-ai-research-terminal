
from typing import Any, Dict, Mapping, Optional

from dcf_model import calculate_dcf


def _safe_number(value: Any) -> Optional[float]:
    try:
        number = float(value)

        if number == number:
            return number
    except (TypeError, ValueError):
        pass

    return None


def _first_number(
    data: Mapping[str, Any],
    *keys: str,
) -> Optional[float]:
    for key in keys:
        number = _safe_number(data.get(key))

        if number is not None:
            return number

    return None


def calculate_dcf_scenarios(
    data: Mapping[str, Any],
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
    forecast_years: Optional[int] = None,
    **_: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate bear, base, and bull DCF scenarios around the user's
    selected base-case assumptions.
    """

    if forecast_years is not None:
        years = int(forecast_years)

    free_cash_flow = _first_number(
        data,
        "annual_free_cash_flow",
        "latest_annual_free_cash_flow",
        "free_cash_flow",
        "freeCashflow",
        "freeCashFlow",
        "fcf",
    )

    shares_outstanding = _first_number(
        data,
        "shares_outstanding",
        "sharesOutstanding",
        "impliedSharesOutstanding",
        "shares",
    )

    total_cash = _first_number(
        data,
        "total_cash",
        "totalCash",
        "cash_and_short_term_investments",
        "cashCashEquivalentsAndShortTermInvestments",
        "cash",
        "cashAndCashEquivalents",
    )

    total_debt = _first_number(
        data,
        "total_debt",
        "totalDebt",
        "debt",
    )

    if free_cash_flow is None or free_cash_flow <= 0:
        raise ValueError(
            "Free cash flow could not be found in the company data."
        )

    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError(
            "Shares outstanding could not be found in the company data."
        )

    scenarios = {
        "Bear": {
            "growth_rate": max(growth_rate - 0.05, -0.50),
            "discount_rate": discount_rate + 0.01,
            "terminal_growth_rate": terminal_growth_rate - 0.005,
        },
        "Base": {
            "growth_rate": growth_rate,
            "discount_rate": discount_rate,
            "terminal_growth_rate": terminal_growth_rate,
        },
        "Bull": {
            "growth_rate": growth_rate + 0.05,
            "discount_rate": max(
                discount_rate - 0.01,
                terminal_growth_rate + 0.01,
            ),
            "terminal_growth_rate": terminal_growth_rate + 0.005,
        },
    }

    results: Dict[str, Dict[str, Any]] = {}

    for scenario_name, assumptions in scenarios.items():
        scenario_discount_rate = assumptions["discount_rate"]
        scenario_terminal_growth = assumptions[
            "terminal_growth_rate"
        ]

        if scenario_terminal_growth >= scenario_discount_rate:
            scenario_terminal_growth = (
                scenario_discount_rate - 0.005
            )
            assumptions["terminal_growth_rate"] = (
                scenario_terminal_growth
            )

        result = calculate_dcf(
            free_cash_flow=free_cash_flow,
            shares_outstanding=shares_outstanding,
            total_cash=total_cash,
            total_debt=total_debt,
            growth_rate=assumptions["growth_rate"],
            discount_rate=scenario_discount_rate,
            terminal_growth_rate=scenario_terminal_growth,
            forecast_years=years,
        )

        result["assumptions"] = assumptions
        results[scenario_name] = result

    return results


def generate_dcf_scenarios(
    data: Mapping[str, Any],
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
    **kwargs: Any,
) -> Dict[str, Dict[str, Any]]:
    return calculate_dcf_scenarios(
        data=data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        years=years,
        **kwargs,
    )
