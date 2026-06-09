# log-analysis-agents

A small CrewAI-based multi-agent system for analyzing Kubernetes-style deployment logs, finding likely root causes, researching related issues online, and generating a remediation plan.

## What this project does

The workflow starts from a real log file, then uses three specialized AI agents in sequence:

1. The Log Analyzer reads the log and extracts the main failure patterns.
2. The Issue Investigator searches online for known causes and documented fixes.
3. The Solution Specialist turns the findings into a practical remediation plan.

The system is designed to simulate a DevOps troubleshooting workflow with AI agents, tools, and basic guardrails.

## Project architecture

The repository is organized as follows:

```text
.
|-- main.py                  # Entry point that creates the crew and starts the workflow
|-- agents/
|   `-- agents.py            # Agent definitions and LLM configuration
|-- tasks/
|   `-- tasks.py             # Tasks, expected outputs, and guardrail validation
|-- tools/
|   `-- tools.py             # File reader and EXA web-search tool wiring
|-- kubernetes_log.log       # Sample log used for the demo run
|-- task_outputs/            # Generated reports from the crew run
|-- requirements.txt         # Python dependencies
`-- README.md
```

### High-level flow

1. `main.py` loads the sample log path and creates a Crew with three tasks.
2. The first task asks the Log Analyzer to inspect the log file.
3. The second task uses the investigation agent to search for similar issues online.
4. The third task uses the solution agent to summarize the result as a remediation plan.
5. Task outputs are saved under `task_outputs/`.

## Multi-agent workflow

The current crew uses a sequential process:

- Process: `sequential`
- Agents:
  - `log_analyzer`
  - `issue_investigator`
  - `solution_specialist`
- Tasks:
  - `analyze_logs_task`
  - `investigate_issue_task`
  - `provide_solution_task`

Each task depends on the previous findings for context:

1. Analyze the raw log.
2. Investigate the likely root cause.
3. Generate a concrete solution.

This is the core multi-agent design of the project.

## Agent roles

### 1. DevOps Log Analyzer

Role: analyze log files and identify incidents, errors, warnings, timelines, and likely root causes.

Responsibilities:

- Parse deployment and runtime log lines.
- Detect error patterns such as `ImagePullBackOff`, `CrashLoopBackOff`, and sandbox failures.
- Create a structured analysis report.

### 2. DevOps Issue Investigator

Role: research the identified problem using external search.

Responsibilities:

- Search the internet for related error messages.
- Gather official docs, forum posts, and known troubleshooting guidance.
- Rank likely causes and proven fixes.

### 3. DevOps Solution Specialist

Role: convert investigation findings into actionable remediation steps.

Responsibilities:

- Produce a step-by-step remediation plan.
- Include commands and verification steps.
- Recommend monitoring and prevention measures.

## Tools used by the agents

### File reader tool

The log analyzer uses CrewAI's `FileReadTool` to inspect the sample log file.

### EXA search tool

The investigation agent uses `EXASearchTool` to search the public web for similar issues and community guidance.

## Guardrails and quality checks

The project includes two simple guardrails in `tasks/tasks.py`:

- The log analysis task validates that at least one error was found.
- The solution task validates that the final answer includes concrete shell command blocks.

If a guardrail fails, CrewAI retries the task. This helps reduce vague or incomplete outputs.

## Output artifacts

After a run, the project writes reports to `task_outputs/`:

- `log_analysis.md`
- `investigation_report.md`
- `solution_plan.md`

These files capture the different stages of the multi-agent troubleshooting process.

## Setup

1. Use Python 3.13. The current dependency set is tested against Python 3.13.
2. Create a virtual environment:

   ```powershell
   py -3.13 -m venv .venv
   ```

3. Activate it in PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root and add the required API keys:

   ```env
   EXA_API_KEY=your_exa_api_key
   ```

   Add any LLM provider keys required by the model configuration in `agents/agents.py`.

## Model configuration

The active LLM configuration is defined in `agents/agents.py`.

The file currently reads `OPENROUTER_MODEL` into `selected_model`, but the agent LLM instances are configured directly in code. If you want runtime model switching, update the `LLM(...)` definitions to use environment variables for the model name and API key.

Security note: keep API keys in `.env` and avoid committing real credentials to source control.

## Run

From the project root:

```powershell
python main.py
```

The demo uses the sample input file:

```text
kubernetes_log.log
```

When the run finishes, review the generated files in `task_outputs/`.

## Notes

- The `.env` file is required because the agents and tools load environment variables at startup.
- `EXA_API_KEY` is required for online investigation.
- The configured LLM provider key must have enough quota for the agent requests to succeed.
- The current system is intentionally simple and easy to extend with more agents, more tools, or more structured output formats.
