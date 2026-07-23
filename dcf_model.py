from typing import Any, Dict, Optional


def calculate_dcf(
    free_cash_flow: Optional[float],
    shares_outstanding: Optional[float],
    total_cash: Optional[float],
    total_debt: Optional[float],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    forecast_years: int = 5,
) -> Dict[str, Any]:
    if free_cash_flow is None or free_cash_flow <= 0:
        raise ValueError("Free cash flow must be greater than zero.")

    if shares_outstanding is None or shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be greater than zero.")

    if discount_rate <= terminal_growth_rate:
        raise ValueError(
            "Discount rate must be greater than terminal growth rate."
        )

    cash = total_cash or 0
    debt = total_debt or 0

    projected_cash_flows = []
    present_values = []

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

    enterprise_value = (
        sum(present_values)
        + discounted_terminal_value
    )

    net_cash = cash - debt
    equity_value = enterprise_value + net_cash

    fair_value_per_share = (
        equity_value
        / shares_outstanding
    )

    return {
        "projected_cash_flows": projected_cash_flows,
        "present_values": present_values,
        "terminal_value": terminal_value,
        "discounted_terminal_value": discounted_terminal_value,
        "enterprise_value": enterprise_value,
        "net_cash": net_cash,
        "equity_value": equity_value,
        "fair_value_per_share": fair_value_per_share,
    }