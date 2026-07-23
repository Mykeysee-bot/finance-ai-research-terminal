# Finance AI Research Terminal

An AI-powered public-equity research, analytics, and valuation platform built with Python and Streamlit.

## Overview

The Finance AI Research Terminal combines market data, company fundamentals, financial statements, analyst estimates, news intelligence, peer comparison, financial scoring, investment recommendations, and discounted cash flow valuation in one interactive application.

Users can enter a public-company ticker and review both quantitative financial analysis and AI-assisted qualitative research.

## Core Features

- Company overview with market data and valuation metrics
- Financial scorecard across profitability, balance sheet, valuation, and market performance
- Annual and quarterly financial statements
- Revenue, earnings, EBITDA, EPS, margin, and free-cash-flow trend analysis
- Analyst price targets, recommendation consensus, and forward estimates
- AI-generated company research
- News intelligence and sentiment analysis
- Investment recommendation engine
- Peer-company comparison
- Discounted cash flow valuation
- DCF scenarios and sensitivity analysis
- CSV exports for financial statements and trend data

## Technology Stack

- Python
- Streamlit
- yfinance
- Pandas
- Plotly
- OpenAI API
- python-dotenv

## Project Structure

```text
app.py
ai_analysis.py
ai_news.py
investment_recommendation.py
comparison.py
ai_comparison.py
dcf_model.py
dcf_scenarios.py
dcf_sensitivity.py
financial_score.py
market_data.py
company_news.py
requirements.txt
README.md
.env
```

## Local Installation

### 1. Clone or download the project

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Add environment variables

Create a `.env` file in the project folder:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not upload the `.env` file to GitHub.

### 5. Run the application

```bash
python -m streamlit run app.py
```

## Deployment

This project can be deployed with Streamlit Community Cloud.

1. Upload the project to GitHub.
2. Open Streamlit Community Cloud.
3. Connect the GitHub repository.
4. Select `app.py` as the main file.
5. Add `OPENAI_API_KEY` under application secrets.
6. Deploy the application.

## Analytical Methodology

### Data Collection

The application retrieves market prices, company fundamentals, financial statements, analyst estimates, and company news from external data providers.

### Financial Analysis

Raw data is transformed into financial ratios, growth rates, scorecards, trend charts, peer comparisons, and valuation outputs.

### AI Interpretation

AI modules summarize company performance, identify risks and catalysts, analyze news, and generate structured investment commentary.

## Resume Description

> Built an AI-powered public-equity research platform using Python and Streamlit that integrates market data, financial statements, multi-year trend analysis, analyst estimates, news intelligence, peer comparisons, financial scoring, investment recommendations, and DCF valuation for publicly traded companies.

## Disclaimer

Market and company data may be delayed, incomplete, or differently defined across providers. Analyst estimates may change frequently. AI-generated research may contain errors and is not personalized investment advice.
