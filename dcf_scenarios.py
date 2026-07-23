from typing import Any, Dict

from dcf_model import calculate_dcf


def calculate_dcf_scenarios(
    data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    scenarios = {
        "Bear": {
            "growth_rate": 0.10,
            "discount_rate": 0.11,
            "terminal_growth_rate": 0.025,
        },
        "Base": {
            "growth_rate": 0.20,
            "discount_rate": 0.10,
            "terminal_growth_rate": 0.03,
        },
        "Bull": {
            "growth_rate": 0.30,
            "discount_rate": 0.09,
            "terminal_growth_rate": 0.035,
        },
    }

    results = {}

    for scenario_name, assumptions in scenarios.items():
        results[scenario_name] = calculate_dcf(
            free_cash_flow=data.get("free_cash_flow"),
            shares_outstanding=data.get("shares_outstanding"),
            total_cash=data.get("total_cash"),
            total_debt=data.get("total_debt"),
            growth_rate=assumptions["growth_rate"],
            discount_rate=assumptions["discount_rate"],
            terminal_growth_rate=assumptions[
                "terminal_growth_rate"
            ],
        )

        results[scenario_name]["assumptions"] = assumptions

    return results