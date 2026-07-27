from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import pandas as pd
import yfinance as yf


def _safe_number(value: Any) -> Optional[float]:
    """Convert a value to a usable float or return None."""
    if value is None:
        return None

    try:
        number = float(value)

        if pd.isna(number):
            return None

        return number
    except (TypeError, ValueError):
        return None


def _first_available(
    data: Dict[str, Any],
    keys: Iterable[str],
) -> Any:
    """Return the first non-empty value found in a dictionary."""
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return None


def _statement_value(
    statement: pd.DataFrame,
    row_names: Iterable[str],
) -> Optional[float]:
    """
    Retrieve the newest available value from a yfinance financial statement.

    yfinance statement rows can vary slightly between companies, so this
    checks several possible row names.
    """
    if statement is None or statement.empty:
        return None

    for row_name in row_names:
        if row_name not in statement.index:
            continue

        row = statement.loc[row_name]

        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]

        for value in row:
            number = _safe_number(value)

            if number is not None:
                return number

    return None


def _safe_statement(
    stock: yf.Ticker,
    attribute_name: str,
) -> pd.DataFrame:
    """Safely retrieve a yfinance financial statement."""
    try:
        statement = getattr(stock, attribute_name)

        if isinstance(statement, pd.DataFrame):
            return statement
    except Exception:
        pass

    return pd.DataFrame()


def get_stock_data(ticker_symbol: str) -> Dict[str, Any]:
    ticker_symbol = ticker_symbol.strip().upper()

    if not ticker_symbol:
        raise ValueError("Ticker symbol cannot be empty.")

    stock = yf.Ticker(ticker_symbol)

    try:
        info = stock.info or {}
    except Exception:
        info = {}

    try:
        fast_info = stock.fast_info
    except Exception:
        fast_info = {}

    try:
        history = stock.history(
            period="1y",
            auto_adjust=False,
        )
    except Exception:
        history = pd.DataFrame()

    income_statement = _safe_statement(stock, "income_stmt")
    balance_sheet = _safe_statement(stock, "balance_sheet")
    cash_flow_statement = _safe_statement(stock, "cashflow")

    if not info and history.empty:
        raise ValueError(f"No data found for ticker: {ticker_symbol}")

    # -------------------------------------------------------------------------
    # PRICE DATA
    # -------------------------------------------------------------------------

    current_price = _safe_number(
        _first_available(
            info,
            (
                "currentPrice",
                "regularMarketPrice",
                "previousClose",
            ),
        )
    )

    if current_price is None:
        try:
            current_price = _safe_number(fast_info["last_price"])
        except Exception:
            current_price = None

    if current_price is None and not history.empty:
        current_price = _safe_number(history["Close"].iloc[-1])

    previous_close = _safe_number(
        _first_available(
            info,
            (
                "previousClose",
                "regularMarketPreviousClose",
            ),
        )
    )

    if previous_close is None:
        try:
            previous_close = _safe_number(fast_info["previous_close"])
        except Exception:
            previous_close = None

    one_year_return = None
    one_year_high = None
    one_year_low = None

    if not history.empty:
        if "Close" in history.columns:
            close_prices = history["Close"].dropna()

            if len(close_prices) >= 2:
                start_price = _safe_number(close_prices.iloc[0])
                end_price = _safe_number(close_prices.iloc[-1])

                if start_price not in (None, 0) and end_price is not None:
                    one_year_return = (
                        end_price - start_price
                    ) / start_price

        if "High" in history.columns:
            one_year_high = _safe_number(history["High"].max())

        if "Low" in history.columns:
            one_year_low = _safe_number(history["Low"].min())

    daily_change = None
    daily_change_percent = None

    if (
        current_price is not None
        and previous_close not in (None, 0)
    ):
        daily_change = current_price - previous_close
        daily_change_percent = daily_change / previous_close

    # -------------------------------------------------------------------------
    # INCOME STATEMENT DATA
    # -------------------------------------------------------------------------

    revenue = _safe_number(info.get("totalRevenue"))

    if revenue is None:
        revenue = _statement_value(
            income_statement,
            (
                "Total Revenue",
                "Operating Revenue",
            ),
        )

    net_income = _safe_number(info.get("netIncomeToCommon"))

    if net_income is None:
        net_income = _statement_value(
            income_statement,
            (
                "Net Income Common Stockholders",
                "Net Income",
            ),
        )

    operating_income = _statement_value(
        income_statement,
        (
            "Operating Income",
            "Total Operating Income As Reported",
        ),
    )

    ebit = _statement_value(
        income_statement,
        (
            "EBIT",
            "Operating Income",
        ),
    )

    ebitda = _safe_number(info.get("ebitda"))

    if ebitda is None:
        ebitda = _statement_value(
            income_statement,
            (
                "EBITDA",
                "Normalized EBITDA",
            ),
        )

    gross_profit = _safe_number(info.get("grossProfits"))

    if gross_profit is None:
        gross_profit = _statement_value(
            income_statement,
            ("Gross Profit",),
        )

    # -------------------------------------------------------------------------
    # BALANCE SHEET DATA
    # -------------------------------------------------------------------------

    total_cash = _safe_number(info.get("totalCash"))

    if total_cash is None:
        total_cash = _statement_value(
            balance_sheet,
            (
                "Cash Cash Equivalents And Short Term Investments",
                "Cash And Cash Equivalents",
                "Cash Financial",
            ),
        )

    total_debt = _safe_number(info.get("totalDebt"))

    if total_debt is None:
        total_debt = _statement_value(
            balance_sheet,
            (
                "Total Debt",
                "Long Term Debt And Capital Lease Obligation",
            ),
        )

    total_assets = _statement_value(
        balance_sheet,
        ("Total Assets",),
    )

    total_liabilities = _statement_value(
        balance_sheet,
        (
            "Total Liabilities Net Minority Interest",
            "Total Liabilities",
        ),
    )

    stockholders_equity = _statement_value(
        balance_sheet,
        (
            "Stockholders Equity",
            "Total Equity Gross Minority Interest",
            "Common Stock Equity",
        ),
    )

    current_assets = _statement_value(
        balance_sheet,
        (
            "Current Assets",
            "Total Current Assets",
        ),
    )

    current_liabilities = _statement_value(
        balance_sheet,
        (
            "Current Liabilities",
            "Total Current Liabilities",
        ),
    )

    inventory = _statement_value(
        balance_sheet,
        (
            "Inventory",
            "Inventories",
        ),
    )

    # -------------------------------------------------------------------------
    # CASH FLOW DATA
    # -------------------------------------------------------------------------

    operating_cash_flow = _safe_number(
        info.get("operatingCashflow")
    )

    if operating_cash_flow is None:
        operating_cash_flow = _statement_value(
            cash_flow_statement,
            (
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
                "Net Cash Provided By Operating Activities",
            ),
        )

    capital_expenditures = _statement_value(
        cash_flow_statement,
        (
            "Capital Expenditure",
            "Capital Expenditures",
            "Purchase Of PPE",
            "Purchase Of Property Plant And Equipment",
        ),
    )

    free_cash_flow = _statement_value(
        cash_flow_statement,
        (
            "Free Cash Flow",
            "FreeCashFlow",
        ),
    )

    if (
        free_cash_flow is None
        and operating_cash_flow is not None
        and capital_expenditures is not None
    ):
        free_cash_flow = (
            operating_cash_flow + capital_expenditures
            if capital_expenditures < 0
            else operating_cash_flow - capital_expenditures
        )

    if free_cash_flow is None:
        free_cash_flow = _safe_number(
            info.get("freeCashflow")
        )

    # -------------------------------------------------------------------------
    # CALCULATED RATIOS
    # -------------------------------------------------------------------------

    profit_margin = _safe_number(info.get("profitMargins"))

    if (
        profit_margin is None
        and revenue not in (None, 0)
        and net_income is not None
    ):
        profit_margin = net_income / revenue

    operating_margin = _safe_number(
        info.get("operatingMargins")
    )

    if (
        operating_margin is None
        and revenue not in (None, 0)
        and operating_income is not None
    ):
        operating_margin = operating_income / revenue

    gross_margin = _safe_number(info.get("grossMargins"))

    if (
        gross_margin is None
        and revenue not in (None, 0)
        and gross_profit is not None
    ):
        gross_margin = gross_profit / revenue

    return_on_equity = _safe_number(
        info.get("returnOnEquity")
    )

    if (
        return_on_equity is None
        and stockholders_equity not in (None, 0)
        and net_income is not None
    ):
        return_on_equity = net_income / stockholders_equity

    return_on_assets = _safe_number(
        info.get("returnOnAssets")
    )

    if (
        return_on_assets is None
        and total_assets not in (None, 0)
        and net_income is not None
    ):
        return_on_assets = net_income / total_assets

    current_ratio = _safe_number(info.get("currentRatio"))

    if (
        current_ratio is None
        and current_liabilities not in (None, 0)
        and current_assets is not None
    ):
        current_ratio = current_assets / current_liabilities

    quick_ratio = _safe_number(info.get("quickRatio"))

    if (
        quick_ratio is None
        and current_liabilities not in (None, 0)
        and current_assets is not None
    ):
        quick_assets = current_assets

        if inventory is not None:
            quick_assets -= inventory

        quick_ratio = quick_assets / current_liabilities

    debt_to_equity_raw = _safe_number(
        info.get("debtToEquity")
    )

    debt_to_equity = None

    if debt_to_equity_raw is not None:
        # Yahoo normally returns debtToEquity as a percentage,
        # for example 6.55 means 0.0655x.
        debt_to_equity = debt_to_equity_raw / 100
    elif (
        total_debt is not None
        and stockholders_equity not in (None, 0)
    ):
        debt_to_equity = total_debt / stockholders_equity

    cash_per_share = _safe_number(info.get("totalCashPerShare"))

    if (
        cash_per_share is None
        and total_cash is not None
    ):
        shares = _safe_number(info.get("sharesOutstanding"))

        if shares not in (None, 0):
            cash_per_share = total_cash / shares

    market_cap = _safe_number(info.get("marketCap"))
    price_to_book = _safe_number(info.get("priceToBook"))

    if (
        price_to_book is None
        and market_cap is not None
        and stockholders_equity not in (None, 0)
    ):
        price_to_book = market_cap / stockholders_equity

    revenue_growth = _safe_number(info.get("revenueGrowth"))
    earnings_growth = _safe_number(info.get("earningsGrowth"))
    earnings_quarterly_growth = _safe_number(
        info.get("earningsQuarterlyGrowth")
    )

    # -------------------------------------------------------------------------
    # DIVIDEND NORMALIZATION
    # -------------------------------------------------------------------------

    dividend_yield = _safe_number(info.get("dividendYield"))

    if dividend_yield is not None and dividend_yield > 0.20:
        # Some Yahoo responses can expose 0.48 instead of 0.0048.
        dividend_yield = dividend_yield / 100

    # -------------------------------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------------------------------

    return {
        "ticker": ticker_symbol,
        "company_name": info.get(
            "longName",
            info.get("shortName", ticker_symbol),
        ),
        "exchange": info.get("exchange"),
        "currency": info.get("currency", "USD"),
        "quote_type": info.get("quoteType"),
        "website": info.get("website"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "country": info.get("country"),
        "employees": info.get("fullTimeEmployees"),
        "business_summary": info.get(
            "longBusinessSummary"
        ),

        "current_price": current_price,
        "previous_close": previous_close,
        "daily_change": daily_change,
        "daily_change_percent": daily_change_percent,
        "market_cap": market_cap,
        "shares_outstanding": _safe_number(
            info.get("sharesOutstanding")
        ),
        "float_shares": _safe_number(
            info.get("floatShares")
        ),
        "average_volume": _safe_number(
            info.get("averageVolume")
        ),
        "volume": _safe_number(info.get("volume")),

        "enterprise_value": _safe_number(
            info.get("enterpriseValue")
        ),
        "trailing_pe": _safe_number(
            info.get("trailingPE")
        ),
        "forward_pe": _safe_number(
            info.get("forwardPE")
        ),
        "peg_ratio": _safe_number(
            info.get("pegRatio")
        ),
        "price_to_book": price_to_book,
        "price_to_sales": _safe_number(
            info.get("priceToSalesTrailing12Months")
        ),
        "enterprise_to_revenue": _safe_number(
            info.get("enterpriseToRevenue")
        ),
        "enterprise_to_ebitda": _safe_number(
            info.get("enterpriseToEbitda")
        ),
        "beta": _safe_number(info.get("beta")),

        "revenue": revenue,
        "net_income": net_income,
        "gross_profit": gross_profit,
        "operating_income": operating_income,
        "ebit": ebit,
        "ebitda": ebitda,

        "profit_margin": profit_margin,
        "operating_margin": operating_margin,
        "gross_margin": gross_margin,
        "ebitda_margin": _safe_number(
            info.get("ebitdaMargins")
        ),
        "return_on_equity": return_on_equity,
        "return_on_assets": return_on_assets,

        "total_cash": total_cash,
        "total_debt": total_debt,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "stockholders_equity": stockholders_equity,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "inventory": inventory,

        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "cash_per_share": cash_per_share,

        "operating_cash_flow": operating_cash_flow,
        "capital_expenditures": capital_expenditures,
        "free_cash_flow": free_cash_flow,

        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "earnings_quarterly_growth": earnings_quarterly_growth,

        "dividend_rate": _safe_number(
            info.get("dividendRate")
        ),
        "dividend_yield": dividend_yield,
        "payout_ratio": _safe_number(
            info.get("payoutRatio")
        ),
        "five_year_average_dividend_yield": _safe_number(
            info.get("fiveYearAvgDividendYield")
        ),

        "fifty_two_week_high": _safe_number(
            info.get("fiftyTwoWeekHigh")
        ) or one_year_high,
        "fifty_two_week_low": _safe_number(
            info.get("fiftyTwoWeekLow")
        ) or one_year_low,
        "one_year_return": one_year_return,
        "one_year_high": one_year_high,
        "one_year_low": one_year_low,

        "target_high_price": _safe_number(
            info.get("targetHighPrice")
        ),
        "target_low_price": _safe_number(
            info.get("targetLowPrice")
        ),
        "target_mean_price": _safe_number(
            info.get("targetMeanPrice")
        ),
        "target_median_price": _safe_number(
            info.get("targetMedianPrice")
        ),
        "analyst_recommendation": info.get(
            "recommendationKey"
        ),
        "analyst_recommendation_mean": _safe_number(
            info.get("recommendationMean")
        ),
        "number_of_analyst_opinions": _safe_number(
            info.get("numberOfAnalystOpinions")
        ),
    }