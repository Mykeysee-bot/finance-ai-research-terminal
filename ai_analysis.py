from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path.cwd() / ".env")

client = OpenAI()

Number = Optional[Union[float, int]]


def format_money(value: Number) -> str:
    if value is None:
        return "Not available"

    if abs(value) >= 1_000_000_000_000:
        return f"USD {value / 1_000_000_000_000:.2f} trillion"

    if abs(value) >= 1_000_000_000:
        return f"USD {value / 1_000_000_000:.2f} billion"

    if abs(value) >= 1_000_000:
        return f"USD {value / 1_000_000:.2f} million"

    return f"USD {value:,.2f}"


def format_percent(value: Optional[float]) -> str:
    if value is None:
        return "Not available"

    return f"{value * 100:.2f}%"


def format_yahoo_percent(value: Optional[float]) -> str:
    if value is None:
        return "Not available"

    return f"{value:.2f}%"


def format_ratio(value: Number) -> str:
    if value is None:
        return "Not available"

    return f"{value:.2f}"


def format_debt_to_equity(value: Number) -> str:
    if value is None:
        return "Not available"

    return f"{value / 100:.2f}x"


def generate_ai_analysis(data: Dict[str, Any]) -> str:
    prompt = f"""
You are an equity research analyst creating a concise company research memo.

Use only the supplied data. Do not add news, competitors, forecasts, market-share claims,
or outside facts.

Company: {data.get('company_name')}
Ticker: {data.get('ticker')}
Sector: {data.get('sector')}
Industry: {data.get('industry')}

Current price: {format_money(data.get('current_price'))}
Market capitalization: {format_money(data.get('market_cap'))}
Enterprise value: {format_money(data.get('enterprise_value'))}
One-year return: {format_percent(data.get('one_year_return'))}

Trailing P/E: {format_ratio(data.get('trailing_pe'))}
Forward P/E: {format_ratio(data.get('forward_pe'))}
PEG ratio: {format_ratio(data.get('peg_ratio'))}
Dividend yield: {format_yahoo_percent(data.get('dividend_yield'))}

Revenue: {format_money(data.get('revenue'))}
Net income: {format_money(data.get('net_income'))}
Profit margin: {format_percent(data.get('profit_margin'))}
Operating margin: {format_percent(data.get('operating_margin'))}
Return on equity: {format_percent(data.get('return_on_equity'))}
Return on assets: {format_percent(data.get('return_on_assets'))}

Cash: {format_money(data.get('total_cash'))}
Debt: {format_money(data.get('total_debt'))}
Debt-to-equity ratio: {format_debt_to_equity(data.get('debt_to_equity'))}
Free cash flow: {format_money(data.get('free_cash_flow'))}

Write the report using exactly these headings:

## Investment Summary

## Financial Strengths

## Bull Case

## Bear Case

## Key Risks

## Catalysts

## Overall Assessment

Rules:
- Use bullet points under every section except Investment Summary and Overall Assessment.
- Do not use dollar signs. Write USD instead.
- Do not use LaTeX or mathematical notation.
- Do not call the company a buy, sell, strong buy, or strong sell.
- Clearly state when an interpretation depends on forward estimates.
- Do not claim that forward P/E or PEG proves the stock is undervalued.
- Explain why the numbers matter instead of merely repeating them.
- Keep the report below 500 words.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text