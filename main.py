import os
from pathlib import Path

from crewai import Crew, Process

from agents.agents import issue_investigator, log_analyzer, solution_specialist
from tasks.tasks import analyze_logs_task, investigate_issue_task, provide_solution_task

REPO_ROOT = Path(__file__).resolve().parent
os.chdir(REPO_ROOT)
LOG_FILE_PATH = Path("kubernetes_log.log")

devops_crew = Crew(
    agents=[log_analyzer, issue_investigator, solution_specialist],
    tasks=[analyze_logs_task, investigate_issue_task, provide_solution_task],
    verbose=True,
    process=Process.sequential,
)

if __name__ == "__main__":
    print("=" * 60)
    print("DevOps Issue Analysis through Log Analysis Agents")
    print("Features: Structured Output | Guardrails")
    print("=" * 60)

    print("\nScenario 1: Kubernetes Deployment Analysis")
    print("-" * 40)
    devops_crew.kickoff(inputs={"log_file_path": str(LOG_FILE_PATH)})

    print("\nAnalysis completed!")