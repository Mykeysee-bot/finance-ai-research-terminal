from typing import Any, Dict


def compare_companies(
    first_company: Dict[str, Any],
    second_company: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    return {
        "Current Price": {
            first_company["ticker"]: first_company.get("current_price"),
            second_company["ticker"]: second_company.get("current_price"),
        },
        "Market Cap": {
            first_company["ticker"]: first_company.get("market_cap"),
            second_company["ticker"]: second_company.get("market_cap"),
        },
        "Enterprise Value": {
            first_company["ticker"]: first_company.get("enterprise_value"),
            second_company["ticker"]: second_company.get("enterprise_value"),
        },
        "Trailing P/E": {
            first_company["ticker"]: first_company.get("trailing_pe"),
            second_company["ticker"]: second_company.get("trailing_pe"),
        },
        "Forward P/E": {
            first_company["ticker"]: first_company.get("forward_pe"),
            second_company["ticker"]: second_company.get("forward_pe"),
        },
        "PEG Ratio": {
            first_company["ticker"]: first_company.get("peg_ratio"),
            second_company["ticker"]: second_company.get("peg_ratio"),
        },
        "Revenue": {
            first_company["ticker"]: first_company.get("revenue"),
            second_company["ticker"]: second_company.get("revenue"),
        },
        "Net Income": {
            first_company["ticker"]: first_company.get("net_income"),
            second_company["ticker"]: second_company.get("net_income"),
        },
        "Profit Margin": {
            first_company["ticker"]: first_company.get("profit_margin"),
            second_company["ticker"]: second_company.get("profit_margin"),
        },
        "Operating Margin": {
            first_company["ticker"]: first_company.get("operating_margin"),
            second_company["ticker"]: second_company.get("operating_margin"),
        },
        "Return on Equity": {
            first_company["ticker"]: first_company.get("return_on_equity"),
            second_company["ticker"]: second_company.get("return_on_equity"),
        },
        "Total Cash": {
            first_company["ticker"]: first_company.get("total_cash"),
            second_company["ticker"]: second_company.get("total_cash"),
        },
        "Total Debt": {
            first_company["ticker"]: first_company.get("total_debt"),
            second_company["ticker"]: second_company.get("total_debt"),
        },
        "Free Cash Flow": {
            first_company["ticker"]: first_company.get("free_cash_flow"),
            second_company["ticker"]: second_company.get("free_cash_flow"),
        },
        "One-Year Return": {
            first_company["ticker"]: first_company.get("one_year_return"),
            second_company["ticker"]: second_company.get("one_year_return"),
        },
    }