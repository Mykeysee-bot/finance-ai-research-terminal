from typing import Any, Dict, Mapping, Optional

import pandas as pd

from dcf_model import calculate_dcf


def get_first_number(
    company_data: Mapping[str, Any],
    *keys: str,
) -> Optional[float]:
    for key in keys:
        value = company_data.get(key)

        if value is None:
            continue

        try:
            number = float(value)

            if number == number:
                return number
        except (TypeError, ValueError):
            continue

    return None


def calculate_sensitivity_table(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int = 5,
) -> pd.DataFrame:
    free_cash_flow = get_first_number(
        company_data,
        "free_cash_flow",
        "freeCashflow",
        "freeCashFlow",
        "fcf",
    )

    shares_outstanding = get_first_number(
        company_data,
        "shares_outstanding",
        "sharesOutstanding",
        "shares",
        "impliedSharesOutstanding",
    )

    total_cash = get_first_number(
        company_data,
        "total_cash",
        "totalCash",
        "cash",
        "cashAndCashEquivalents",
    )

    total_debt = get_first_number(
        company_data,
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

    growth_rates = [
        max(growth_rate - 0.04, 0.00),
        max(growth_rate - 0.02, 0.00),
        growth_rate,
        growth_rate + 0.02,
        growth_rate + 0.04,
    ]

    discount_rates = [
        max(discount_rate - 0.02, terminal_growth_rate + 0.01),
        max(discount_rate - 0.01, terminal_growth_rate + 0.01),
        discount_rate,
        discount_rate + 0.01,
        discount_rate + 0.02,
    ]

    rows: list[Dict[str, Any]] = []

    for current_growth_rate in growth_rates:
        row: Dict[str, Any] = {
            "FCF Growth": current_growth_rate,
        }

        for current_discount_rate in discount_rates:
            if current_discount_rate <= terminal_growth_rate:
                row[current_discount_rate] = None
                continue

            result = calculate_dcf(
                free_cash_flow=free_cash_flow,
                shares_outstanding=shares_outstanding,
                total_cash=total_cash,
                total_debt=total_debt,
                growth_rate=current_growth_rate,
                discount_rate=current_discount_rate,
                terminal_growth_rate=terminal_growth_rate,
                forecast_years=years,
            )

            row[current_discount_rate] = result[
                "fair_value_per_share"
            ]

        rows.append(row)

    sensitivity_df = pd.DataFrame(rows)

    renamed_columns: Dict[Any, str] = {
        "FCF Growth": "FCF Growth"
    }

    for rate in discount_rates:
        renamed_columns[rate] = f"{rate * 100:.1f}% WACC"

    sensitivity_df = sensitivity_df.rename(
        columns=renamed_columns
    )

    sensitivity_df["FCF Growth"] = sensitivity_df[
        "FCF Growth"
    ].apply(
        lambda value: f"{value * 100:.1f}%"
    )

    return sensitivity_df


def calculate_dcf_sensitivity(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int = 5,
) -> pd.DataFrame:
    return calculate_sensitivity_table(
        company_data=company_data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        years=years,
    )


def generate_sensitivity_table(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int = 5,
) -> pd.DataFrame:
    return calculate_sensitivity_table(
        company_data=company_data,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        years=years,
    )