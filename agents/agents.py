import os

from crewai import Agent
from crewai.llm import LLM
from dotenv import load_dotenv

from tools.tools import exa_search_tool, log_reader_tool

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"

selected_model = os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL
print(f"Selected model = {selected_model}")

llm1 = LLM(
    model="nvidia_nim/openai/gpt-oss-120b",
    api_key="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",
    # base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.7
)

llm2 = LLM(
    model="nvidia_nim/openai/gpt-oss-120b",
    api_key="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",
    # base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.7
)

llm3 = LLM(
    model="nvidia_nim/openai/gpt-oss-120b",
    api_key="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",
    # base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.7
)

# print(f"CrewAI model = {llm.model}")
log_analyzer = Agent(
    role="DevOps Log Analyzer",
    goal="Analyze log files to identify and extract specific issues, errors, and failure patterns",
    llm=llm1,
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
    llm=llm2,
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
    llm=llm3,
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