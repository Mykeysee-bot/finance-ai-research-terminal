from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _get_api_key() -> str:
    """Get the OpenAI API key locally or from Streamlit Cloud."""
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        return api_key

    try:
        import streamlit as st

        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found. Add it to your .env file "
            "or Streamlit Secrets."
        )

    return api_key


def _format_value(value: Any) -> str:
    """Format values so they are readable inside the AI prompt."""
    if value is None:
        return "Not available"

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    return str(value)


def _build_company_summary(company_data: dict[str, Any]) -> str:
    """Convert a company-data dictionary into readable prompt text."""
    if not company_data:
        return "- No additional financial data supplied."

    excluded_fields = {
        "price_history",
        "historical_prices",
        "financial_statements",
        "income_statement",
        "balance_sheet",
        "cash_flow_statement",
    }

    lines = []

    for key, value in company_data.items():
        if key in excluded_fields:
            continue

        if isinstance(value, (dict, list, tuple)):
            continue

        readable_key = key.replace("_", " ").title()
        lines.append(f"- {readable_key}: {_format_value(value)}")

    if not lines:
        return "- No additional financial data supplied."

    return "\n".join(lines)


def compare_companies_with_ai(
    company_1_data: dict[str, Any],
    company_2_data: dict[str, Any],
    *_: Any,
    **__: Any,
) -> str:
    """
    Generate an AI comparison using two company-data dictionaries.

    This function is designed to receive the dictionaries created by app.py.
    """

    if not isinstance(company_1_data, dict):
        raise TypeError("company_1_data must be a dictionary.")

    if not isinstance(company_2_data, dict):
        raise TypeError("company_2_data must be a dictionary.")

    ticker_1 = str(
        company_1_data.get("ticker")
        or company_1_data.get("symbol")
        or "Company 1"
    ).strip().upper()

    ticker_2 = str(
        company_2_data.get("ticker")
        or company_2_data.get("symbol")
        or "Company 2"
    ).strip().upper()

    company_name_1 = str(
        company_1_data.get("company_name")
        or company_1_data.get("name")
        or ticker_1
    )

    company_name_2 = str(
        company_2_data.get("company_name")
        or company_2_data.get("name")
        or ticker_2
    )

    company_1_summary = _build_company_summary(company_1_data)
    company_2_summary = _build_company_summary(company_2_data)

    prompt = f"""
You are an equity research analyst.

Compare the following two public companies as potential investments.

Company 1
Name: {company_name_1}
Ticker: {ticker_1}

Financial information:
{company_1_summary}

Company 2
Name: {company_name_2}
Ticker: {ticker_2}

Financial information:
{company_2_summary}

Write a clear and professional comparison using these sections:

1. Business overview
2. Growth and profitability
3. Valuation
4. Financial strength
5. Market performance
6. Competitive advantages
7. Major risks
8. Which company currently appears stronger
9. Final investment conclusion

Requirements:
- Use concise markdown headings.
- Use bullet points instead of long paragraphs where possible.
- Format all currency values like $53.17 billion or $4.70 trillion.
- Never split numbers, currency symbols, or units across lines.
- Format percentages like 63% and ratios like 3.44x.
- Do not repeat the same number twice in one sentence.
- Do not invent missing financial figures.
- Clearly distinguish facts from judgment.
- Do not guarantee future returns.
- Keep the response under 1,000 words.
"""

    client = OpenAI(api_key=_get_api_key())

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    output_text = getattr(response, "output_text", None)

    if not output_text:
        raise ValueError("The AI comparison returned no text.")

    return output_text


def generate_ai_comparison(
    company_1_data: dict[str, Any],
    company_2_data: dict[str, Any],
    *_: Any,
    **__: Any,
) -> str:
    """Compatibility function used by app.py."""
    return compare_companies_with_ai(
        company_1_data,
        company_2_data,
    )


def compare_companies_ai(
    company_1_data: dict[str, Any],
    company_2_data: dict[str, Any],
    *_: Any,
    **__: Any,
) -> str:
    """Additional compatibility function."""
    return compare_companies_with_ai(
        company_1_data,
        company_2_data,
    )


def ai_compare_companies(
    company_1_data: dict[str, Any],
    company_2_data: dict[str, Any],
    *_: Any,
    **__: Any,
) -> str:
    """Additional compatibility function."""
    return compare_companies_with_ai(
        company_1_data,
        company_2_data,
    )