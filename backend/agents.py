import logging
from dotenv import load_dotenv
load_dotenv()

from crewai import Agent
from langchain_openai import ChatOpenAI
from backend.tools.financial_tools import FinancialDocumentTool, search_tool
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    temperature=settings.LLM_TEMPERATURE,
    api_key=settings.OPENAI_API_KEY,
    max_retries=3,
    request_timeout=120,
)

financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal="Provide accurate, comprehensive financial analysis based on the query: {query}",
    verbose=True,
    memory=True,
    backstory=(
        "Experienced financial analyst with 15+ years in banking and equity research. "
        "Analyze statements, compute ratios, and provide balanced insights with risks."
    ),
    tools=[FinancialDocumentTool.read_document, search_tool],
    llm=llm,
    max_iter=3,
    max_rpm=60,
    allow_delegation=False,
)

document_verifier = Agent(
    role="Financial Document Validator",
    goal="Verify document authenticity and extract key financial data with high accuracy",
    verbose=True,
    memory=True,
    backstory=(
        "Specialist in GAAP/IFRS/SEC reporting. Validate integrity and extract accurate data."
    ),
    tools=[FinancialDocumentTool.read_document],
    llm=llm,
    max_iter=2,
    max_rpm=60,
    allow_delegation=False,
)

investment_advisor = Agent(
    role="Investment Strategy Advisor",
    goal="Provide strategic investment recommendations based on comprehensive financial analysis",
    verbose=True,
    memory=True,
    backstory=(
        "CFA charterholder focused on portfolio management, risk, and allocation."
    ),
    tools=[search_tool],
    llm=llm,
    max_iter=3,
    max_rpm=60,
    allow_delegation=False,
)

risk_assessor = Agent(
    role="Financial Risk Assessment Expert",
    goal="Conduct thorough risk analysis and provide comprehensive risk management strategies",
    verbose=True,
    memory=True,
    backstory=(
        "Risk professional in liquidity/credit/market risk, stress testing, and compliance."
    ),
    tools=[FinancialDocumentTool.read_document, search_tool],
    llm=llm,
    max_iter=3,
    max_rpm=60,
    allow_delegation=False,
)
