from crewai import Task
from agents import financial_analyst, document_verifier, investment_advisor, risk_assessor
from tools.financial_tools import ParseDocTool
from tools.search_tool import SerperSearchTool
search_tool = SerperSearchTool()
read_tool=ParseDocTool()

verification_task = Task(
    description="""Verify and validate the financial document at {file_path}.
1) Confirm the document contains legitimate financial data
2) Identify the document type and reporting period
3) Extract key metrics (revenue, profit, assets, liabilities)
4) Verify data integrity and consistency
5) Flag anomalies or data quality issues""",
    expected_output="""Verification Report:
- Document type & period
- Key metrics extracted
- Data quality assessment (with confidence)
- Anomalies/inconsistencies
- Status: VERIFIED / NEEDS_REVIEW / REJECTED""",
    agent=document_verifier,
    tools=[read_tool],
    async_execution=False,
)

financial_analysis_task = Task(
    description="""Analyze the verified document per user query: {query}
Include: trends (revenue, margins), ratios (liquidity, leverage, efficiency),
balance sheet quality, cash flows, and industry comparisons.""",
    expected_output="""Financial Analysis:
- Executive summary
- Quantitative metrics & ratios
- Trend analysis
- Strengths/weaknesses with data
- Industry context""",
    agent=financial_analyst,
    tools=[read_tool, search_tool],
    async_execution=False,
)

risk_analysis_task = Task(
    description="""Provide a comprehensive risk assessment:
liquidity/credit/market/operational risk, business model durability, regulatory,
macro/industry risks, ESG factors. Quantify where possible.""",
    expected_output="""Risk Assessment:
- Overall rating & rationale
- Category breakdown with severity
- Key indicators & warnings
- Mitigation strategies
- Stress scenarios""",
    agent=risk_assessor,
    tools=[read_tool, search_tool],
    async_execution=False,
)

investment_recommendation_task = Task(
    description="""Based on financial & risk analysis and user query {query},
provide an evidence-based investment recommendation with approach, sizing,
entry/exit, diversification impact, and alternative scenarios.""",
    expected_output="""Investment Recommendation:
- Thesis & data support
- BUY/HOLD/SELL + target(s)
- Risk-adjusted return & horizon
- Position sizing
- Catalysts/milestones
- Bull/base/bear with probabilities
- Implementation notes""",
    agent=investment_advisor,
    tools=[search_tool],
    async_execution=False,
)
