from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Mapping, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = letter


def _is_number(value: Any) -> bool:
    try:
        return value is not None and not pd.isna(value) and float(value) == float(value)
    except (TypeError, ValueError):
        return False


def _money(value: Any) -> str:
    """Format monetary values using finance-friendly abbreviations."""
    if not _is_number(value):
        return "N/A"

    numeric = float(value)
    absolute = abs(numeric)

    if absolute >= 1_000_000_000_000:
        return f"${numeric / 1_000_000_000_000:.2f}T"

    if absolute >= 1_000_000_000:
        return f"${numeric / 1_000_000_000:.2f}B"

    if absolute >= 1_000_000:
        return f"${numeric / 1_000_000:.2f}M"

    if absolute >= 1_000:
        return f"${numeric / 1_000:.2f}K"

    return f"${numeric:,.2f}"


def _number(value: Any, decimals: int = 1) -> str:
    if not _is_number(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def _percent(value: Any) -> str:
    if not _is_number(value):
        return "N/A"

    numeric = float(value)

    if abs(numeric) <= 1:
        numeric *= 100

    return f"{numeric:,.1f}%"


def _ratio_percent(value: Any) -> str:
    """Format ratios supplied as decimals, including values above 1.0."""
    if not _is_number(value):
        return "N/A"

    return f"{float(value) * 100:,.1f}%"


def _compact_number(value: Any) -> str:
    """Format large non-currency values for financial tables."""
    if not _is_number(value):
        return _clean_text(value, "-")

    numeric = float(value)
    absolute = abs(numeric)

    if absolute >= 1_000_000_000_000:
        return f"{numeric / 1_000_000_000_000:.2f}T"

    if absolute >= 1_000_000_000:
        return f"{numeric / 1_000_000_000:.2f}B"

    if absolute >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"

    if absolute >= 1_000:
        return f"{numeric / 1_000:.2f}K"

    if numeric.is_integer():
        return f"{numeric:,.0f}"

    return f"{numeric:,.2f}"


def _format_table_value(column: str, value: Any) -> str:
    """Apply context-aware formatting to PDF table cells."""
    if value is None or (
        not isinstance(value, str)
        and pd.isna(value)
    ):
        return "-"

    column_name = str(column).lower()

    if isinstance(value, (pd.Timestamp, datetime)):
        return f"FY{value.year}"

    if column_name in {"date", "index"}:
        try:
            parsed = pd.to_datetime(value)
            return f"FY{parsed.year}"
        except Exception:
            pass

    if not _is_number(value):
        return _clean_text(value, "-")

    numeric = float(value)

    if "eps" in column_name:
        return f"{numeric:.2f}"

    if "margin" in column_name or "growth" in column_name:
        return _percent(numeric)

    if any(
        label in column_name
        for label in (
            "revenue",
            "income",
            "ebitda",
            "cash flow",
            "cashflow",
            "market cap",
            "enterprise value",
        )
    ):
        return _money(numeric)

    return _compact_number(numeric)


def _clean_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def _first_present(
    data: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return default


def _section_title(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles["SectionTitle"])


def _metric_table(
    metrics: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    cells = []

    for label, value in metrics:
        cells.append(
            [
                Paragraph(label, styles["MetricLabel"]),
                Paragraph(value, styles["MetricValue"]),
            ]
        )

    table = Table(
        cells,
        colWidths=[2.45 * inch, 3.85 * inch],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F3F6")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#272936")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DCE5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return table


def _dataframe_table(
    frame: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    max_rows: int = 8,
    max_columns: int = 5,
) -> Optional[Table]:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None

    prepared = frame.copy().head(max_rows)
    prepared = prepared.iloc[:, :max_columns]
    prepared = prepared.reset_index()

    column_labels = {
        "period": "Period",
        "avg": "Average",
        "low": "Low",
        "high": "High",
        "numberOfAnalysts": "Analysts",
        "yearAgoRevenue": "Prior Revenue",
        "yearAgoEps": "Prior EPS",
        "growth": "Growth",
        "Date": "Fiscal Year",
        "index": "Fiscal Year",
    }

    header = [
        Paragraph(
            column_labels.get(str(column), str(column)),
            styles["TableHeader"],
        )
        for column in prepared.columns
    ]

    rows = [header]

    for _, row in prepared.iterrows():
        rows.append(
            [
                Paragraph(
                    _format_table_value(column, value),
                    styles["TableCell"],
                )
                for column, value in zip(
                    prepared.columns,
                    row.tolist(),
                )
            ]
        )

    available_width = 6.3 * inch
    column_width = available_width / max(len(prepared.columns), 1)

    table = Table(
        rows,
        colWidths=[column_width] * len(prepared.columns),
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#272936")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DCE5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


def _revenue_trend_chart(
    financial_trends: pd.DataFrame,
) -> Optional[Drawing]:
    """Create a compact revenue trend chart for the PDF report."""
    if (
        not isinstance(financial_trends, pd.DataFrame)
        or financial_trends.empty
        or "Revenue" not in financial_trends.columns
    ):
        return None

    revenue = pd.to_numeric(
        financial_trends["Revenue"],
        errors="coerce",
    ).dropna()

    if revenue.empty:
        return None

    revenue = revenue.sort_index()

    years = []

    for index_value in revenue.index:
        try:
            years.append(
                f"FY{pd.to_datetime(index_value).year}"
            )
        except Exception:
            years.append(str(index_value))

    values_billions = [
        float(value) / 1_000_000_000
        for value in revenue.tolist()
    ]

    drawing = Drawing(
        460,
        225,
    )

    drawing.add(
        String(
            10,
            205,
            "Annual Revenue Trend",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=colors.HexColor("#272936"),
        )
    )

    chart = HorizontalLineChart()

    chart.x = 50
    chart.y = 42
    chart.height = 135
    chart.width = 380

    chart.data = [values_billions]

    chart.categoryAxis.categoryNames = years
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.dy = -8
    chart.categoryAxis.strokeColor = colors.HexColor("#AEB3BE")

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values_billions) * 1.15
    chart.valueAxis.valueStep = max(
        round(max(values_billions) / 4, 0),
        1,
    )
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labelTextFormat = lambda value: (
        f"${value:,.0f}B"
    )
    chart.valueAxis.strokeColor = colors.HexColor("#AEB3BE")
    chart.valueAxis.gridStrokeColor = colors.HexColor("#E1E4EA")
    chart.valueAxis.visibleGrid = True

    chart.lines[0].strokeColor = colors.HexColor("#E84B4B")
    chart.lines[0].strokeWidth = 2.5
    chart.lines[0].symbol = None

    drawing.add(chart)

    latest_revenue = values_billions[-1]

    drawing.add(
        String(
            430,
            185,
            f"${latest_revenue:,.1f}B",
            textAnchor="end",
            fontName="Helvetica-Bold",
            fontSize=9,
            fillColor=colors.HexColor("#E84B4B"),
        )
    )

    return drawing


def _add_page_number(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#707482"))

    page_number = canvas.getPageNumber()

    canvas.drawString(
        0.65 * inch,
        0.38 * inch,
        "Finance AI Research Terminal",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 0.65 * inch,
        0.38 * inch,
        f"Page {page_number}",
    )

    canvas.restoreState()


def generate_research_report_pdf(
    ticker: str,
    company_data: Mapping[str, Any],
    scores: Optional[Mapping[str, Any]] = None,
    analyst_data: Optional[Mapping[str, Any]] = None,
    recommendation: Optional[Mapping[str, Any]] = None,
    dcf_data: Optional[Mapping[str, Any]] = None,
    financial_trends: Optional[pd.DataFrame] = None,
    ai_research: Optional[str] = None,
    news_summary: Optional[str] = None,
) -> bytes:
    """
    Build a professional public-company research report and return PDF bytes.
    """
    scores = scores or {}
    analyst_data = analyst_data or {}
    recommendation = recommendation or {}
    dcf_data = dcf_data or {}

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{ticker.upper()} Research Report",
        author="Finance AI Research Terminal",
    )

    base_styles = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#272936"),
            spaceAfter=12,
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#707482"),
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#272936"),
            spaceBefore=10,
            spaceAfter=10,
        ),
        "Body": ParagraphStyle(
            "ReportBody",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#343642"),
            spaceAfter=8,
        ),
        "MetricLabel": ParagraphStyle(
            "MetricLabel",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4A4D59"),
        ),
        "MetricValue": ParagraphStyle(
            "MetricValue",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#272936"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#343642"),
        ),
        "Disclaimer": ParagraphStyle(
            "Disclaimer",
            parent=base_styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#707482"),
        ),
    }

    company_name = _first_present(
        company_data,
        "company_name",
        "longName",
        "shortName",
        "name",
        default=ticker.upper(),
    )

    current_price = _first_present(
        company_data,
        "current_price",
        "currentPrice",
        "regularMarketPrice",
    )

    market_cap = _first_present(
        company_data,
        "market_cap",
        "marketCap",
    )

    story = [
        Spacer(1, 0.35 * inch),
        Paragraph(
            "Finance AI Research Terminal",
            styles["Subtitle"],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph(
            f"{_clean_text(company_name)} ({ticker.upper()})",
            styles["Title"],
        ),
        Paragraph(
            "Public Company Research Report",
            styles["Subtitle"],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph(
            datetime.now().strftime("%B %d, %Y"),
            styles["Subtitle"],
        ),
        Spacer(1, 0.55 * inch),
    ]

    cover_metrics = [
        ("Current Price", _money(current_price)),
        ("Market Capitalization", _money(market_cap)),
        (
            "Overall Score",
            (
                f"{_number(scores.get('overall'), 0)} / 100"
                if _is_number(scores.get("overall"))
                else "N/A"
            ),
        ),
        (
            "Analyst Consensus",
            _clean_text(
                analyst_data.get("recommendation_key")
                or recommendation.get("recommendation")
            )
            .replace("_", " ")
            .title(),
        ),
        (
            "DCF Intrinsic Value",
            _money(
                _first_present(
                    dcf_data,
                    "intrinsic_value",
                    "intrinsic_value_per_share",
                    "fair_value",
                )
            ),
        ),
    ]

    story.append(_metric_table(cover_metrics, styles))
    story.append(PageBreak())

    story.append(_section_title("Executive Summary", styles))

    supplied_summary = (
        recommendation.get("summary")
        or recommendation.get("rationale")
        or ai_research
    )

    if supplied_summary:
        summary_text = _clean_text(supplied_summary)
    else:
        overall_score = scores.get("overall")
        revenue_value = _first_present(
            company_data,
            "revenue",
            "total_revenue",
            "totalRevenue",
        )
        operating_margin_value = _first_present(
            company_data,
            "operating_margin",
            "operatingMargins",
        )
        free_cash_flow_value = _first_present(
            company_data,
            "free_cash_flow",
            "freeCashflow",
        )
        target_mean_value = analyst_data.get("target_mean")
        consensus_value = analyst_data.get("recommendation_key")

        summary_sentences = [
            (
                f"{_clean_text(company_name)} operates in the "
                f"{_clean_text(_first_present(company_data, 'industry', default='public markets'))} "
                f"industry and currently trades at {_money(current_price)} per share."
            )
        ]

        performance_details = []

        if _is_number(revenue_value):
            performance_details.append(
                f"revenue of {_money(revenue_value)}"
            )

        if _is_number(operating_margin_value):
            performance_details.append(
                f"an operating margin of {_percent(operating_margin_value)}"
            )

        if _is_number(free_cash_flow_value):
            performance_details.append(
                f"free cash flow of {_money(free_cash_flow_value)}"
            )

        if performance_details:
            summary_sentences.append(
                "The company reports "
                + ", ".join(performance_details)
                + "."
            )

        if _is_number(overall_score):
            score_value = float(overall_score)

            if score_value >= 80:
                score_description = "strong"
            elif score_value >= 60:
                score_description = "moderate"
            else:
                score_description = "weak"

            summary_sentences.append(
                f"Its financial scorecard is {score_description}, "
                f"with an overall score of {score_value:.0f} out of 100."
            )

        if consensus_value:
            consensus_text = (
                str(consensus_value)
                .replace("_", " ")
                .replace("-", " ")
                .strip()
                .title()
            )

            analyst_sentence = (
                f"Wall Street consensus is {consensus_text}"
            )

            if (
                _is_number(target_mean_value)
                and _is_number(current_price)
                and float(current_price) != 0
            ):
                implied_change = (
                    (
                        float(target_mean_value)
                        - float(current_price)
                    )
                    / float(current_price)
                    * 100
                )

                direction = (
                    "upside"
                    if implied_change >= 0
                    else "downside"
                )

                analyst_sentence += (
                    f", with a mean price target of "
                    f"{_money(target_mean_value)} implying "
                    f"{abs(implied_change):.1f}% {direction}"
                )

            summary_sentences.append(analyst_sentence + ".")

        summary_sentences.append(
            "Investors should weigh the company's financial strength, "
            "valuation, competitive position, and market risks before "
            "making an investment decision."
        )

        summary_text = " ".join(summary_sentences)

    story.append(Paragraph(summary_text, styles["Body"]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(_section_title("Company Overview", styles))

    overview_metrics = [
        (
            "Sector",
            _clean_text(
                _first_present(company_data, "sector", default="N/A")
            ),
        ),
        (
            "Industry",
            _clean_text(
                _first_present(company_data, "industry", default="N/A")
            ),
        ),
        ("Current Price", _money(current_price)),
        ("Market Capitalization", _money(market_cap)),
        (
            "Enterprise Value",
            _money(
                _first_present(
                    company_data,
                    "enterprise_value",
                    "enterpriseValue",
                )
            ),
        ),
        (
            "Trailing P/E",
            _number(
                _first_present(
                    company_data,
                    "trailing_pe",
                    "trailingPE",
                ),
                2,
            ),
        ),
        (
            "Forward P/E",
            _number(
                _first_present(
                    company_data,
                    "forward_pe",
                    "forwardPE",
                ),
                2,
            ),
        ),
        (
            "Dividend Yield",
            _percent(
                _first_present(
                    company_data,
                    "dividend_yield",
                    "dividendYield",
                )
            ),
        ),
    ]

    story.append(_metric_table(overview_metrics, styles))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_title("Financial Scorecard", styles))

    score_metrics = [
        (
            "Overall",
            (
                f"{_number(scores.get('overall'), 0)} / 100"
                if _is_number(scores.get("overall"))
                else "N/A"
            ),
        ),
        (
            "Profitability",
            (
                f"{_number(scores.get('profitability'), 0)} / 100"
                if _is_number(scores.get("profitability"))
                else "N/A"
            ),
        ),
        (
            "Balance Sheet",
            (
                f"{_number(scores.get('balance_sheet'), 0)} / 100"
                if _is_number(scores.get("balance_sheet"))
                else "N/A"
            ),
        ),
        (
            "Valuation",
            (
                f"{_number(scores.get('valuation'), 0)} / 100"
                if _is_number(scores.get("valuation"))
                else "N/A"
            ),
        ),
        (
            "Market Performance",
            (
                f"{_number(scores.get('market_performance'), 0)} / 100"
                if _is_number(scores.get("market_performance"))
                else "N/A"
            ),
        ),
    ]

    story.append(_metric_table(score_metrics, styles))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_title("Profitability and Financial Health", styles))

    financial_metrics = [
        (
            "Revenue",
            _money(
                _first_present(
                    company_data,
                    "revenue",
                    "total_revenue",
                    "totalRevenue",
                )
            ),
        ),
        (
            "Net Income",
            _money(
                _first_present(
                    company_data,
                    "net_income",
                    "netIncomeToCommon",
                )
            ),
        ),
        (
            "Profit Margin",
            _percent(
                _first_present(
                    company_data,
                    "profit_margin",
                    "profitMargins",
                )
            ),
        ),
        (
            "Operating Margin",
            _percent(
                _first_present(
                    company_data,
                    "operating_margin",
                    "operatingMargins",
                )
            ),
        ),
        (
            "Return on Equity",
            _ratio_percent(
                _first_present(
                    company_data,
                    "return_on_equity",
                    "returnOnEquity",
                )
            ),
        ),
        (
            "Free Cash Flow",
            _money(
                _first_present(
                    company_data,
                    "free_cash_flow",
                    "freeCashflow",
                )
            ),
        ),
        (
            "Total Cash",
            _money(
                _first_present(
                    company_data,
                    "total_cash",
                    "totalCash",
                )
            ),
        ),
        (
            "Total Debt",
            _money(
                _first_present(
                    company_data,
                    "total_debt",
                    "totalDebt",
                )
            ),
        ),
    ]

    story.append(_metric_table(financial_metrics, styles))

    if isinstance(financial_trends, pd.DataFrame) and not financial_trends.empty:
        story.append(Spacer(1, 0.22 * inch))
        story.append(_section_title("Recent Financial Trends", styles))

        revenue_chart = _revenue_trend_chart(
            financial_trends
        )

        if revenue_chart is not None:
            story.append(revenue_chart)
            story.append(Spacer(1, 0.12 * inch))

        trends_table = _dataframe_table(
            financial_trends.sort_index(ascending=False),
            styles,
        )

        if trends_table is not None:
            story.append(trends_table)

    story.append(PageBreak())
    story.append(_section_title("Analyst Estimates", styles))

    analyst_metrics = [
        (
            "Mean Price Target",
            _money(analyst_data.get("target_mean")),
        ),
        (
            "Median Price Target",
            _money(analyst_data.get("target_median")),
        ),
        (
            "Low Price Target",
            _money(analyst_data.get("target_low")),
        ),
        (
            "High Price Target",
            _money(analyst_data.get("target_high")),
        ),
        (
            "Analyst Coverage",
            (
                f"{int(float(analyst_data['analyst_count']))} analysts"
                if _is_number(analyst_data.get("analyst_count"))
                else "N/A"
            ),
        ),
        (
            "Consensus",
            _clean_text(
                analyst_data.get("recommendation_key")
            )
            .replace("_", " ")
            .title(),
        ),
    ]

    story.append(_metric_table(analyst_metrics, styles))

    revenue_estimates = analyst_data.get("revenue_estimates")
    earnings_estimates = analyst_data.get("earnings_estimates")

    if isinstance(revenue_estimates, pd.DataFrame) and not revenue_estimates.empty:
        story.append(Spacer(1, 0.2 * inch))
        story.append(_section_title("Revenue Estimates", styles))

        table = _dataframe_table(revenue_estimates, styles)

        if table is not None:
            story.append(table)

    if isinstance(earnings_estimates, pd.DataFrame) and not earnings_estimates.empty:
        story.append(Spacer(1, 0.2 * inch))
        story.append(_section_title("Earnings Estimates", styles))

        table = _dataframe_table(earnings_estimates, styles)

        if table is not None:
            story.append(table)

    story.append(Spacer(1, 0.2 * inch))
    story.append(_section_title("Investment Recommendation", styles))

    recommendation_text = (
        recommendation.get("recommendation")
        or recommendation.get("rating")
        or analyst_data.get("recommendation_key")
        or "N/A"
    )

    target_price_value = (
        recommendation.get("target_price")
        or analyst_data.get("target_mean")
    )

    expected_upside = None

    if (
        _is_number(current_price)
        and _is_number(target_price_value)
        and float(current_price) != 0
    ):
        expected_upside = (
            (
                float(target_price_value)
                - float(current_price)
            )
            / float(current_price)
            * 100
        )

    recommendation_metrics = [
        (
            "Recommendation",
            _clean_text(recommendation_text)
            .replace("_", " ")
            .title(),
        ),
        (
            "Current Price",
            _money(current_price),
        ),
        (
            "Mean Target",
            _money(target_price_value),
        ),
        (
            "Expected Upside",
            (
                f"{expected_upside:+.1f}%"
                if expected_upside is not None
                else "N/A"
            ),
        ),
    ]

    story.append(_metric_table(recommendation_metrics, styles))

    rationale = (
        recommendation.get("rationale")
        or recommendation.get("summary")
    )

    if rationale:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(_clean_text(rationale), styles["Body"]))

    dcf_intrinsic_value = _first_present(
        dcf_data,
        "intrinsic_value",
        "intrinsic_value_per_share",
        "fair_value",
    )
    dcf_growth_rate = _first_present(
        dcf_data,
        "growth_rate",
        "fcf_growth_rate",
    )
    dcf_discount_rate = _first_present(
        dcf_data,
        "discount_rate",
        "wacc",
    )
    dcf_terminal_growth = _first_present(
        dcf_data,
        "terminal_growth_rate",
        "terminal_growth",
    )
    dcf_projection_years = _first_present(
        dcf_data,
        "projection_years",
        "years",
    )

    has_dcf_results = any(
        _is_number(value)
        for value in (
            dcf_intrinsic_value,
            dcf_growth_rate,
            dcf_discount_rate,
            dcf_terminal_growth,
            dcf_projection_years,
        )
    )

    if has_dcf_results:
        story.append(_section_title("DCF Valuation", styles))

        dcf_metrics = [
            (
                "Intrinsic Value per Share",
                _money(dcf_intrinsic_value),
            ),
            (
                "Current Price",
                _money(
                    _first_present(
                        dcf_data,
                        "current_price",
                        default=current_price,
                    )
                ),
            ),
            (
                "Annual FCF Growth",
                _percent(dcf_growth_rate),
            ),
            (
                "Discount Rate / WACC",
                _percent(dcf_discount_rate),
            ),
            (
                "Terminal Growth",
                _percent(dcf_terminal_growth),
            ),
            (
                "Projection Years",
                _number(dcf_projection_years, 0),
            ),
        ]

        story.append(_metric_table(dcf_metrics, styles))

    if ai_research:
        story.append(PageBreak())
        story.append(_section_title("AI Research Summary", styles))
        story.append(Paragraph(_clean_text(ai_research), styles["Body"]))

    if news_summary:
        story.append(Spacer(1, 0.2 * inch))
        story.append(_section_title("News Intelligence Summary", styles))
        story.append(Paragraph(_clean_text(news_summary), styles["Body"]))

    story.append(Spacer(1, 0.3 * inch))
    story.append(_section_title("Important Disclaimer", styles))
    story.append(
        Paragraph(
            "This report is provided solely for educational and informational "
            "purposes. It does not constitute investment, legal, accounting, "
            "tax, or financial advice. Market data may be delayed, incomplete, "
            "or inaccurate. Financial projections and valuation models rely on "
            "assumptions that may not occur. Investors should conduct independent "
            "research and consult qualified professionals before making decisions.",
            styles["Disclaimer"],
        )
    )

    document.build(
        story,
        onFirstPage=_add_page_number,
        onLaterPages=_add_page_number,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
