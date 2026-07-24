from pathlib import Path
from typing import Any, Dict, List, Mapping
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path.cwd() / ".env")


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        try:
            import streamlit as st

            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found. Add it to Streamlit Secrets."
        )

    return OpenAI(api_key=api_key)


def generate_news_analysis(
    company_data: Mapping[str, Any],
    news_items: List[Dict[str, Any]],
) -> str:
    ticker_symbol = str(
        company_data.get("ticker")
        or company_data.get("symbol")
        or "Unknown"
    )

    company_name = str(
        company_data.get("company_name")
        or company_data.get("name")
        or ticker_symbol
    )

    if not news_items:
        return "No recent news was available for analysis."

    article_text = []

    for index, article in enumerate(news_items, start=1):
        article_text.append(
            f"""
Article {index}
Title: {article.get("title", "N/A")}
Publisher: {article.get("publisher", article.get("source", "N/A"))}
Date: {article.get("published_at", article.get("published", "N/A"))}
Summary: {article.get("summary", article.get("description", "N/A"))}
"""
        )

    combined_articles = "\n".join(article_text)

    prompt = f"""
You are an equity research analyst.

Analyze the following recent news for {company_name} ({ticker_symbol}).

Recent news:
{combined_articles}

Create a concise investor-focused report using these exact headings:

## Recent News Summary

Summarize the most important developments.

## Bullish Developments

Explain any news that could positively affect revenue, earnings, growth,
competitive position, or investor sentiment.

## Bearish Developments

Explain any news that could negatively affect the company, including risks,
competition, regulation, valuation concerns, or operational problems.

## Investment Impact

Classify the overall news impact as one of:

- Bullish
- Slightly Bullish
- Neutral
- Slightly Bearish
- Bearish

Explain the classification.

## What Investors Should Watch

List the most important upcoming issues, announcements, or risks.

Do not invent information that is not present in the supplied articles.
Use clear language and short paragraphs.
"""

    client = get_openai_client()

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text


# Compatibility name for app.py
def generate_ai_news_analysis(
    company_data: Mapping[str, Any],
    news_items: List[Dict[str, Any]],
) -> str:
    return generate_news_analysis(company_data, news_items)
