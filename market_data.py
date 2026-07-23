from typing import Any, Dict

import yfinance as yf


def get_stock_data(ticker_symbol: str) -> Dict[str, Any]:
    ticker_symbol = ticker_symbol.strip().upper()

    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    history = stock.history(period="1y")

    if not info:
        raise ValueError(f"No data found for ticker: {ticker_symbol}")

    one_year_return = None
    one_year_high = None
    one_year_low = None

    if not history.empty:
        start_price = history["Close"].iloc[0]
        end_price = history["Close"].iloc[-1]

        if start_price:
            one_year_return = (end_price - start_price) / start_price

        one_year_high = history["High"].max()
        one_year_low = history["Low"].min()

    return {
        "ticker": ticker_symbol,
        "company_name": info.get("longName", ticker_symbol),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "current_price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "enterprise_value": info.get("enterpriseValue"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "revenue": info.get("totalRevenue"),
        "net_income": info.get("netIncomeToCommon"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "return_on_assets": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "total_cash": info.get("totalCash"),
        "total_debt": info.get("totalDebt"),
        "free_cash_flow": info.get("freeCashflow"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "one_year_return": one_year_return,
        "one_year_high": one_year_high,
        "one_year_low": one_year_low,
    }