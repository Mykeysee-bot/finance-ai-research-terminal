from typing import Any, Dict, Optional, Union

from market_data import get_stock_data


Number = Optional[Union[float, int]]


def format_large_number(value: Number) -> str:
    if value is None:
        return "Not available"

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f} trillion"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} billion"

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f} million"

    return f"${value:,.2f}"


def format_price(value: Number) -> str:
    if value is None:
        return "Not available"

    return f"${value:,.2f}"


def format_decimal_percent(value: Optional[float]) -> str:
    if value is None:
        return "Not available"

    return f"{value * 100:.2f}%"


def format_yahoo_percent(value: Optional[float]) -> str:
    if value is None:
        return "Not available"

    return f"{value:.2f}%"


def format_number(value: Number) -> str:
    if value is None:
        return "Not available"

    return f"{value:,.2f}"


def format_debt_to_equity(value: Number) -> str:
    if value is None:
        return "Not available"

    return f"{value / 100:.2f}x"


def print_stock_report(data: Dict[str, Any]) -> None:
    print("\n" + "=" * 55)
    print(data["company_name"].upper())
    print("=" * 55)

    print(f"Ticker: {data['ticker']}")
    print(f"Sector: {data['sector'] or 'Not available'}")
    print(f"Industry: {data['industry'] or 'Not available'}")

    print("\n--- MARKET DATA ---")
    print(f"Current Price: {format_price(data['current_price'])}")
    print(f"52-Week High: {format_price(data['fifty_two_week_high'])}")
    print(f"52-Week Low: {format_price(data['fifty_two_week_low'])}")
    print(f"Market Cap: {format_large_number(data['market_cap'])}")
    print(f"Enterprise Value: {format_large_number(data['enterprise_value'])}")
    print(f"Beta: {format_number(data['beta'])}")
    print(f"Dividend Yield: {format_yahoo_percent(data['dividend_yield'])}")
    print(f"1-Year Return: {format_decimal_percent(data['one_year_return'])}")

    print("\n--- VALUATION ---")
    print(f"Trailing P/E: {format_number(data['trailing_pe'])}")
    print(f"Forward P/E: {format_number(data['forward_pe'])}")
    print(f"PEG Ratio: {format_number(data['peg_ratio'])}")

    print("\n--- FINANCIAL PERFORMANCE ---")
    print(f"Revenue: {format_large_number(data['revenue'])}")
    print(f"Net Income: {format_large_number(data['net_income'])}")
    print(f"Profit Margin: {format_decimal_percent(data['profit_margin'])}")
    print(f"Operating Margin: {format_decimal_percent(data['operating_margin'])}")
    print(f"Return on Equity: {format_decimal_percent(data['return_on_equity'])}")
    print(f"Return on Assets: {format_decimal_percent(data['return_on_assets'])}")

    print("\n--- BALANCE SHEET & CASH FLOW ---")
    print(f"Total Cash: {format_large_number(data['total_cash'])}")
    print(f"Total Debt: {format_large_number(data['total_debt'])}")
    print(f"Debt to Equity: {format_debt_to_equity(data['debt_to_equity'])}")
    print(f"Free Cash Flow: {format_large_number(data['free_cash_flow'])}")

    print("=" * 55)


def main() -> None:
    ticker_symbol = input("Enter a stock ticker: ").strip().upper()

    try:
        stock_data = get_stock_data(ticker_symbol)
        print_stock_report(stock_data)
    except Exception as error:
        print(f"\nCould not analyze {ticker_symbol}: {error}")


if __name__ == "__main__":
    main()