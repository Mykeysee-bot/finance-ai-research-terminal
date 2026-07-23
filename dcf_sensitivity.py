from typing import Any, Dict, List

from dcf_model import calculate_dcf


def calculate_sensitivity_table(
    data: Dict[str, Any],
    growth_rates: List[float],
    discount_rates: List[float],
    terminal_growth_rate: float,
) -> Dict[str, Dict[str, float]]:
    table = {}

    for growth_rate in growth_rates:
        growth_label = f"{growth_rate * 100:.0f}% Growth"
        table[growth_label] = {}

        for discount_rate in discount_rates:
            discount_label = f"{discount_rate * 100:.1f}% Discount"

            result = calculate_dcf(
                free_cash_flow=data.get("free_cash_flow"),
                shares_outstanding=data.get("shares_outstanding"),
                total_cash=data.get("total_cash"),
                total_debt=data.get("total_debt"),
                growth_rate=growth_rate,
                discount_rate=discount_rate,
                terminal_growth_rate=terminal_growth_rate,
            )

            table[growth_label][discount_label] = round(
                result["fair_value_per_share"],
                2,
            )

    return table
