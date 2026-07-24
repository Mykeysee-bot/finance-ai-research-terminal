from typing import Any, Dict, Mapping

from dcf_model import calculate_dcf


def calculate_sensitivity_table(
    data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int = 5,
) -> Dict[str, Dict[str, float]]:
    """
    Create a DCF sensitivity table around the user's base assumptions.

    Rows vary annual FCF growth.
    Columns vary the discount rate / WACC.
    """

    growth_rates = [
        max(growth_rate - 0.04, -0.50),
        max(growth_rate - 0.02, -0.50),
        growth_rate,
        growth_rate + 0.02,
        growth_rate + 0.04,
    ]

    discount_rates = [
        max(discount_rate - 0.02, 0.01),
        max(discount_rate - 0.01, 0.01),
        discount_rate,
        discount_rate + 0.01,
        discount_rate + 0.02,
    ]

    table: Dict[str, Dict[str, float]] = {}

    for scenario_growth_rate in growth_rates:
        growth_label = f"{scenario_growth_rate * 100:.1f}% Growth"
        table[growth_label] = {}

        for scenario_discount_rate in discount_rates:
            discount_label = (
                f"{scenario_discount_rate * 100:.1f}% WACC"
            )

            if scenario_discount_rate <= terminal_growth_rate:
                table[growth_label][discount_label] = float("nan")
                continue

            result = calculate_dcf(
                company_data=data,
                growth_rate=scenario_growth_rate,
                discount_rate=scenario_discount_rate,
                terminal_growth_rate=terminal_growth_rate,
                years=years,
            )

            table[growth_label][discount_label] = round(
                result["fair_value_per_share"],
                2,
            )

    return table
