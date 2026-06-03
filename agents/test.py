from crewai import Agent, Task, Crew, LLM

llm = LLM(
    model="ollama/qwen3:8b",
    base_url="http://localhost:11434"
)

agent = Agent(
    role="Assistant",
    goal="Answer questions",
    llm=llm,
    verbose=True
)

task = Task(
    description="What is Python?",
    expected_output="One paragraph"
)

crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

result = crew.kickoff()
print(result)