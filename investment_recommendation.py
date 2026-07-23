from openai import OpenAI

client = OpenAI()


def generate_investment_recommendation(
    company_data,
    financial_scores,
    dcf_results,
    news_analysis,
):
    prompt = f"""
You are a Senior Wall Street Equity Research Analyst.

Company:
{company_data}

Financial Scores:
{financial_scores}

DCF:
{dcf_results}

Research:
{news_analysis}

Write a professional report using markdown.

Include these sections:

# Investment Rating
(BUY, HOLD or SELL)

# Confidence Score
(1-10)

# Investment Thesis

# Key Risks

# Valuation Opinion

# Best Investor Type

# Suggested Holding Period

Keep the report under 500 words.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text