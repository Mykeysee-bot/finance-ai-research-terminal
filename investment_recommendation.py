from typing import Any, Mapping

from openai import OpenAI


client = OpenAI()


def generate_investment_recommendation(
    company_data: Mapping[str, Any],
    financial_scores: Mapping[str, Any],
    analysis: Any = None,
    news_analysis: Any = None,
) -> str:
    """
    Generate a professional investment recommendation using only the
    financial data and research supplied by the application.
    """

    prompt = f"""
You are a senior equity research analyst preparing an institutional-quality
investment recommendation.

Use only the information supplied below. Do not invent facts, news, forecasts,
competitors, market-share figures, price targets, or catalysts.

COMPANY DATA
{company_data}

FINANCIAL SCORECARD
{financial_scores}

AI EQUITY RESEARCH
{analysis if analysis else "Not available"}

NEWS ANALYSIS
{news_analysis if news_analysis else "Not available"}

Write a professional Markdown report using exactly these headings:

## Executive Recommendation

State one rating:
STRONG BUY, BUY, HOLD, SELL, or STRONG SELL.

Immediately explain the rating in 2 to 4 sentences. The explanation must balance
financial quality, valuation, growth expectations, market performance, and risk.

## Confidence Assessment

Give a confidence score from 1 to 10.

Explain what strengthens or limits confidence. Clearly identify missing,
incomplete, stale, or forward-looking inputs.

## Investment Thesis

Provide 3 to 5 concise bullet points explaining the central investment case.
Focus on the factors that matter most to an investor.

## Financial Quality

Provide 3 to 5 bullet points assessing profitability, margins, returns on
capital, cash generation, and balance-sheet strength.

Explain why the metrics matter instead of merely repeating them.

## Valuation Assessment

Assess the available valuation metrics in context.

Rules:
- Do not claim that a low forward P/E or PEG ratio proves undervaluation.
- Do not claim that a high multiple automatically means overvaluation.
- Clearly distinguish historical metrics from forward-looking estimates.
- State when the supplied data is insufficient for a firm valuation conclusion.
- Do not invent a fair value or price target.

## Growth Drivers

Provide 2 to 4 bullet points using only growth evidence or forward-looking
information contained in the supplied materials.

If no reliable growth-driver information is available, say so directly.

## Key Risks

Provide 3 to 5 specific bullet points.

Include valuation risk, execution risk, financial risk, earnings-expectation
risk, or market-sensitivity risk when supported by the supplied information.

Do not invent company-specific events.

## Bull and Bear Balance

Use this exact format:

**Bull Case Strength:** Low, Moderate, or High  
**Bear Case Strength:** Low, Moderate, or High

Then explain in 2 to 4 sentences which side currently has the stronger evidence
and why.

## Suitable Investor Profile

Explain which type of investor may find the risk-and-return profile appropriate.

Do not provide personalized financial advice or assume the investor's age,
income, wealth, objectives, or risk tolerance.

## Suggested Holding Period

Choose one:
- Short term: under 12 months
- Medium term: 1 to 3 years
- Long term: 3 years or more

Explain the choice in 1 to 3 sentences.

## Bottom Line

Provide a decisive final conclusion in no more than 100 words. State the rating
again and summarize the main reason supporting it and the most important risk
that could invalidate it.

ADDITIONAL RULES
- Keep the full report under 750 words.
- Use clear, direct professional language.
- Do not use dollar signs unless quoting supplied data. Prefer USD.
- Do not use LaTeX.
- Do not repeat the same metric across several sections.
- Do not present speculation as fact.
- Do not describe this output as personalized financial advice.
- Avoid generic phrases such as "investors should do their own research."
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    result = response.output_text.strip()

    if not result:
        raise RuntimeError(
            "The investment recommendation model returned an empty response."
        )

    return result
