# log-analysis-agents

This project is a small CrewAI-based multi-agent system for analyzing Kubernetes-style deployment logs, finding root causes, investigating related issues online, and generating a remediation plan.

## What this project does

The workflow starts from a real log file, then uses three specialized AI agents in sequence:

1. The Log Analyzer reads the log and extracts the main failure patterns.
2. The Issue Investigator searches online for known causes and documented fixes.
3. The Solution Specialist turns the findings into a practical remediation plan.

The system is designed to simulate a DevOps troubleshooting workflow with AI agents, tools, and basic guardrails.

## Project architecture

The repository is organized as follows:

- main.py — entry point that creates the crew and starts the workflow.
- agents/agents.py — defines the three agents and their LLM configuration.
- tasks/tasks.py — defines the tasks, expected outputs, and guardrail validation.
- tools/tools.py — wires the file-reader tool and the EXA web-search tool.
- kubernetes_log.log — sample log used for the demo run.
- task_outputs/ — generated reports from the crew run.

### High-level flow

1. main.py loads the sample log path and creates a Crew with three tasks.
2. The first task asks the Log Analyzer to inspect the log file.
3. The second task uses the investigation agent to search for similar issues online.
4. The third task uses the solution agent to summarize the result as a remediation plan.
5. Task outputs are saved under task_outputs/.

## Multi-agent workflow

The current crew uses a sequential process:

- Process: sequential
- Agents:
  - log_analyzer
  - issue_investigator
  - solution_specialist
- Tasks:
  - analyze_logs_task
  - investigate_issue_task
  - provide_solution_task

Each task depends on the previous findings for context, which makes the system behave like a chain of reasoning:

- Analyze the raw log
- Investigate the likely root cause
- Generate a concrete solution

This is the core multi-agent design of the project.

## Agent roles

### 1. DevOps Log Analyzer

Role: analyze log files and identify incidents, errors, warnings, timelines, and likely root causes.

Responsibilities:
- Parse deployment and runtime log lines
- Detect error patterns such as ImagePullBackOff, CrashLoopBackOff, and sandbox failures
- Create a structured analysis report

### 2. DevOps Issue Investigator

Role: research the identified problem using external search.

Responsibilities:
- Search the internet for related error messages
- Gather official docs, forum posts, and known troubleshooting guidance
- Rank likely causes and proven fixes

### 3. DevOps Solution Specialist

Role: convert investigation findings into actionable remediation steps.

Responsibilities:
- Produce a step-by-step remediation plan
- Include commands and verification steps
- Recommend monitoring and prevention measures

## Tools used by the agents

### File reader tool

The log analyzer uses a file reader tool to inspect the sample log file.

### EXA search tool

The investigation agent uses EXA to search the public web for similar issues and community guidance.

## Guardrails and quality checks

The project includes a simple guardrail in tasks/tasks.py:

- The log analysis task validates that at least one error was actually found.
- If the model output is too vague or empty, the task is retried.

This helps reduce low-quality or empty analysis results.

## Output artifacts

After a run, the project writes reports to task_outputs/:

- log_analysis.md
- investigation_report.md
- solution_plan.md

These files capture the different stages of the multi-agent reasoning process.

## Setup

1. Use Python 3.13 for the project environment. The current dependency set is tested against Python 3.13.
2. Create the project virtual environment:
   py -3.13 -m venv .venv
3. Activate it in PowerShell:
   .\.venv\Scripts\Activate.ps1
4. Install dependencies:
   python -m pip install -r requirements.txt
5. Add your API keys to .env before running the crew.

### Model configuration

The default model is configured in agents/agents.py and can be overridden with OPENROUTER_MODEL in .env.

Recommended notes:
- Free OpenRouter models are rate-limited and may return 429 or 402 errors when quota is exhausted.
- If you hit those limits, add credits at OpenRouter or switch to a paid model in .env.

## Run

From the project root:

python main.py

The sample input used by the demo is the repository file kubernetes_log.log.

## Notes

- The .env file is required because the agents and tools load environment variables at startup so create a .env in your current environment.
- The OpenRouter key must have available credits for the LLM requests to succeed.
- The current system is intentionally simple and easy to extend with more agents, more tools, or more structured output formats.
