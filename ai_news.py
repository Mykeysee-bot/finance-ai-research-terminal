from typing import Any, Dict, List

from openai import OpenAI


client = OpenAI()


def generate_news_analysis(
    ticker_symbol: str,
    company_name: str,
    news_articles: List[Dict[str, Any]],
) -> str:
    if not news_articles:
        return "No recent news was available for analysis."

    article_text = []

    for index, article in enumerate(news_articles, start=1):
        article_text.append(
            f"""
Article {index}
Title: {article.get("title", "N/A")}
Publisher: {article.get("publisher", "N/A")}
Date: {article.get("published_at", "N/A")}
Summary: {article.get("summary", "N/A")}
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

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text