import os

from crewai import Agent
from crewai.llm import LLM
from dotenv import load_dotenv

from tools.tools import exa_search_tool, log_reader_tool

load_dotenv()

DEFAULT_MODEL = "openrouter/openai/gpt-4o-mini"

selected_model = os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL

llm = LLM(
     model="ollama/qwen3:8b",
    base_url="http://localhost:11434"
)

log_analyzer = Agent(
    role="DevOps Log Analyzer",
    goal="Analyze log files to identify and extract specific issues, errors, and failure patterns",
    llm=llm,
    backstory="""You are a senior DevOps engineer with 10 years of experience in 
    analyzing production logs and identifying critical issues. You excel at parsing 
    through complex log files, identifying error patterns, extracting relevant error 
    messages, and determining the root cause of failures from log data.""",
    tools=[log_reader_tool],
    verbose=True,
    respect_context_window=True,
    max_iter=3,
    max_execution_time=300,
    max_rpm=10,
)

issue_investigator = Agent(
    role="DevOps Issue Investigator",
    goal="Investigate identified issues by searching documentation, forums, and known solutions online",
    llm=llm,
    backstory="""You are a DevOps troubleshooting specialist who excels at quickly 
    finding solutions to technical problems. You know how to search effectively for 
    similar issues, identify reliable sources, and gather comprehensive information 
    about error patterns and their solutions.""",
    tools=[exa_search_tool],
    verbose=True,
    respect_context_window=True,
    max_iter=5,
    max_execution_time=600,
    max_rpm=15,
)

solution_specialist = Agent(
    role="DevOps Solution Specialist",
    goal="Provide clear, actionable solutions with step-by-step instructions based on investigation findings",
    llm=llm,
    backstory="""You are a DevOps solutions architect who specializes in creating 
    reliable, step-by-step remediation plans for infrastructure and deployment issues. 
    You always provide official documentation references, tested solutions, and 
    preventive measures to avoid future occurrences.""",
    verbose=True,
    respect_context_window=True,
    max_iter=4,
    max_execution_time=450,
    max_rpm=8,
)