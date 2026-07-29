from typing import Any, Dict, List

from openai import OpenAI


client = OpenAI()


def generate_news_analysis(
    ticker_symbol: str,
    company_name: str,
    news_articles: List[Dict[str, Any]],
) -> str:
    """
    Generate a professional investor-focused analysis of recent company news.
    """

    if not news_articles:
        return "No recent news was available for analysis."

    article_sections = []

    for index, article in enumerate(news_articles, start=1):
        article_sections.append(
            f"""
ARTICLE {index}

Title: {article.get("title", "N/A")}
Publisher: {article.get("publisher", "N/A")}
Published: {article.get("published_at", "N/A")}
Summary: {article.get("summary", "N/A")}
"""
        )

    combined_articles = "\n".join(article_sections)

    prompt = f"""
You are a senior equity research analyst preparing an investor-focused
news intelligence report for {company_name} ({ticker_symbol}).

Use only the supplied articles. Do not invent events, dates, quotations,
financial impacts, management commentary, forecasts, competitors, or
market reactions.

RECENT ARTICLES
{combined_articles}

Write a professional Markdown report using exactly these headings:

## Executive News Summary

Summarize the two to four most important developments in concise paragraphs.
Prioritize developments with the greatest likely relevance to revenue,
earnings, operations, regulation, valuation, or investor sentiment.

## Overall News Sentiment

Classify the overall news tone using exactly one of these labels:

**Bullish**
**Slightly Bullish**
**Neutral**
**Slightly Bearish**
**Bearish**

Explain the classification in two to four sentences.

Do not classify sentiment as bullish merely because an article is promotional.
Separate factual developments from opinion or speculation.

## Positive Catalysts

Provide two to five bullet points describing developments that may support
revenue, earnings, margins, growth, competitive positioning, or investor
sentiment.

For each point:
- identify the relevant article development,
- explain why it may matter financially,
- avoid stating uncertain outcomes as facts.

If the supplied articles contain no credible positive catalyst, state that
directly.

## Negative Catalysts and Risks

Provide two to five bullet points describing developments that may pressure
revenue, earnings, margins, operations, regulation, valuation, or sentiment.

Distinguish confirmed developments from potential risks.

If the supplied articles contain no credible negative development, state that
directly.

## Expected Market Impact

Classify the likely near-term impact using exactly one label:

**High Positive**
**Moderate Positive**
**Limited Positive**
**Neutral**
**Limited Negative**
**Moderate Negative**
**High Negative**

Explain the classification.

Do not predict a specific share-price move. Acknowledge when the likely market
impact is uncertain or may already be reflected in the stock price.

## Financial Relevance

Explain which financial areas could be affected by the news, such as:

- revenue growth,
- operating margins,
- capital spending,
- free cash flow,
- balance-sheet risk,
- valuation expectations.

Use only areas supported by the supplied articles. Do not invent numerical
effects.

## What Investors Should Watch

Provide three to five concise bullet points covering the most important
follow-up items.

Only include future events, milestones, disclosures, or risks that are
reasonably supported by the article content. Do not invent dates or events.

## Investor Takeaway

Provide a balanced conclusion in no more than 120 words.

Summarize:
- the dominant news signal,
- the most important positive factor,
- the most important risk,
- whether the news materially changes the investment case.

ADDITIONAL RULES

- Keep the full report below 700 words.
- Use concise, professional language.
- Explain why developments matter instead of only repeating headlines.
- Do not provide personalized financial advice.
- Do not use LaTeX.
- Do not fabricate facts to fill missing information.
- State clearly when the article set is insufficient for a strong conclusion.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    result = response.output_text.strip()

    if not result:
        raise RuntimeError(
            "The news-analysis model returned an empty response."
        )

    return result
