from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _safe_number(value: Any) -> Optional[float]:
    """Convert a value to a valid float when possible."""
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number != number:
        return None

    return number


def _first_number(
    data: Mapping[str, Any],
    *keys: str,
) -> Optional[float]:
    """Return the first valid numeric value found for the supplied keys."""
    for key in keys:
        number = _safe_number(data.get(key))

        if number is not None:
            return number

    return None


def calculate_dcf(
    free_cash_flow: Optional[float] = None,
    shares_outstanding: Optional[float] = None,
    total_cash: Optional[float] = None,
    total_debt: Optional[float] = None,
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    forecast_years: int = 5,
    company_data: Optional[Mapping[str, Any]] = None,
    data: Optional[Mapping[str, Any]] = None,
    stock_data: Optional[Mapping[str, Any]] = None,
    financial_data: Optional[Mapping[str, Any]] = None,
    years: Optional[int] = None,
    projection_years: Optional[int] = None,
    fcf_growth_rate: Optional[float] = None,
    wacc: Optional[float] = None,
    **_: Any,
) -> Dict[str, Any]:
    """
    Calculate a discounted cash flow valuation.

    Supports both explicit financial inputs and a company-data dictionary.
    """

    source_data = (
        company_data
        or data
        or stock_data
        or financial_data
        or {}
    )

    if free_cash_flow is None:
        free_cash_flow = _first_number(
            source_data,
            "annual_free_cash_flow",
            "latest_annual_free_cash_flow",
            "free_cash_flow",
            "freeCashflow",
            "freeCashFlow",
            "fcf",
        )

    if shares_outstanding is None:
        shares_outstanding = _first_number(
            source_data,
            "shares_outstanding",
            "sharesOutstanding",
            "impliedSharesOutstanding",
            "shares",
        )

    if total_cash is None:
        total_cash = _first_number(
            source_data,
            "total_cash",
            "totalCash",
            "cash_and_short_term_investments",
            "cashCashEquivalentsAndShortTermInvestments",
            "cash",
            "cashAndCashEquivalents",
        )

    if total_debt is None:
        total_debt = _first_number(
            source_data,
            "total_debt",
            "totalDebt",
            "debt",
        )

    if fcf_growth_rate is not None:
        growth_rate = fcf_growth_rate

    if wacc is not None:
        discount_rate = wacc

    if projection_years is not None:
        forecast_years = projection_years
    elif years is not None:
        forecast_years = years

    free_cash_flow = _safe_number(free_cash_flow)
    shares_outstanding = _safe_number(shares_outstanding)
    total_cash = _safe_number(total_cash) or 0.0
    total_debt = _safe_number(total_debt) or 0.0
    growth_rate = float(growth_rate)
    discount_rate = float(discount_rate)
    terminal_growth_rate = float(terminal_growth_rate)
    forecast_years = int(forecast_years)

    if free_cash_flow is None or free_cash_flow <= 0:
        raise ValueError(
            "Free cash flow must be greater than zero."
        )

    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError(
            "Shares outstanding must be greater than zero."
        )

    if forecast_years <= 0:
        raise ValueError(
            "Forecast years must be greater than zero."
        )

    if growth_rate <= -1:
        raise ValueError(
            "Growth rate must be greater than -100%."
        )

    if discount_rate <= terminal_growth_rate:
        raise ValueError(
            "Discount rate must be greater than terminal growth rate."
        )

    projected_cash_flows: list[float] = []
    present_values: list[float] = []

    projected_fcf = free_cash_flow

    for year in range(1, forecast_years + 1):
        projected_fcf *= 1 + growth_rate

        discount_factor = (1 + discount_rate) ** year
        present_value = projected_fcf / discount_factor

        projected_cash_flows.append(projected_fcf)
        present_values.append(present_value)

    terminal_value = (
        projected_cash_flows[-1]
        * (1 + terminal_growth_rate)
        / (discount_rate - terminal_growth_rate)
    )

    discounted_terminal_value = (
        terminal_value
        / ((1 + discount_rate) ** forecast_years)
    )

    present_value_of_forecast_cash_flows = sum(
        present_values
    )

    enterprise_value = (
        present_value_of_forecast_cash_flows
        + discounted_terminal_value
    )

    net_cash = total_cash - total_debt
    equity_value = enterprise_value + net_cash

    fair_value_per_share = (
        equity_value / shares_outstanding
    )

    return {
        "starting_free_cash_flow": free_cash_flow,
        "shares_outstanding": shares_outstanding,
        "total_cash": total_cash,
        "total_debt": total_debt,
        "growth_rate": growth_rate,
        "discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "forecast_years": forecast_years,
        "projected_cash_flows": projected_cash_flows,
        "present_values": present_values,
        "present_value_of_forecast_cash_flows": (
            present_value_of_forecast_cash_flows
        ),
        "terminal_value": terminal_value,
        "discounted_terminal_value": discounted_terminal_value,
        "enterprise_value": enterprise_value,
        "net_cash": net_cash,
        "equity_value": equity_value,
        "fair_value_per_share": fair_value_per_share,
    }


def run_dcf(
    company_data: Mapping[str, Any],
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
) -> Dict[str, Any]:
    """Compatibility wrapper for callers that pass company data."""

    return calculate_dcf(
        company_data=company_data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        forecast_years=years,
    )


def dcf_valuation(
    company_data: Mapping[str, Any],
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
) -> Dict[str, Any]:
    return run_dcf(
        company_data=company_data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        years=years,
    )


def calculate_dcf_valuation(
    company_data: Mapping[str, Any],
    growth_rate: float = 0.10,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.03,
    years: int = 5,
) -> Dict[str, Any]:
    return run_dcf(
        company_data=company_data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        years=years,
    )