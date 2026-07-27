from datetime import datetime
from typing import Any, Dict, List

import yfinance as yf


def get_company_news(
    ticker_symbol: str,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    ticker = yf.Ticker(ticker_symbol)

    try:
        raw_news = ticker.news
    except Exception:
        return []

    cleaned_news = []

    for article in raw_news[:limit]:
        content = article.get("content", article)

        title = content.get("title")
        summary = content.get("summary")
        publisher = content.get("provider", {}).get("displayName")
        published_at = content.get("pubDate")

        canonical_url = content.get("canonicalUrl", {})
        click_through_url = content.get("clickThroughUrl", {})

        link = (
            canonical_url.get("url")
            or click_through_url.get("url")
            or content.get("link")
        )

        formatted_date = "N/A"

        if published_at:
            try:
                parsed_date = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
                formatted_date = parsed_date.strftime(
                    "%b %d, %Y at %I:%M %p"
                )
            except (ValueError, AttributeError):
                formatted_date = str(published_at)

        if not title:
            continue

        cleaned_news.append(
            {
                "title": title,
                "summary": summary or "No summary available.",
                "publisher": publisher or "Unknown Publisher",
                "published_at": formatted_date,
                "link": link,
            }
        )

    return cleaned_news