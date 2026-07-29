from datetime import datetime
from typing import Any, Dict, List

import yfinance as yf


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def article_relevance_score(
    article: Dict[str, Any],
    ticker_symbol: str,
    company_name: str = "",
) -> int:
    title = normalize_text(article.get("title"))
    summary = normalize_text(article.get("summary"))
    combined_text = f"{title} {summary}"

    ticker = normalize_text(ticker_symbol)
    company = normalize_text(company_name)

    company_terms = {
        ticker,
        company,
    }

    if company:
        company_terms.add(company.split()[0])

    company_terms = {
        term
        for term in company_terms
        if len(term) >= 2
    }

    score = 0

    for term in company_terms:
        if term in title:
            score += 5

        if term in summary:
            score += 2

    sector_terms = (
        "semiconductor",
        "chip",
        "artificial intelligence",
        "ai",
        "technology",
        "earnings",
        "stock",
    )

    for term in sector_terms:
        if term in combined_text:
            score += 1

    return score


def get_company_news(
    ticker_symbol: str,
    limit: int = 8,
    company_name: str = "",
) -> List[Dict[str, Any]]:
    ticker = yf.Ticker(ticker_symbol)

    try:
        raw_news = ticker.news
    except Exception:
        return []

    cleaned_news: List[Dict[str, Any]] = []

    for article in raw_news:
        if not isinstance(article, dict):
            continue

        content = article.get("content", article)

        if not isinstance(content, dict):
            continue

        title = content.get("title")
        summary = content.get("summary")

        provider = content.get("provider", {})
        publisher = (
            provider.get("displayName")
            if isinstance(provider, dict)
            else provider
        )

        published_at = content.get("pubDate")

        canonical_url = content.get("canonicalUrl", {})
        click_through_url = content.get("clickThroughUrl", {})

        canonical_link = (
            canonical_url.get("url")
            if isinstance(canonical_url, dict)
            else canonical_url
        )

        click_through_link = (
            click_through_url.get("url")
            if isinstance(click_through_url, dict)
            else click_through_url
        )

        link = (
            canonical_link
            or click_through_link
            or content.get("link")
        )

        formatted_date = "Date unavailable"

        if published_at:
            try:
                parsed_date = datetime.fromisoformat(
                    str(published_at).replace(
                        "Z",
                        "+00:00",
                    )
                )

                formatted_date = parsed_date.strftime(
                    "%b %d, %Y at %I:%M %p"
                )
            except (ValueError, AttributeError):
                formatted_date = str(published_at)

        if not title:
            continue

        cleaned_article = {
            "title": str(title).strip(),
            "summary": (
                str(summary).strip()
                if summary
                else "No summary available."
            ),
            "publisher": (
                str(publisher).strip()
                if publisher
                else "Unknown Publisher"
            ),
            "published_at": formatted_date,
            "link": link,
        }

        cleaned_article["relevance_score"] = article_relevance_score(
            cleaned_article,
            ticker_symbol,
            company_name,
        )

        cleaned_news.append(cleaned_article)

    cleaned_news.sort(
        key=lambda item: item.get(
            "relevance_score",
            0,
        ),
        reverse=True,
    )

    directly_relevant = [
        article
        for article in cleaned_news
        if article.get("relevance_score", 0) >= 2
    ]

    selected_articles = (
        directly_relevant
        if directly_relevant
        else cleaned_news
    )

    return selected_articles[:limit]