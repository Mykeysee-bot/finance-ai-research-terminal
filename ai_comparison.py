from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path.cwd() / ".env")

client = OpenAI()


def format_money(value: Any) -> str:
    if value is None:
        return "Not available"

    if abs(value) >= 1_000_000_000_000:
        return f"USD {value / 1_000_000_000_000:.2f} trillion"

    if abs(value) >= 1_000_000_000:
        return f"USD {value / 1_000_000_000:.2f} billion"

    if abs(value) >= 1_000_000:
        return f"USD {value / 1_000_000:.2f} million"

    return f"USD {value:,.2f}"


def format_percent(value: Any) -> str:
    if value is None:
        return "Not available"

    return f"{value * 100:.2f}%"


def format_ratio(value: Any) -> str:
    if value is None:
        return "Not available"

    return f"{value:.2f}"


def generate_ai_comparison(
    first_company: Dict[str, Any],
    second_company: Dict[str, Any],
    first_scores: Dict[str, int],
    second_scores: Dict[str, int],
) -> str:
    prompt = f"""
You are an equity research analyst comparing two public companies.

Use only the data provided. Do not add news, products, competitors,
market-share claims, forecasts, or outside facts.

FIRST COMPANY
Company: {first_company.get('company_name')}
Ticker: {first_company.get('ticker')}
Overall score: {first_scores.get('overall')} / 100
Profitability score: {first_scores.get('profitability')} / 100
Balance sheet score: {first_scores.get('balance_sheet')} / 100
Valuation score: {first_scores.get('valuation')} / 100
Market performance score: {first_scores.get('market_performance')} / 100
Market capitalization: {format_money(first_company.get('market_cap'))}
Trailing P/E: {format_ratio(first_company.get('trailing_pe'))}
Forward P/E: {format_ratio(first_company.get('forward_pe'))}
PEG ratio: {format_ratio(first_company.get('peg_ratio'))}
Revenue: {format_money(first_company.get('revenue'))}
Net income: {format_money(first_company.get('net_income'))}
Profit margin: {format_percent(first_company.get('profit_margin'))}
Operating margin: {format_percent(first_company.get('operating_margin'))}
Return on equity: {format_percent(first_company.get('return_on_equity'))}
Total cash: {format_money(first_company.get('total_cash'))}
Total debt: {format_money(first_company.get('total_debt'))}
Free cash flow: {format_money(first_company.get('free_cash_flow'))}
One-year return: {format_percent(first_company.get('one_year_return'))}

SECOND COMPANY
Company: {second_company.get('company_name')}
Ticker: {second_company.get('ticker')}
Overall score: {second_scores.get('overall')} / 100
Profitability score: {second_scores.get('profitability')} / 100
Balance sheet score: {second_scores.get('balance_sheet')} / 100
Valuation score: {second_scores.get('valuation')} / 100
Market performance score: {second_scores.get('market_performance')} / 100
Market capitalization: {format_money(second_company.get('market_cap'))}
Trailing P/E: {format_ratio(second_company.get('trailing_pe'))}
Forward P/E: {format_ratio(second_company.get('forward_pe'))}
PEG ratio: {format_ratio(second_company.get('peg_ratio'))}
Revenue: {format_money(second_company.get('revenue'))}
Net income: {format_money(second_company.get('net_income'))}
Profit margin: {format_percent(second_company.get('profit_margin'))}
Operating margin: {format_percent(second_company.get('operating_margin'))}
Return on equity: {format_percent(second_company.get('return_on_equity'))}
Total cash: {format_money(second_company.get('total_cash'))}
Total debt: {format_money(second_company.get('total_debt'))}
Free cash flow: {format_money(second_company.get('free_cash_flow'))}
One-year return: {format_percent(second_company.get('one_year_return'))}

Write the comparison using exactly these headings:

## Comparison Summary

## Profitability Comparison

## Balance Sheet Comparison

## Valuation Comparison

## Market Performance Comparison

## Key Trade-Offs

## Overall Conclusion

Rules:
- Use bullet points under every section except Comparison Summary and Overall Conclusion.
- Explain why each difference matters.
- Do not call either stock a buy or sell.
- Do not use dollar signs or LaTeX.
- Do not claim that a lower valuation automatically means undervaluation.
- Clearly state when an interpretation relies on forward estimates.
- Keep the report below 500 words.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text
