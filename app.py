from __future__ import annotations

import inspect
import importlib
import math
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Finance AI Research Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# MODULE LOADING
# =============================================================================

MODULE_NAMES = (
    "ai_analysis",
    "ai_news",
    "investment_recommendation",
    "comparison",
    "ai_comparison",
    "dcf_model",
    "dcf_scenarios",
    "dcf_sensitivity",
    "financial_score",
    "market_data",
    "company_news",
)


@st.cache_resource(show_spinner=False)
def load_project_modules() -> dict[str, Any]:
    modules: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for module_name in MODULE_NAMES:
        try:
            modules[module_name] = importlib.import_module(module_name)
        except Exception as exc:
            modules[module_name] = None
            errors[module_name] = f"{type(exc).__name__}: {exc}"

    modules["_errors"] = errors
    return modules


MODULES = load_project_modules()


# =============================================================================
# GENERIC HELPERS
# =============================================================================

Number = Optional[Union[int, float]]


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def clean_ticker(value: str) -> str:
    return "".join(value.strip().upper().split())


def first_present(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return {}


def format_currency(value: Number, decimals: int = 2) -> str:
    if not is_number(value):
        return "N/A"
    return f"${float(value):,.{decimals}f}"


def format_large_number(value: Number) -> str:
    if not is_number(value):
        return "N/A"

    number = float(value)
    absolute = abs(number)

    if absolute >= 1_000_000_000_000:
        return f"${number / 1_000_000_000_000:.2f}T"
    if absolute >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"${number / 1_000:.2f}K"
    return f"${number:,.2f}"


def format_number(value: Number, decimals: int = 2) -> str:
    if not is_number(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def format_multiple(value: Number) -> str:
    if not is_number(value):
        return "N/A"
    return f"{float(value):.2f}x"


def normalize_percent(value: Number) -> Optional[float]:
    """Convert decimal ratios such as 0.25 into 25.00 for display."""
    if not is_number(value):
        return None

    number = float(value)
    if abs(number) <= 1.5:
        return number * 100
    return number


def format_percent(value: Number) -> str:
    normalized = normalize_percent(value)
    if normalized is None:
        return "N/A"
    return f"{normalized:.2f}%"


def format_dividend_yield(value: Number) -> str:
    """Handle Yahoo values returned as either 0.0048 or 0.48 for 0.48%."""
    if not is_number(value):
        return "N/A"

    number = float(value)
    if abs(number) > 0.20:
        number /= 100

    return f"{number * 100:.2f}%"


def format_debt_to_equity(value: Number) -> str:
    """Handle Yahoo debtToEquity values such as 6.55, meaning 0.0655x."""
    if not is_number(value):
        return "N/A"

    number = float(value)
    if abs(number) > 1:
        number /= 100

    return f"{number:.2f}x"


def calculate_upside(fair_value: Number, current_price: Number) -> Optional[float]:
    if not is_number(fair_value) or not is_number(current_price):
        return None
    if float(current_price) <= 0:
        return None
    return (float(fair_value) / float(current_price) - 1) * 100


def get_callable(module_name: str, candidates: Sequence[str]) -> Optional[Callable[..., Any]]:
    module = MODULES.get(module_name)
    if module is None:
        return None

    for name in candidates:
        function = getattr(module, name, None)
        if callable(function):
            return function

    public_functions = [
        member
        for name, member in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_") and member.__module__ == module.__name__
    ]

    if len(public_functions) == 1:
        return public_functions[0]

    return None


def call_compatible(
    function: Callable[..., Any],
    context: Mapping[str, Any],
    positional_attempts: Sequence[Sequence[Any]] = (),
) -> Any:
    """
    Call a project function while accommodating common parameter-name variations.
    The function's real signature is inspected first. If that cannot fully resolve
    the call, several explicit positional forms are attempted.
    """
    signature = inspect.signature(function)
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    unresolved_required: list[str] = []

    aliases: dict[str, tuple[str, ...]] = {
        "ticker": ("ticker", "ticker_symbol", "symbol"),
        "ticker_symbol": ("ticker_symbol", "ticker", "symbol"),
        "symbol": ("symbol", "ticker", "ticker_symbol"),
        "data": ("data", "stock_data", "company_data", "financial_data"),
        "stock_data": ("stock_data", "data", "company_data", "financial_data"),
        "company_data": ("company_data", "stock_data", "data", "financial_data"),
        "financial_data": ("financial_data", "stock_data", "company_data", "data"),
        "scores": ("scores", "financial_scores", "score"),
        "financial_scores": ("financial_scores", "scores", "score"),
        "news": ("news", "news_items", "articles", "company_news"),
        "news_items": ("news_items", "news", "articles", "company_news"),
        "articles": ("articles", "news", "news_items", "company_news"),
        "company_news": ("company_news", "news", "news_items", "articles"),
        "company_1": ("company_1", "first_company", "company1", "data_1", "first_data"),
        "company_2": ("company_2", "second_company", "company2", "data_2", "second_data"),
        "first_company": ("first_company", "company_1", "company1", "data_1", "first_data"),
        "second_company": ("second_company", "company_2", "company2", "data_2", "second_data"),
        "first_scores": ("first_scores", "scores_1", "company_1_scores"),
        "second_scores": ("second_scores", "scores_2", "company_2_scores"),
        "growth_rate": ("growth_rate", "fcf_growth_rate", "annual_growth_rate"),
        "fcf_growth_rate": ("fcf_growth_rate", "growth_rate", "annual_growth_rate"),
        "discount_rate": ("discount_rate", "wacc", "required_return"),
        "terminal_growth_rate": ("terminal_growth_rate", "terminal_rate", "perpetual_growth_rate"),
        "years": ("years", "projection_years", "forecast_years"),
        "projection_years": ("projection_years", "years", "forecast_years"),
        "base_growth_rate": ("base_growth_rate", "growth_rate", "fcf_growth_rate"),
        "base_discount_rate": ("base_discount_rate", "discount_rate", "wacc"),
    }

    for parameter in signature.parameters.values():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        lookup_names = aliases.get(parameter.name, (parameter.name,))
        matched = False

        for lookup_name in lookup_names:
            if lookup_name in context:
                value = context[lookup_name]
                if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(value)
                else:
                    kwargs[parameter.name] = value
                matched = True
                break

        if not matched and parameter.default is inspect.Parameter.empty:
            unresolved_required.append(parameter.name)

    if not unresolved_required:
        return function(*args, **kwargs)

    last_error: Optional[Exception] = None
    for attempt in positional_attempts:
        try:
            return function(*attempt)
        except TypeError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise TypeError(
        f"Could not resolve required parameters for {function.__module__}."
        f"{function.__name__}: {', '.join(unresolved_required)}"
    )


def module_status_table() -> pd.DataFrame:
    errors = MODULES.get("_errors", {})
    rows = []

    for name in MODULE_NAMES:
        available = MODULES.get(name) is not None
        rows.append(
            {
                "Module": name,
                "Status": "Loaded" if available else "Unavailable",
                "Details": "" if available else errors.get(name, "Import failed"),
            }
        )

    return pd.DataFrame(rows)


def render_text_result(result: Any) -> None:
    if result is None:
        st.info("The module completed but returned no displayable result.")
    elif isinstance(result, str):
        st.markdown(result)
    elif isinstance(result, pd.DataFrame):
        st.dataframe(result, use_container_width=True)
    elif isinstance(result, Mapping):
        st.json(dict(result))
    elif isinstance(result, (list, tuple)):
        if all(isinstance(item, Mapping) for item in result):
            st.dataframe(pd.DataFrame(result), use_container_width=True)
        else:
            for item in result:
                st.write(item)
    else:
        st.write(result)


# =============================================================================
# DATA ACCESS LAYER
# =============================================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_company_data(ticker: str) -> dict[str, Any]:
    function = get_callable(
        "market_data",
        (
            "get_stock_data",
            "get_market_data",
            "fetch_stock_data",
            "fetch_market_data",
            "get_company_data",
        ),
    )
    if function is None:
        raise RuntimeError(
            "market_data.py loaded, but no supported market-data function was found."
        )

    result = call_compatible(
        function,
        {"ticker": ticker, "ticker_symbol": ticker, "symbol": ticker},
        positional_attempts=((ticker,),),
    )
    data = as_mapping(result)

    if not data:
        raise ValueError(f"No market data was returned for {ticker}.")

    data.setdefault("ticker", ticker)
    data.setdefault(
        "company_name",
        first_present(data, "long_name", "short_name", "name", default=ticker),
    )
    return data


@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(ticker: str, period: str) -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    history = stock.history(period=period, auto_adjust=False)

    if history is None or history.empty:
        return pd.DataFrame()

    history = history.copy()
    history.index = pd.to_datetime(history.index)
    return history


@st.cache_data(ttl=900, show_spinner=False)
def get_financial_statements(
    ticker: str,
    frequency: str,
) -> dict[str, pd.DataFrame]:
    """
    Fetch annual or quarterly company statements with multiple yfinance
    fallbacks so the feature continues working across yfinance versions.
    """
    stock = yf.Ticker(ticker)
    freq = "quarterly" if frequency == "quarterly" else "yearly"

    def fetch_statement(
        method_name: str,
        annual_attribute: str,
        quarterly_attribute: str,
    ) -> pd.DataFrame:
        statement = pd.DataFrame()

        method = getattr(stock, method_name, None)
        if callable(method):
            try:
                statement = method(freq=freq)
            except TypeError:
                try:
                    statement = method()
                except Exception:
                    statement = pd.DataFrame()
            except Exception:
                statement = pd.DataFrame()

        if not isinstance(statement, pd.DataFrame) or statement.empty:
            attribute_name = (
                quarterly_attribute
                if frequency == "quarterly"
                else annual_attribute
            )
            try:
                statement = getattr(stock, attribute_name)
            except Exception:
                statement = pd.DataFrame()

        if not isinstance(statement, pd.DataFrame) or statement.empty:
            return pd.DataFrame()

        prepared = statement.copy()

        prepared.columns = [
            pd.to_datetime(column).strftime("%Y-%m-%d")
            if not isinstance(column, str)
            else column
            for column in prepared.columns
        ]

        prepared.index = [
            str(index)
            .replace("_", " ")
            .replace("  ", " ")
            .strip()
            for index in prepared.index
        ]

        prepared = prepared.dropna(axis=0, how="all")
        prepared = prepared.dropna(axis=1, how="all")
        return prepared

    return {
        "Income Statement": fetch_statement(
            "get_income_stmt",
            "financials",
            "quarterly_financials",
        ),
        "Balance Sheet": fetch_statement(
            "get_balance_sheet",
            "balance_sheet",
            "quarterly_balance_sheet",
        ),
        "Cash Flow Statement": fetch_statement(
            "get_cash_flow",
            "cashflow",
            "quarterly_cashflow",
        ),
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_financial_trends(ticker: str) -> pd.DataFrame:
    """Build annual financial trend data from yfinance statements."""
    stock = yf.Ticker(ticker)

    try:
        income = stock.get_income_stmt(freq="yearly")
    except Exception:
        income = getattr(stock, "financials", pd.DataFrame())

    try:
        cash_flow = stock.get_cash_flow(freq="yearly")
    except Exception:
        cash_flow = getattr(stock, "cashflow", pd.DataFrame())

    if not isinstance(income, pd.DataFrame):
        income = pd.DataFrame()

    if not isinstance(cash_flow, pd.DataFrame):
        cash_flow = pd.DataFrame()

    def row_values(frame: pd.DataFrame, candidates: tuple[str, ...]) -> pd.Series:
        if frame.empty:
            return pd.Series(dtype="float64")

        for candidate in candidates:
            if candidate in frame.index:
                values = pd.to_numeric(frame.loc[candidate], errors="coerce")
                values.index = pd.to_datetime(values.index)
                return values

        normalized_index = {
            str(index).replace(" ", "").replace("_", "").lower(): index
            for index in frame.index
        }

        for candidate in candidates:
            normalized_candidate = (
                candidate.replace(" ", "").replace("_", "").lower()
            )
            matched = normalized_index.get(normalized_candidate)
            if matched is not None:
                values = pd.to_numeric(frame.loc[matched], errors="coerce")
                values.index = pd.to_datetime(values.index)
                return values

        return pd.Series(dtype="float64")

    revenue = row_values(
        income,
        ("TotalRevenue", "OperatingRevenue"),
    )
    net_income = row_values(
        income,
        ("NetIncome", "NetIncomeCommonStockholders"),
    )
    ebitda = row_values(
        income,
        ("EBITDA", "NormalizedEBITDA"),
    )
    diluted_eps = row_values(
        income,
        ("DilutedEPS", "BasicEPS"),
    )
    gross_profit = row_values(
        income,
        ("GrossProfit",),
    )
    operating_income = row_values(
        income,
        ("OperatingIncome", "TotalOperatingIncomeAsReported"),
    )
    free_cash_flow = row_values(
        cash_flow,
        ("FreeCashFlow",),
    )

    all_dates = sorted(
        set(revenue.index)
        | set(net_income.index)
        | set(ebitda.index)
        | set(diluted_eps.index)
        | set(gross_profit.index)
        | set(operating_income.index)
        | set(free_cash_flow.index)
    )

    if not all_dates:
        return pd.DataFrame()

    trends = pd.DataFrame(index=all_dates)
    trends.index.name = "Date"

    trends["Revenue"] = revenue.reindex(all_dates)
    trends["Net Income"] = net_income.reindex(all_dates)
    trends["EBITDA"] = ebitda.reindex(all_dates)
    trends["Diluted EPS"] = diluted_eps.reindex(all_dates)
    trends["Free Cash Flow"] = free_cash_flow.reindex(all_dates)

    revenue_safe = trends["Revenue"].replace(0, pd.NA)
    trends["Gross Margin"] = (
        gross_profit.reindex(all_dates) / revenue_safe * 100
    )
    trends["Operating Margin"] = (
        operating_income.reindex(all_dates) / revenue_safe * 100
    )

    trends = trends.sort_index()
    return trends


@st.cache_data(ttl=900, show_spinner=False)
def get_analyst_estimates(ticker: str) -> dict[str, Any]:
    """
    Fetch analyst recommendations, price targets, and forward estimates
    using yfinance with version-compatible fallbacks.
    """
    stock = yf.Ticker(ticker)
    info = {}

    try:
        info = stock.get_info()
    except Exception:
        try:
            info = stock.info
        except Exception:
            info = {}

    if not isinstance(info, Mapping):
        info = {}

    current_price = first_present(
        info,
        "currentPrice",
        "regularMarketPrice",
        "previousClose",
    )
    target_mean = first_present(info, "targetMeanPrice")
    target_high = first_present(info, "targetHighPrice")
    target_low = first_present(info, "targetLowPrice")
    target_median = first_present(info, "targetMedianPrice")
    recommendation_key = first_present(info, "recommendationKey")
    analyst_count = first_present(info, "numberOfAnalystOpinions")

    recommendation_summary = pd.DataFrame()
    recommendations = pd.DataFrame()
    revenue_estimates = pd.DataFrame()
    earnings_estimates = pd.DataFrame()

    try:
        recommendation_summary = stock.recommendations_summary
    except Exception:
        recommendation_summary = pd.DataFrame()

    try:
        recommendations = stock.recommendations
    except Exception:
        recommendations = pd.DataFrame()

    try:
        revenue_estimates = stock.revenue_estimate
    except Exception:
        try:
            revenue_estimates = stock.get_revenue_estimate()
        except Exception:
            revenue_estimates = pd.DataFrame()

    try:
        earnings_estimates = stock.earnings_estimate
    except Exception:
        try:
            earnings_estimates = stock.get_earnings_estimate()
        except Exception:
            earnings_estimates = pd.DataFrame()

    def safe_dataframe(value: Any) -> pd.DataFrame:
        if not isinstance(value, pd.DataFrame):
            return pd.DataFrame()
        return value.copy()

    return {
        "current_price": current_price,
        "target_mean": target_mean,
        "target_high": target_high,
        "target_low": target_low,
        "target_median": target_median,
        "recommendation_key": recommendation_key,
        "analyst_count": analyst_count,
        "recommendation_summary": safe_dataframe(recommendation_summary),
        "recommendations": safe_dataframe(recommendations),
        "revenue_estimates": safe_dataframe(revenue_estimates),
        "earnings_estimates": safe_dataframe(earnings_estimates),
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_news_items(ticker: str, company_data: Mapping[str, Any]) -> Any:
    function = get_callable(
        "company_news",
        (
            "get_company_news",
            "fetch_company_news",
            "get_news",
            "fetch_news",
            "company_news",
        ),
    )
    if function is None:
        raise RuntimeError(
            "company_news.py loaded, but no supported news-fetching function was found."
        )

    company_name = first_present(company_data, "company_name", "name", default=ticker)
    context = {
        "ticker": ticker,
        "ticker_symbol": ticker,
        "symbol": ticker,
        "data": company_data,
        "company_data": company_data,
        "stock_data": company_data,
        "company_name": company_name,
    }

    return call_compatible(
        function,
        context,
        positional_attempts=((ticker,), (company_name,), (ticker, company_name)),
    )


def calculate_scores(company_data: Mapping[str, Any]) -> dict[str, Any]:
    function = get_callable(
        "financial_score",
        (
            "calculate_financial_scores",
            "calculate_financial_score",
            "get_financial_scores",
            "score_company",
        ),
    )
    if function is None:
        raise RuntimeError(
            "financial_score.py loaded, but no supported scoring function was found."
        )

    result = call_compatible(
        function,
        {
            "data": company_data,
            "stock_data": company_data,
            "company_data": company_data,
            "financial_data": company_data,
        },
        positional_attempts=((company_data,),),
    )
    return as_mapping(result)


# =============================================================================
# MODULE-SPECIFIC CALLS
# =============================================================================

def generate_analysis(company_data: Mapping[str, Any], scores: Mapping[str, Any]) -> Any:
    function = get_callable(
        "ai_analysis",
        (
            "generate_ai_analysis",
            "generate_analysis",
            "analyze_company",
            "create_ai_analysis",
        ),
    )
    if function is None:
        raise RuntimeError(
            "ai_analysis.py loaded, but no supported analysis function was found."
        )

    return call_compatible(
        function,
        {
            "data": company_data,
            "stock_data": company_data,
            "company_data": company_data,
            "financial_data": company_data,
            "scores": scores,
            "financial_scores": scores,
        },
        positional_attempts=((company_data,), (company_data, scores)),
    )


def generate_news_analysis(
    company_data: Mapping[str, Any],
    news_items: Any,
) -> Any:
    function = get_callable(
        "ai_news",
        (
            "generate_ai_news_analysis",
            "analyze_news_with_ai",
            "generate_news_analysis",
            "analyze_news",
            "generate_ai_news",
        ),
    )
    if function is None:
        raise RuntimeError(
            "ai_news.py loaded, but no supported AI-news function was found."
        )

    return call_compatible(
        function,
        {
            "data": company_data,
            "stock_data": company_data,
            "company_data": company_data,
            "news": news_items,
            "news_items": news_items,
            "articles": news_items,
            "company_news": news_items,
            "news_articles": news_items,
            "ticker": first_present(company_data, "ticker"),
            "ticker_symbol": first_present(company_data, "ticker"),
            "company_name": first_present(company_data, "company_name", "name"),
        },
        positional_attempts=(
            (news_items,),
            (company_data, news_items),
            (first_present(company_data, "ticker"), news_items),
        ),
    )


def generate_recommendation(
    company_data: Mapping[str, Any],
    scores: Mapping[str, Any],
    analysis: Any = None,
    news_analysis: Any = None,
) -> Any:
    function = get_callable(
        "investment_recommendation",
        (
            "generate_investment_recommendation",
            "get_investment_recommendation",
            "create_investment_recommendation",
            "generate_recommendation",
            "recommend_investment",
        ),
    )
    if function is None:
        raise RuntimeError(
            "investment_recommendation.py loaded, but no supported recommendation function was found."
        )

    context = {
        "data": company_data,
        "stock_data": company_data,
        "company_data": company_data,
        "financial_data": company_data,
        "scores": scores,
        "financial_scores": scores,
        "analysis": analysis,
        "ai_analysis": analysis,
        "news_analysis": news_analysis,
        "ai_news_analysis": news_analysis,
    }

    return call_compatible(
        function,
        context,
        positional_attempts=(
            (company_data,),
            (company_data, scores),
            (company_data, scores, analysis),
            (company_data, scores, analysis, news_analysis),
        ),
    )


def run_comparison(
    first_company: Mapping[str, Any],
    second_company: Mapping[str, Any],
) -> Any:
    function = get_callable(
        "comparison",
        (
            "compare_companies",
            "compare_stocks",
            "build_comparison",
            "company_comparison",
        ),
    )
    if function is None:
        raise RuntimeError(
            "comparison.py loaded, but no supported comparison function was found."
        )

    return call_compatible(
        function,
        {
            "company_1": first_company,
            "company_2": second_company,
            "first_company": first_company,
            "second_company": second_company,
            "data_1": first_company,
            "data_2": second_company,
        },
        positional_attempts=((first_company, second_company),),
    )


def run_ai_comparison(
    first_company: Mapping[str, Any],
    second_company: Mapping[str, Any],
    first_scores: Mapping[str, Any],
    second_scores: Mapping[str, Any],
) -> Any:
    function = get_callable(
        "ai_comparison",
        (
            "generate_ai_comparison",
            "compare_companies_with_ai",
            "generate_comparison_analysis",
            "analyze_comparison",
        ),
    )
    if function is None:
        raise RuntimeError(
            "ai_comparison.py loaded, but no supported AI-comparison function was found."
        )

    context = {
        "company_1": first_company,
        "company_2": second_company,
        "first_company": first_company,
        "second_company": second_company,
        "data_1": first_company,
        "data_2": second_company,
        "first_scores": first_scores,
        "second_scores": second_scores,
        "scores_1": first_scores,
        "scores_2": second_scores,
    }

    return call_compatible(
        function,
        context,
        positional_attempts=(
            (first_company, second_company),
            (first_company, second_company, first_scores, second_scores),
        ),
    )


def run_dcf(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int,
) -> Any:
    function = get_callable(
        "dcf_model",
        (
            "calculate_dcf",
            "run_dcf",
            "dcf_valuation",
            "calculate_dcf_valuation",
        ),
    )

    if function is None:
        raise RuntimeError(
            "dcf_model.py loaded, but no supported DCF function was found."
        )

    def get_first_number(*keys: str) -> Optional[float]:
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

    free_cash_flow = get_first_number(
        "free_cash_flow",
        "freeCashflow",
        "freeCashFlow",
        "fcf",
    )

    shares_outstanding = get_first_number(
        "shares_outstanding",
        "sharesOutstanding",
        "shares",
        "impliedSharesOutstanding",
    )

    total_cash = get_first_number(
        "total_cash",
        "totalCash",
        "cash",
        "cashAndCashEquivalents",
    )

    total_debt = get_first_number(
        "total_debt",
        "totalDebt",
        "debt",
    )

    if free_cash_flow is None:
        raise ValueError(
            "Free cash flow could not be found in the company data."
        )

    if shares_outstanding is None:
        raise ValueError(
            "Shares outstanding could not be found in the company data."
        )

    return function(
        free_cash_flow=free_cash_flow,
        shares_outstanding=shares_outstanding,
        total_cash=total_cash,
        total_debt=total_debt,
        growth_rate=growth_rate,
        discount_rate=discount_rate,
        terminal_growth_rate=terminal_growth_rate,
        forecast_years=years,
    )

def run_dcf_scenarios(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int,
) -> Any:
    function = get_callable(
        "dcf_scenarios",
        (
            "calculate_dcf_scenarios",
            "run_dcf_scenarios",
            "generate_dcf_scenarios",
            "scenario_analysis",
        ),
    )
    if function is None:
        raise RuntimeError(
            "dcf_scenarios.py loaded, but no supported scenario function was found."
        )

    context = {
        "data": company_data,
        "stock_data": company_data,
        "company_data": company_data,
        "growth_rate": growth_rate,
        "base_growth_rate": growth_rate,
        "discount_rate": discount_rate,
        "base_discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "years": years,
        "projection_years": years,
    }

    return call_compatible(
        function,
        context,
        positional_attempts=(
            (company_data,),
            (company_data, growth_rate, discount_rate, terminal_growth_rate),
            (company_data, growth_rate, discount_rate, terminal_growth_rate, years),
        ),
    )


def run_dcf_sensitivity(
    company_data: Mapping[str, Any],
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int,
) -> Any:
    function = get_callable(
        "dcf_sensitivity",
        (
            "calculate_sensitivity_table",
            "calculate_dcf_sensitivity",
            "run_sensitivity_analysis",
            "generate_sensitivity_table",
        ),
    )
    if function is None:
        raise RuntimeError(
            "dcf_sensitivity.py loaded, but no supported sensitivity function was found."
        )

    context = {
        "data": company_data,
        "stock_data": company_data,
        "company_data": company_data,
        "growth_rate": growth_rate,
        "base_growth_rate": growth_rate,
        "discount_rate": discount_rate,
        "base_discount_rate": discount_rate,
        "terminal_growth_rate": terminal_growth_rate,
        "years": years,
        "projection_years": years,
    }

    return call_compatible(
        function,
        context,
        positional_attempts=(
            (company_data,),
            (company_data, growth_rate, discount_rate, terminal_growth_rate),
            (company_data, growth_rate, discount_rate, terminal_growth_rate, years),
        ),
    )


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def render_scorecard(scores: Mapping[str, Any]) -> None:
    score_keys = [
        ("overall", "Overall"),
        ("profitability", "Profitability"),
        ("balance_sheet", "Balance Sheet"),
        ("valuation", "Valuation"),
        ("market_performance", "Market Performance"),
    ]

    columns = st.columns(len(score_keys))

    for column, (key, label) in zip(columns, score_keys):
        value = first_present(scores, key, key.replace("_", " "), default=None)
        if is_number(value):
            column.metric(label, f"{float(value):.0f} / 100")
        else:
            column.metric(label, "N/A")


def render_price_chart(history: pd.DataFrame, ticker: str) -> None:
    if history.empty or "Close" not in history.columns:
        st.warning("Price history was not available.")
        return

    chart_data = history.copy()
    chart_data = chart_data.dropna(subset=["Close"])

    if chart_data.empty:
        st.warning("Price history was not available.")
        return

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data["Close"],
            mode="lines",
            name=ticker,
            line={"width": 2.5},
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Close: $%{y:,.2f}<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        title=f"{ticker} Price History",
        hovermode="x unified",
        margin={"l": 10, "r": 10, "t": 55, "b": 10},
        height=430,
        xaxis_title="Date",
        yaxis_title="Price",
        legend_title_text="Ticker",
    )

    figure.update_xaxes(
        rangeslider_visible=False,
        rangeselector={
            "buttons": [
                {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                {"step": "all", "label": "All"},
            ]
        },
    )

    st.plotly_chart(figure, width="stretch")


def render_financial_overview(data: Mapping[str, Any]) -> None:
    """Render all financial metrics without allowing one missing value to stop the section."""
    valuation, profitability, health = st.columns(3)

    with valuation:
        st.markdown("#### Valuation")
        st.write(
            f"**Enterprise Value:** "
            f"{format_large_number(first_present(data, 'enterprise_value'))}"
        )
        st.write(
            f"**Trailing P/E:** "
            f"{format_number(first_present(data, 'trailing_pe'))}"
        )
        st.write(
            f"**Forward P/E:** "
            f"{format_number(first_present(data, 'forward_pe'))}"
        )
        st.write(
            f"**PEG Ratio:** "
            f"{format_number(first_present(data, 'peg_ratio'))}"
        )
        st.write(
            f"**Price / Book:** "
            f"{format_number(first_present(data, 'price_to_book'))}"
        )
        st.write(
            f"**Beta:** "
            f"{format_number(first_present(data, 'beta'))}"
        )
        st.write(
            f"**Dividend Yield:** "
            f"{format_dividend_yield(first_present(data, 'dividend_yield'))}"
        )

    with profitability:
        st.markdown("#### Profitability")
        st.write(
            f"**Revenue:** "
            f"{format_large_number(first_present(data, 'revenue', 'total_revenue'))}"
        )
        st.write(
            f"**Net Income:** "
            f"{format_large_number(first_present(data, 'net_income'))}"
        )
        st.write(
            f"**EBITDA:** "
            f"{format_large_number(first_present(data, 'ebitda'))}"
        )
        st.write(
            f"**Profit Margin:** "
            f"{format_percent(first_present(data, 'profit_margin'))}"
        )
        st.write(
            f"**Operating Margin:** "
            f"{format_percent(first_present(data, 'operating_margin'))}"
        )
        st.write(
            f"**Return on Equity:** "
            f"{format_percent(first_present(data, 'return_on_equity'))}"
        )
        st.write(
            f"**Return on Assets:** "
            f"{format_percent(first_present(data, 'return_on_assets'))}"
        )

    with health:
        st.markdown("#### Financial Health")
        st.write(
            f"**Total Cash:** "
            f"{format_large_number(first_present(data, 'total_cash'))}"
        )
        st.write(
            f"**Total Debt:** "
            f"{format_large_number(first_present(data, 'total_debt'))}"
        )
        st.write(
            f"**Debt / Equity:** "
            f"{format_debt_to_equity(first_present(data, 'debt_to_equity'))}"
        )
        st.write(
            f"**Current Ratio:** "
            f"{format_number(first_present(data, 'current_ratio'))}"
        )
        st.write(
            f"**Quick Ratio:** "
            f"{format_number(first_present(data, 'quick_ratio'))}"
        )
        st.write(
            f"**Operating Cash Flow:** "
            f"{format_large_number(first_present(data, 'operating_cash_flow'))}"
        )
        st.write(
            f"**Free Cash Flow:** "
            f"{format_large_number(first_present(data, 'free_cash_flow'))}"
        )


def format_statement_value(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if is_number(value):
        return f"{float(value):,.0f}"
    return value


def statement_download_bytes(statement: pd.DataFrame) -> bytes:
    return statement.to_csv(index=True).encode("utf-8")


def render_financial_statement(
    statement_name: str,
    statement: pd.DataFrame,
    ticker: str,
    frequency: str,
) -> None:
    st.subheader(statement_name)

    if not isinstance(statement, pd.DataFrame) or statement.empty:
        st.warning(
            f"No {statement_name.lower()} data was returned for {ticker}. "
            "Try the other frequency or another ticker."
        )
        return

    display_statement = statement.copy()
    display_statement.index.name = "Line Item"

    # Convert the index into a standard visible column. This is more reliable
    # across Streamlit versions than displaying a styled DataFrame index.
    display_table = display_statement.reset_index()

    for column in display_table.columns:
        if column == "Line Item":
            display_table[column] = display_table[column].astype(str)
        else:
            display_table[column] = display_table[column].apply(
                lambda value: (
                    ""
                    if pd.isna(value)
                    else f"{float(value):,.0f}"
                    if is_number(value)
                    else str(value)
                )
            )

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
        height=650,
        column_config={
            "Line Item": st.column_config.TextColumn(
                "Line Item",
                width="large",
            )
        },
    )

    st.caption(
        f"{len(display_statement):,} line items · "
        f"{len(display_statement.columns):,} reporting periods"
    )

    filename = (
        f"{ticker}_{frequency}_"
        f"{statement_name.lower().replace(' ', '_')}.csv"
    )

    st.download_button(
        label=f"Download {statement_name} CSV",
        data=statement_download_bytes(display_statement),
        file_name=filename,
        mime="text/csv",
        key=f"download_{ticker}_{frequency}_{statement_name}",
    )


def render_financial_trends_chart(
    trends: pd.DataFrame,
    metrics: list[str],
    title: str,
    percent_metrics: Optional[set[str]] = None,
) -> None:
    if trends.empty:
        st.info("No financial trend data is available.")
        return

    available_metrics = [
        metric for metric in metrics if metric in trends.columns
    ]

    if not available_metrics:
        st.info(f"No data is available for {title.lower()}.")
        return

    chart_data = trends[available_metrics].copy()
    chart_data.index = chart_data.index.strftime("%Y")

    fig = go.Figure()

    for metric in available_metrics:
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data[metric],
                mode="lines+markers",
                name=metric,
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Fiscal Year",
        yaxis_title="Percent" if percent_metrics else "Value",
        hovermode="x unified",
        legend_title_text="Metric",
        height=420,
    )

    if percent_metrics:
        fig.update_yaxes(ticksuffix="%")

    st.plotly_chart(fig, width="stretch")


def render_growth_metrics(trends: pd.DataFrame) -> None:
    if trends.empty or len(trends.index) < 2:
        return

    latest = trends.iloc[-1]
    previous = trends.iloc[-2]

    metric_columns = st.columns(4)

    metric_map = [
        ("Revenue", "Revenue Growth"),
        ("Net Income", "Net Income Growth"),
        ("EBITDA", "EBITDA Growth"),
        ("Free Cash Flow", "FCF Growth"),
    ]

    for column, (source_metric, label) in zip(metric_columns, metric_map):
        current_value = latest.get(source_metric)
        prior_value = previous.get(source_metric)

        growth = None
        if (
            is_number(current_value)
            and is_number(prior_value)
            and float(prior_value) != 0
        ):
            growth = (
                (float(current_value) - float(prior_value))
                / abs(float(prior_value))
                * 100
            )

        with column:
            st.metric(
                label,
                "N/A" if growth is None else f"{growth:.1f}%",
            )



def format_estimate_table(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()

    display = frame.copy()
    display.index = [str(index) for index in display.index]
    display.index.name = "Period"
    display = display.reset_index()

    for column in display.columns:
        if column == "Period":
            display[column] = display[column].astype(str)
            continue

        display[column] = display[column].apply(
            lambda value: (
                ""
                if pd.isna(value)
                else f"{float(value):,.2f}"
                if is_number(value)
                else str(value)
            )
        )

    return display


def render_analyst_rating_summary(data: Mapping[str, Any]) -> None:
    recommendation_summary = data.get("recommendation_summary")

    if (
        not isinstance(recommendation_summary, pd.DataFrame)
        or recommendation_summary.empty
    ):
        recommendation_key = data.get("recommendation_key")
        if recommendation_key:
            st.info(
                f"Current consensus recommendation: "
                f"**{str(recommendation_key).replace('_', ' ').title()}**"
            )
        else:
            st.info("No analyst recommendation summary was available.")
        return

    summary = recommendation_summary.copy()

    rename_map = {
        "strongBuy": "Strong Buy",
        "buy": "Buy",
        "hold": "Hold",
        "sell": "Sell",
        "strongSell": "Strong Sell",
    }
    summary = summary.rename(columns=rename_map)

    preferred_columns = [
        column
        for column in (
            "period",
            "Strong Buy",
            "Buy",
            "Hold",
            "Sell",
            "Strong Sell",
        )
        if column in summary.columns
    ]

    if preferred_columns:
        summary = summary[preferred_columns]

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
    )

    numeric_columns = [
        column
        for column in ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell")
        if column in summary.columns
    ]

    if numeric_columns:
        latest_row = summary.iloc[0]
        labels = []
        values = []

        for column in numeric_columns:
            value = latest_row.get(column)
            if is_number(value):
                labels.append(column)
                values.append(float(value))

        if values:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=labels,
                        y=values,
                    )
                ]
            )
            fig.update_layout(
                title="Latest Analyst Recommendation Breakdown",
                xaxis_title="Recommendation",
                yaxis_title="Number of Analysts",
                height=400,
            )
            st.plotly_chart(fig, width="stretch")


def render_estimate_dataframe(
    title: str,
    frame: pd.DataFrame,
) -> None:
    st.subheader(title)

    formatted = format_estimate_table(frame)

    if formatted.empty:
        st.info(f"No {title.lower()} data was available.")
        return

    st.dataframe(
        formatted,
        use_container_width=True,
        hide_index=True,
    )



def normalize_news(news_items: Any) -> list[dict[str, Any]]:
    if news_items is None:
        return []

    if isinstance(news_items, Mapping):
        for key in ("articles", "news", "items", "results"):
            nested = news_items.get(key)
            if isinstance(nested, list):
                return [as_mapping(item) for item in nested]
        return [dict(news_items)]

    if isinstance(news_items, (list, tuple)):
        return [as_mapping(item) for item in news_items]

    return []


def render_news_cards(news_items: Any) -> None:
    articles = normalize_news(news_items)

    if not articles:
        st.info("No news articles were returned.")
        return

    for article in articles:
        title = first_present(article, "title", "headline", default="Untitled article")
        publisher = first_present(article, "publisher", "source", "provider", default="Unknown source")
        link = first_present(article, "link", "url")
        summary = first_present(article, "summary", "description", "snippet", default="")
        published = first_present(
            article,
            "published",
            "published_at",
            "providerPublishTime",
            "date",
            default="",
        )

        if is_number(published):
            try:
                published = datetime.fromtimestamp(float(published)).strftime("%b %d, %Y %I:%M %p")
            except (ValueError, OSError, OverflowError):
                pass

        if link:
            st.markdown(f"### [{title}]({link})")
        else:
            st.markdown(f"### {title}")

        metadata = f"**{publisher}**"
        if published:
            metadata += f" · {published}"
        st.caption(metadata)

        if summary:
            st.write(summary)

        st.divider()


def comparison_to_dataframe(result: Any) -> pd.DataFrame:
    def format_comparison_value(metric: str, value: Any) -> Any:
        if value is None:
            return "N/A"

        if not is_number(value):
            return value

        numeric_value = float(value)
        metric_lower = metric.lower()

        currency_metrics = (
            "price",
            "market cap",
            "enterprise value",
            "revenue",
            "net income",
            "cash",
            "debt",
            "free cash flow",
        )

        percent_metrics = (
            "margin",
            "return",
            "yield",
            "growth",
        )

        ratio_metrics = (
            "p/e",
            "peg",
            "ratio",
            "return on equity",
        )

        if any(token in metric_lower for token in currency_metrics):
            if metric_lower == "current price":
                return format_currency(numeric_value)
            return format_large_number(numeric_value)

        if any(token in metric_lower for token in percent_metrics):
            return format_percent(numeric_value)

        if any(token in metric_lower for token in ratio_metrics):
            return format_number(numeric_value)

        return format_number(numeric_value)

    if isinstance(result, pd.DataFrame):
        dataframe = result.copy()

    elif isinstance(result, Mapping):
        result_dict = dict(result)

        if result_dict and all(
            isinstance(value, Mapping)
            for value in result_dict.values()
        ):
            dataframe = pd.DataFrame(result_dict).T
        else:
            dataframe = pd.DataFrame(
                [
                    {"Metric": key, "Value": value}
                    for key, value in result_dict.items()
                ]
            )

    elif isinstance(result, (list, tuple)):
        dataframe = pd.DataFrame(result)

    else:
        dataframe = pd.DataFrame({"Result": [result]})

    if dataframe.empty:
        return dataframe

    dataframe = dataframe.reset_index()

    if "index" in dataframe.columns:
        dataframe = dataframe.rename(columns={"index": "Metric"})

    if "Metric" not in dataframe.columns:
        dataframe.insert(
            0,
            "Metric",
            [f"Metric {index + 1}" for index in range(len(dataframe))],
        )

    for column in dataframe.columns:
        if column == "Metric":
            continue

        dataframe[column] = [
            format_comparison_value(metric, value)
            for metric, value in zip(
                dataframe["Metric"],
                dataframe[column],
            )
        ]

    return dataframe


def extract_fair_value(result: Any) -> Optional[float]:
    data = as_mapping(result)
    keys = (
        "fair_value_per_share",
        "intrinsic_value_per_share",
        "estimated_share_price",
        "share_price",
        "fair_value",
        "intrinsic_value",
        "dcf_price",
    )

    for key in keys:
        value = data.get(key)
        if is_number(value):
            return float(value)

    if is_number(result):
        return float(result)

    return None


def render_dcf_result(
    result: Any,
    current_price: Number,
    title: str = "Base-Case DCF",
) -> None:
    st.subheader(title)
    result_map = as_mapping(result)
    fair_value = extract_fair_value(result)
    upside = calculate_upside(fair_value, current_price)

    metric_columns = st.columns(3)
    metric_columns[0].metric("DCF Fair Value", format_currency(fair_value))
    metric_columns[1].metric("Current Price", format_currency(current_price))
    metric_columns[2].metric(
        "Upside / Downside",
        "N/A" if upside is None else f"{upside:.2f}%",
    )

    if result_map:
        display_rows = []
        for key, value in result_map.items():
            if isinstance(value, (Mapping, list, tuple, pd.DataFrame)):
                continue
            label = key.replace("_", " ").title()
            if "rate" in key.lower() or "margin" in key.lower() or "upside" in key.lower():
                displayed = format_percent(value)
            elif any(token in key.lower() for token in ("value", "price", "cash", "debt", "equity")):
                displayed = format_large_number(value)
            else:
                displayed = format_number(value) if is_number(value) else value
            display_rows.append({"DCF Output": label, "Value": displayed})

        if display_rows:
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

        projections = first_present(
            result_map,
            "projected_cash_flows",
            "cash_flow_projections",
            "projections",
        )
        if isinstance(projections, Mapping):
            projection_df = pd.DataFrame(
                {"Year": list(projections.keys()), "Projected FCF": list(projections.values())}
            )
            st.dataframe(projection_df, use_container_width=True, hide_index=True)
        elif isinstance(projections, (list, tuple)):
            st.dataframe(pd.DataFrame(projections), use_container_width=True)

    elif result is not None:
        st.write(result)


def render_scenario_result(result: Any) -> None:
    if not isinstance(result, Mapping):
        render_text_result(result)
        return

    rows: list[dict[str, Any]] = []

    for scenario_name, scenario_data in result.items():
        if not isinstance(scenario_data, Mapping):
            continue

        fair_value = scenario_data.get("fair_value_per_share")

        growth_rate = (
            scenario_data.get("growth_rate")
            or scenario_data.get("fcf_growth_rate")
        )

        discount_rate = (
            scenario_data.get("discount_rate")
            or scenario_data.get("wacc")
        )

        terminal_growth_rate = scenario_data.get(
            "terminal_growth_rate"
        )

        projection_years = (
            scenario_data.get("projection_years")
            or scenario_data.get("forecast_years")
            or scenario_data.get("years")
        )

        rows.append(
            {
                "Scenario": str(scenario_name).title(),
                "Fair Value": fair_value,
                "FCF Growth": growth_rate,
                "WACC": discount_rate,
                "Terminal Growth": terminal_growth_rate,
                "Years": projection_years,
            }
        )

    if not rows:
        st.info("No DCF scenario results were returned.")
        return

    scenario_df = pd.DataFrame(rows)

    scenario_order = {
        "Bear": 0,
        "Base": 1,
        "Bull": 2,
    }

    scenario_df["_order"] = scenario_df["Scenario"].map(
        scenario_order
    ).fillna(99)

    scenario_df = scenario_df.sort_values("_order").drop(
        columns="_order"
    )

    scenario_df["Scenario"] = scenario_df["Scenario"].replace(
        {
            "Bear": "🔴 Bear",
            "Base": "⚪ Base",
            "Bull": "🟢 Bull",
        }
    )

    scenario_df["Fair Value"] = scenario_df["Fair Value"].apply(
        lambda value: (
            f"${float(value):,.2f}"
            if is_number(value)
            else "N/A"
        )
    )

    for column in (
        "FCF Growth",
        "WACC",
        "Terminal Growth",
    ):
        scenario_df[column] = scenario_df[column].apply(
            lambda value: (
                f"{float(value) * 100:.1f}%"
                if is_number(value)
                else "N/A"
            )
        )

    st.dataframe(
        scenario_df,
        width="stretch",
        hide_index=True,
    )


def render_sensitivity_result(result: Any) -> None:
    if isinstance(result, pd.DataFrame):
        st.dataframe(
            result.style.format(lambda value: f"${value:,.2f}" if is_number(value) else value),
            use_container_width=True,
        )
        return

    if isinstance(result, Mapping):
        data = dict(result)

        if "table" in data:
            table = data["table"]
            if isinstance(table, pd.DataFrame):
                st.dataframe(table, use_container_width=True)
                return
            if isinstance(table, (list, tuple, Mapping)):
                st.dataframe(pd.DataFrame(table), use_container_width=True)
                return

        try:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        except ValueError:
            st.json(data)
        return

    render_text_result(result)


# =============================================================================
# SESSION STATE
# =============================================================================

STATE_DEFAULTS = {
    "analysis_data": None,
    "analysis_scores": None,
    "analysis_history": None,
    "ai_report": None,
    "news_items": None,
    "ai_news_report": None,
    "investment_recommendation": None,
    "comparison_result": None,
    "ai_comparison_result": None,
    "comparison_companies": None,
    "dcf_result": None,
    "dcf_scenarios_result": None,
    "dcf_sensitivity_result": None,
    "dcf_company_data": None,
    "financial_statements": None,
    "financial_statements_ticker": None,
    "financial_statements_frequency": None,
}

for state_key, default_value in STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.title("📈 Finance AI Research Terminal")
    st.caption("AI-powered public-equity research, analytics, and valuation.")

    main_ticker = clean_ticker(
        st.text_input(
            "Primary ticker",
            value=st.session_state.get("primary_ticker", "NVDA"),
            key="primary_ticker_input",
        )
    )
    st.session_state["primary_ticker"] = main_ticker

    history_period = st.selectbox(
        "Price-history period",
        options=("1mo", "3mo", "6mo", "1y", "2y", "5y", "max"),
        index=3,
    )

# =============================================================================
# HEADER
# =============================================================================

st.title("Finance AI Research Terminal")
st.caption(
    "End-to-end public-company research platform combining market data, "
    "financial statements, scoring, AI research, news intelligence, "
    "peer comparison, investment recommendations, and DCF valuation."
)

if not main_ticker:
    st.warning("Enter a ticker in the sidebar to begin.")
    st.stop()


# =============================================================================
# MAIN NAVIGATION
# =============================================================================

(
    overview_tab,
    statements_tab,
    trends_tab,
    analyst_tab,
    research_tab,
    news_tab,
    recommendation_tab,
    comparison_tab,
    dcf_tab,
    about_tab,
) = st.tabs(
    (
        "Company Overview",
        "Financial Statements",
        "Financial Trends",
        "Analyst Estimates",
        "AI Research",
        "News Intelligence",
        "Investment Recommendation",
        "Company Comparison",
        "DCF Valuation",
        "About Project",
    )
)


# =============================================================================
# COMPANY OVERVIEW TAB
# =============================================================================

with overview_tab:
    st.header("Company Overview")

    if st.button("Analyze Company", type="primary", key="overview_analyze_button"):
        try:
            with st.spinner(f"Loading market and financial data for {main_ticker}..."):
                company_data = get_company_data(main_ticker)
                scores = calculate_scores(company_data)
                history = get_price_history(main_ticker, history_period)

            st.session_state.analysis_data = company_data
            st.session_state.analysis_scores = scores
            st.session_state.analysis_history = history

            # Clear ticker-dependent generated outputs when a new company is analyzed.
            st.session_state.ai_report = None
            st.session_state.news_items = None
            st.session_state.ai_news_report = None
            st.session_state.investment_recommendation = None

        except Exception as exc:
            st.error(f"Could not analyze {main_ticker}: {exc}")

    company_data = st.session_state.analysis_data
    scores = st.session_state.analysis_scores
    history = st.session_state.analysis_history

    if company_data and clean_ticker(str(first_present(company_data, "ticker", default=""))) == main_ticker:
        company_name = first_present(company_data, "company_name", "name", default=main_ticker)
        sector = first_present(company_data, "sector", default="N/A")
        industry = first_present(company_data, "industry", default="N/A")

        st.subheader(company_name)
        st.write(f"**Ticker:** {main_ticker} · **Sector:** {sector} · **Industry:** {industry}")

        current_price = first_present(company_data, "current_price", "regular_market_price")
        market_cap = first_present(company_data, "market_cap")
        one_year_return = first_present(company_data, "one_year_return", "one_year_change")
        trailing_pe = first_present(company_data, "trailing_pe")

        headline_metrics = st.columns(4)
        headline_metrics[0].metric("Current Price", format_currency(current_price))
        headline_metrics[1].metric("Market Cap", format_large_number(market_cap))
        headline_metrics[2].metric("1-Year Return", format_percent(one_year_return))
        headline_metrics[3].metric("Trailing P/E", format_number(trailing_pe))

        st.subheader("Financial Scorecard")
        render_scorecard(scores or {})

        st.subheader(f"{history_period.upper()} Price History")
        render_price_chart(history if isinstance(history, pd.DataFrame) else pd.DataFrame(), main_ticker)

        st.subheader("Financial Overview")
        render_financial_overview(company_data)

    else:
        st.info("Click **Analyze Company** to load the full overview.")


# =============================================================================
# FINANCIAL STATEMENTS TAB
# =============================================================================

with statements_tab:
    st.header("Financial Statements")
    st.caption(
        "Review annual or quarterly income statements, balance sheets, "
        "and cash flow statements. Download any statement as a CSV file."
    )

    statement_frequency = st.radio(
        "Statement frequency",
        options=("Annual", "Quarterly"),
        horizontal=True,
        key="statement_frequency",
    )

    if st.button(
        f"Load {statement_frequency} Financial Statements",
        type="primary",
        key="load_financial_statements",
    ):
        try:
            with st.spinner(
                f"Loading {statement_frequency.lower()} financial statements "
                f"for {main_ticker}..."
            ):
                st.session_state["financial_statements"] = get_financial_statements(
                    main_ticker,
                    statement_frequency.lower(),
                )
                st.session_state["financial_statements_ticker"] = main_ticker
                st.session_state["financial_statements_frequency"] = (
                    statement_frequency.lower()
                )
        except Exception as exc:
            st.error(f"Could not load financial statements: {exc}")

    statements = st.session_state.get("financial_statements")
    statements_ticker = st.session_state.get("financial_statements_ticker")
    statements_frequency = st.session_state.get(
        "financial_statements_frequency"
    )

    if statements and statements_ticker == main_ticker:
        income_tab, balance_tab, cash_flow_tab = st.tabs(
            ("Income Statement", "Balance Sheet", "Cash Flow Statement")
        )

        with income_tab:
            render_financial_statement(
                "Income Statement",
                statements.get("Income Statement", pd.DataFrame()),
                main_ticker,
                statements_frequency or "annual",
            )

        with balance_tab:
            render_financial_statement(
                "Balance Sheet",
                statements.get("Balance Sheet", pd.DataFrame()),
                main_ticker,
                statements_frequency or "annual",
            )

        with cash_flow_tab:
            render_financial_statement(
                "Cash Flow Statement",
                statements.get("Cash Flow Statement", pd.DataFrame()),
                main_ticker,
                statements_frequency or "annual",
            )
    else:
        st.info(
            "Select annual or quarterly data and click "
            "**Load Financial Statements**."
        )


# =============================================================================
# FINANCIAL TRENDS TAB
# =============================================================================

with trends_tab:
    st.header("Financial Trends")
    st.caption(
        "Visualize multi-year revenue, profitability, cash flow, EPS, "
        "and margin trends."
    )

    try:
        with st.spinner(f"Loading financial trends for {main_ticker}..."):
            financial_trends = get_financial_trends(main_ticker)
    except Exception as exc:
        financial_trends = pd.DataFrame()
        st.error(f"Could not load financial trends: {exc}")

    if financial_trends.empty:
        st.info("No financial trend data was returned for this ticker.")
    else:
        render_growth_metrics(financial_trends)

        st.markdown("### Revenue and Profitability")
        render_financial_trends_chart(
            financial_trends,
            ["Revenue", "Net Income", "EBITDA"],
            "Revenue, Net Income, and EBITDA",
        )

        st.markdown("### Cash Flow")
        render_financial_trends_chart(
            financial_trends,
            ["Free Cash Flow"],
            "Free Cash Flow Trend",
        )

        st.markdown("### Earnings per Share")
        render_financial_trends_chart(
            financial_trends,
            ["Diluted EPS"],
            "Diluted EPS Trend",
        )

        st.markdown("### Margin Analysis")
        render_financial_trends_chart(
            financial_trends,
            ["Gross Margin", "Operating Margin"],
            "Gross and Operating Margins",
            percent_metrics={"Gross Margin", "Operating Margin"},
        )

        st.download_button(
            label="Download Financial Trends CSV",
            data=financial_trends.to_csv(index=True).encode("utf-8"),
            file_name=f"{main_ticker}_financial_trends.csv",
            mime="text/csv",
            key="download_financial_trends",
        )


# =============================================================================
# ANALYST ESTIMATES TAB
# =============================================================================

with analyst_tab:
    st.header("Analyst Estimates and Price Targets")
    st.caption(
        "Review Wall Street consensus ratings, target prices, "
        "and forward revenue and earnings expectations."
    )

    try:
        with st.spinner(f"Loading analyst estimates for {main_ticker}..."):
            analyst_data = get_analyst_estimates(main_ticker)
    except Exception as exc:
        analyst_data = {}
        st.error(f"Could not load analyst estimates: {exc}")

    current_price = analyst_data.get("current_price")
    target_mean = analyst_data.get("target_mean")
    target_high = analyst_data.get("target_high")
    target_low = analyst_data.get("target_low")
    analyst_count = analyst_data.get("analyst_count")

    implied_upside = None
    if (
        is_number(current_price)
        and is_number(target_mean)
        and float(current_price) != 0
    ):
        implied_upside = (
            (float(target_mean) - float(current_price))
            / float(current_price)
            * 100
        )

    metric_columns = st.columns(5)

    with metric_columns[0]:
        st.metric(
            "Current Price",
            format_currency(current_price),
        )

    with metric_columns[1]:
        st.metric(
            "Average Target",
            format_currency(target_mean),
            None if implied_upside is None else f"{implied_upside:.1f}%",
        )

    with metric_columns[2]:
        st.metric(
            "High Target",
            format_currency(target_high),
        )

    with metric_columns[3]:
        st.metric(
            "Low Target",
            format_currency(target_low),
        )

    with metric_columns[4]:
        st.metric(
            "Analyst Count",
            "N/A"
            if not is_number(analyst_count)
            else f"{int(float(analyst_count))}",
        )

    if (
        is_number(current_price)
        and is_number(target_low)
        and is_number(target_mean)
        and is_number(target_high)
    ):
        target_chart = go.Figure()

        target_chart.add_trace(
            go.Bar(
                x=["Low Target", "Current Price", "Average Target", "High Target"],
                y=[
                    float(target_low),
                    float(current_price),
                    float(target_mean),
                    float(target_high),
                ],
                text=[
                    format_currency(target_low),
                    format_currency(current_price),
                    format_currency(target_mean),
                    format_currency(target_high),
                ],
                textposition="auto",
            )
        )

        target_chart.update_layout(
            title="Price Target Range",
            xaxis_title="Measure",
            yaxis_title="Price",
            height=420,
        )

        st.plotly_chart(target_chart, use_container_width=True)

    st.markdown("### Recommendation Consensus")
    render_analyst_rating_summary(analyst_data)

    estimate_tab_1, estimate_tab_2, estimate_tab_3 = st.tabs(
        (
            "Revenue Estimates",
            "Earnings Estimates",
            "Recommendation History",
        )
    )

    with estimate_tab_1:
        render_estimate_dataframe(
            "Revenue Estimates",
            analyst_data.get("revenue_estimates", pd.DataFrame()),
        )

    with estimate_tab_2:
        render_estimate_dataframe(
            "Earnings Estimates",
            analyst_data.get("earnings_estimates", pd.DataFrame()),
        )

    with estimate_tab_3:
        recommendation_history = analyst_data.get(
            "recommendations",
            pd.DataFrame(),
        )

        if (
            not isinstance(recommendation_history, pd.DataFrame)
            or recommendation_history.empty
        ):
            st.info("No recommendation history was available.")
        else:
            history = recommendation_history.copy()

            if len(history) > 100:
                history = history.tail(100)

            history = history.reset_index()

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )


# =============================================================================
# AI RESEARCH TAB
# =============================================================================

with research_tab:
    st.header("AI Equity Research")

    if st.session_state.analysis_data is None or clean_ticker(
        str(first_present(st.session_state.analysis_data or {}, "ticker", default=""))
    ) != main_ticker:
        st.info("Analyze the company in the Company Overview tab first.")
    else:
        if st.button("Generate AI Research Report", type="primary", key="generate_ai_report"):
            try:
                with st.spinner("Generating the AI equity-research report..."):
                    st.session_state.ai_report = generate_analysis(
                        st.session_state.analysis_data,
                        st.session_state.analysis_scores or {},
                    )
            except Exception as exc:
                st.error(f"Could not generate the AI research report: {exc}")

        if st.session_state.ai_report is not None:
            render_text_result(st.session_state.ai_report)
        else:
            st.info("Generate a report to view the AI investment thesis, risks, and catalysts.")


# =============================================================================
# NEWS TAB
# =============================================================================

with news_tab:
    st.header("Company News Intelligence")

    if st.session_state.analysis_data is None or clean_ticker(
        str(first_present(st.session_state.analysis_data or {}, "ticker", default=""))
    ) != main_ticker:
        st.info("Analyze the company in the Company Overview tab first.")
    else:
        news_button, ai_news_button = st.columns(2)

        with news_button:
            fetch_news = st.button(
                "Fetch Company News",
                type="primary",
                key="fetch_company_news",
                use_container_width=True,
            )

        with ai_news_button:
            analyze_news_button = st.button(
                "Run AI News Analysis",
                key="run_ai_news_analysis",
                use_container_width=True,
            )

        if fetch_news:
            try:
                with st.spinner(f"Fetching company news for {main_ticker}..."):
                    st.session_state.news_items = get_news_items(
                        main_ticker,
                        st.session_state.analysis_data,
                    )
                    st.session_state.ai_news_report = None
            except Exception as exc:
                st.error(f"Could not fetch company news: {exc}")

        if analyze_news_button:
            try:
                if st.session_state.news_items is None:
                    with st.spinner(f"Fetching company news for {main_ticker}..."):
                        st.session_state.news_items = get_news_items(
                            main_ticker,
                            st.session_state.analysis_data,
                        )

                with st.spinner("Analyzing news sentiment, catalysts, and risks..."):
                    st.session_state.ai_news_report = generate_news_analysis(
                        st.session_state.analysis_data,
                        st.session_state.news_items,
                    )
            except Exception as exc:
                st.error(f"Could not run the AI news analysis: {exc}")

        news_list_tab, news_analysis_tab = st.tabs(("Latest Articles", "AI News Analysis"))

        with news_list_tab:
            if st.session_state.news_items is not None:
                render_news_cards(st.session_state.news_items)
            else:
                st.info("Fetch company news to display the latest articles.")

        with news_analysis_tab:
            if st.session_state.ai_news_report is not None:
                render_text_result(st.session_state.ai_news_report)
            else:
                st.info("Run AI News Analysis to summarize sentiment, catalysts, and risks.")


# =============================================================================
# INVESTMENT RECOMMENDATION TAB
# =============================================================================

with recommendation_tab:
    st.header("Investment Recommendation")

    if st.session_state.analysis_data is None or clean_ticker(
        str(first_present(st.session_state.analysis_data or {}, "ticker", default=""))
    ) != main_ticker:
        st.info("Analyze the company in the Company Overview tab first.")
    else:
        st.warning(
            "This output is a research aid, not personalized financial advice. "
            "Verify all market data and assumptions before making an investment decision."
        )

        if st.button(
            "Generate Investment Recommendation",
            type="primary",
            key="generate_investment_recommendation",
        ):
            try:
                with st.spinner("Building the investment recommendation..."):
                    if st.session_state.ai_report is None:
                        st.session_state.ai_report = generate_analysis(
                            st.session_state.analysis_data,
                            st.session_state.analysis_scores or {},
                        )

                    if st.session_state.news_items is None:
                        try:
                            st.session_state.news_items = get_news_items(
                                main_ticker,
                                st.session_state.analysis_data,
                            )
                        except Exception:
                            st.session_state.news_items = []

                    if st.session_state.ai_news_report is None and st.session_state.news_items:
                        try:
                            st.session_state.ai_news_report = generate_news_analysis(
                                st.session_state.analysis_data,
                                st.session_state.news_items,
                            )
                        except Exception:
                            st.session_state.ai_news_report = None

                    st.session_state.investment_recommendation = generate_recommendation(
                        st.session_state.analysis_data,
                        st.session_state.analysis_scores or {},
                        st.session_state.ai_report,
                        st.session_state.ai_news_report,
                    )
            except Exception as exc:
                st.error(f"Could not generate the investment recommendation: {exc}")

        if st.session_state.investment_recommendation is not None:
            render_text_result(st.session_state.investment_recommendation)
        else:
            st.info(
                "Generate the recommendation to combine market data, financial scoring, "
                "AI equity research, and available news intelligence."
            )


# =============================================================================
# COMPANY COMPARISON TAB
# =============================================================================

with comparison_tab:
    st.header("Company Comparison")

    comparison_input_1, comparison_input_2 = st.columns(2)

    with comparison_input_1:
        first_ticker = clean_ticker(
            st.text_input(
                "First ticker",
                value=main_ticker,
                key="comparison_first_ticker",
            )
        )

    with comparison_input_2:
        second_ticker = clean_ticker(
            st.text_input(
                "Second ticker",
                value="AMD" if main_ticker != "AMD" else "NVDA",
                key="comparison_second_ticker",
            )
        )

    if st.button("Compare Companies", type="primary", key="compare_companies_button"):
        if not first_ticker or not second_ticker:
            st.error("Enter both ticker symbols.")
        elif first_ticker == second_ticker:
            st.error("Enter two different ticker symbols.")
        else:
            try:
                with st.spinner(
                    f"Loading financial data for {first_ticker} and {second_ticker}..."
                ):
                    first_company = get_company_data(first_ticker)
                    second_company = get_company_data(second_ticker)

                    first_scores = calculate_scores(first_company)
                    second_scores = calculate_scores(second_company)

                    comparison_result = run_comparison(
                        first_company,
                        second_company,
                    )

                st.session_state.comparison_result = comparison_result
                st.session_state.comparison_companies = {
                    "first": first_company,
                    "second": second_company,
                    "first_scores": first_scores,
                    "second_scores": second_scores,
                }

                # Clear the previous AI result when a new pair is compared.
                st.session_state.ai_comparison_result = None

            except Exception as exc:
                st.error(f"Could not load the financial comparison: {exc}")

    comparison_companies = st.session_state.comparison_companies

    if comparison_companies:
        first_company = comparison_companies["first"]
        second_company = comparison_companies["second"]
        first_scores = comparison_companies["first_scores"]
        second_scores = comparison_companies["second_scores"]

        first_name = first_present(first_company, "company_name", "name", default=first_ticker)
        second_name = first_present(second_company, "company_name", "name", default=second_ticker)

        st.subheader(f"{first_name} vs. {second_name}")

        company_columns = st.columns(2)
        with company_columns[0]:
            st.markdown(f"### {first_present(first_company, 'ticker', default=first_ticker)}")
            st.metric(
                "Overall Score",
                f"{first_present(first_scores, 'overall', default='N/A')} / 100"
                if is_number(first_present(first_scores, "overall"))
                else "N/A",
            )
            st.metric("Current Price", format_currency(first_present(first_company, "current_price")))
            st.metric("Market Cap", format_large_number(first_present(first_company, "market_cap")))

        with company_columns[1]:
            st.markdown(f"### {first_present(second_company, 'ticker', default=second_ticker)}")
            st.metric(
                "Overall Score",
                f"{first_present(second_scores, 'overall', default='N/A')} / 100"
                if is_number(first_present(second_scores, "overall"))
                else "N/A",
            )
            st.metric("Current Price", format_currency(first_present(second_company, "current_price")))
            st.metric("Market Cap", format_large_number(first_present(second_company, "market_cap")))

        raw_comparison_tab, ai_comparison_tab = st.tabs(
            ("Financial Comparison", "AI Comparison")
        )

        with raw_comparison_tab:
            if st.session_state.comparison_result is not None:
                st.dataframe(
                    comparison_to_dataframe(st.session_state.comparison_result),
                    use_container_width=True,
                )

        with ai_comparison_tab:
            if st.button(
                "Generate AI Comparison",
                type="primary",
                key="generate_ai_comparison_button",
            ):
                try:
                    with st.spinner("Generating AI investment analysis..."):
                        ai_result = run_ai_comparison(
                            first_company,
                            second_company,
                            first_scores,
                            second_scores,
                        )

                    if isinstance(ai_result, str):
                        ai_result = ai_result.strip()

                    if ai_result:
                        st.session_state.ai_comparison_result = ai_result
                    else:
                        st.session_state.ai_comparison_result = (
                            "The AI comparison completed but returned no written analysis."
                        )

                except Exception as exc:
                    st.error(f"Could not generate AI comparison: {exc}")

            if st.session_state.ai_comparison_result:
                render_text_result(
                    st.session_state.ai_comparison_result
                )
            else:
                st.info(
                    "Click **Generate AI Comparison** to create an AI investment analysis."
                )
    else:
        st.info("Enter two tickers and click **Compare Companies**.")


# =============================================================================
# DCF TAB
# =============================================================================

with dcf_tab:
    st.header("Discounted Cash Flow Valuation")

    dcf_ticker = clean_ticker(
        st.text_input(
            "DCF ticker",
            value=main_ticker,
            key="dcf_ticker",
        )
    )

    assumption_columns = st.columns(4)

    with assumption_columns[0]:
        growth_rate_percent = st.number_input(
            "Annual FCF Growth (%)",
            min_value=-50.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
            key="dcf_growth_rate",
        )

    with assumption_columns[1]:
        discount_rate_percent = st.number_input(
            "Discount Rate / WACC (%)",
            min_value=1.0,
            max_value=50.0,
            value=10.0,
            step=0.25,
            key="dcf_discount_rate",
        )

    with assumption_columns[2]:
        terminal_growth_percent = st.number_input(
            "Terminal Growth (%)",
            min_value=-5.0,
            max_value=10.0,
            value=3.0,
            step=0.25,
            key="dcf_terminal_growth_rate",
        )

    with assumption_columns[3]:
        projection_years = st.number_input(
            "Projection Years",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            key="dcf_projection_years",
        )

    growth_rate = growth_rate_percent / 100
    discount_rate = discount_rate_percent / 100
    terminal_growth_rate = terminal_growth_percent / 100

    if terminal_growth_rate >= discount_rate:
        st.error("Terminal growth must be lower than the discount rate.")

    run_dcf_button = st.button(
        "Run Complete DCF Analysis",
        type="primary",
        key="run_complete_dcf",
        disabled=terminal_growth_rate >= discount_rate or not dcf_ticker,
    )

    if run_dcf_button:
        try:
            with st.spinner(f"Running DCF valuation for {dcf_ticker}..."):
                dcf_company_data = get_company_data(dcf_ticker)

                base_result = run_dcf(
                    dcf_company_data,
                    growth_rate,
                    discount_rate,
                    terminal_growth_rate,
                    int(projection_years),
                )

                scenarios_result = run_dcf_scenarios(
                    dcf_company_data,
                    growth_rate,
                    discount_rate,
                    terminal_growth_rate,
                    int(projection_years),
                )

                sensitivity_result = run_dcf_sensitivity(
                    dcf_company_data,
                    growth_rate,
                    discount_rate,
                    terminal_growth_rate,
                    int(projection_years),
                )

                st.session_state.dcf_company_data = dcf_company_data
                st.session_state.dcf_result = base_result
                st.session_state.dcf_scenarios_result = scenarios_result
                st.session_state.dcf_sensitivity_result = sensitivity_result

        except Exception as exc:
            st.error(f"Could not complete the DCF analysis: {exc}")

    if st.session_state.dcf_result is not None and st.session_state.dcf_company_data:
        dcf_company_data = st.session_state.dcf_company_data
        current_price = first_present(
            dcf_company_data,
            "current_price",
            "regular_market_price",
        )

        base_tab, scenarios_tab, sensitivity_tab = st.tabs(
            ("Base Case", "Scenarios", "Sensitivity")
        )

        with base_tab:
            render_dcf_result(
                st.session_state.dcf_result,
                current_price,
                title=f"{first_present(dcf_company_data, 'company_name', default=dcf_ticker)} DCF",
            )

        with scenarios_tab:
            st.subheader("Bull, Base, and Bear Scenarios")
            render_scenario_result(st.session_state.dcf_scenarios_result)

        with sensitivity_tab:
            st.subheader("DCF Sensitivity Table")
            render_sensitivity_result(st.session_state.dcf_sensitivity_result)
    else:
        st.info(
            "Set the assumptions and click **Run Complete DCF Analysis** to calculate "
            "the base valuation, scenarios, and sensitivity table."
        )


# =============================================================================
# ABOUT PROJECT TAB
# =============================================================================

with about_tab:
    st.header("About This Project")
    st.caption(
        "A portfolio-ready equity research platform combining financial "
        "analysis, valuation, market intelligence, and AI-assisted research."
    )

    overview_column, stack_column = st.columns(2)

    with overview_column:
        st.subheader("Project Overview")
        st.write(
            "The Finance AI Research Terminal is an end-to-end public-equity "
            "analysis application. Users can enter a ticker and review company "
            "fundamentals, price performance, financial statements, analyst "
            "expectations, AI research, news, peer comparisons, investment "
            "recommendations, and DCF valuation outputs."
        )

        st.subheader("Core Capabilities")
        st.markdown(
            """
- Public-company market and fundamental data
- Financial scoring across profitability, valuation, balance sheet, and performance
- Annual and quarterly financial statements
- Multi-year revenue, earnings, margin, EPS, and cash-flow trends
- Analyst ratings, price targets, and forward estimates
- AI-generated company research and investment recommendations
- News intelligence and sentiment analysis
- Peer-company comparison
- DCF valuation, scenarios, and sensitivity analysis
- CSV exports for financial statements and trend data
"""
        )

    with stack_column:
        st.subheader("Technology Stack")
        technology_stack = pd.DataFrame(
            {
                "Technology": [
                    "Python",
                    "Streamlit",
                    "yfinance",
                    "Pandas",
                    "Plotly",
                    "OpenAI API",
                ],
                "Purpose": [
                    "Application logic and financial calculations",
                    "Interactive web interface",
                    "Market and company data",
                    "Data transformation and analysis",
                    "Interactive financial visualizations",
                    "AI research and recommendation generation",
                ],
            }
        )
        st.dataframe(
            technology_stack,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Analytical Methods")
        st.markdown(
            """
- Fundamental ratio analysis
- Profitability and balance-sheet scoring
- Relative valuation
- Historical trend analysis
- Analyst-consensus analysis
- Discounted cash flow valuation
- Scenario and sensitivity analysis
- AI-assisted qualitative research
"""
        )

    st.divider()
    st.subheader("Methodology")

    methodology_one, methodology_two, methodology_three = st.columns(3)

    with methodology_one:
        st.markdown("#### 1. Data Collection")
        st.write(
            "Collects market prices, company fundamentals, financial "
            "statements, analyst estimates, and news from external providers."
        )

    with methodology_two:
        st.markdown("#### 2. Financial Analysis")
        st.write(
            "Transforms raw data into standardized metrics, growth rates, "
            "financial scores, trend charts, comparisons, and valuations."
        )

    with methodology_three:
        st.markdown("#### 3. AI Interpretation")
        st.write(
            "Summarizes performance, identifies risks and catalysts, evaluates "
            "news, and produces structured investment commentary."
        )

    st.divider()
    st.subheader("Project Metrics")

    project_metric_one, project_metric_two, project_metric_three, project_metric_four = st.columns(4)

    with project_metric_one:
        integrated_module_count = sum(
            MODULES.get(name) is not None
            for name in MODULE_NAMES
        )
        st.metric(
            "Integrated Modules",
            f"{integrated_module_count}/{len(MODULE_NAMES)}",
        )

    with project_metric_two:
        st.metric("Research Sections", "10")

    with project_metric_three:
        st.metric("Valuation Tools", "3")

    with project_metric_four:
        st.metric("Export Format", "CSV")

    st.divider()
    st.subheader("Data and Model Disclosures")
    st.info(
        "Market and company data may be delayed, incomplete, or differently "
        "defined across providers. Analyst estimates change frequently. "
        "AI-generated research may contain errors and is not personalized "
        "investment advice."
    )



# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption(
    "Finance AI Research Terminal · Data may be delayed or incomplete. "
    "AI-generated analysis can be wrong and should be independently verified."
)