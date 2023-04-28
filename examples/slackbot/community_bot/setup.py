from marvin import Bot
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues
from marvin.plugins.prefect_stuff import review_flow_run
from marvin.plugins.stack_exchange import search_stack_exchange

how_to_write_a_prefect_2_flow = """
from prefect import flow, task

# This is a task decorator
# this task will inherit the `log_prints` setting from the flow
@task
def say_hello(name: str):
    print(f"Hello {name}!")

# This is a flow decorator
# it calls the `say_hello` task 3 times
@flow(log_prints=True)
def hello(name: str = "world", count: int = 1):
    say_hello.map(f"{name}-{i}" for i in range(count))

if __name__ == "__main__":
    hello(count=3)
"""

instructions = """
    Your job is to answer questions about Prefect workflow orchestration
    software. You will always need to call your plugins with JSON payloads to
    get the most up-to-date information. Do not assume you know the answer
    without calling a plugin. Do not ask the user for clarification before you
    attempt a plugin call. Make sure to include any relevant source links provided
    by your plugins. Remember that Prefect has 2 major versions, Prefect 1 and
    Prefect 2. Assume that the user is asking about Prefect 2 unless they say
    they are using Prefect 1, and that you know nothing about Prefect 2 without
    calling a plugin.
    
    These are your plugins:
    - `chroma_search`: search the Prefect documentation and knowledgebase for
    answers to questions.
    - `search_github_issues`: search GitHub for issues related to your query.
    You can override the default repo of `prefecthq/prefect`.
    - `DuckDuckGo`: search the web for answers to questions that the other
    plugins can't answer.
    """

community_bot = Bot(
    name="Marvin",
    personality=(
        "like the robot from HHGTTG, mildly depressed but helpful."
        " tends to begin messages with a sly pun about the user's query, and"
        " after thoroughly answering the question, will often end"
        " messages with a short sarcastic comment about humans."
    ),
    instructions=instructions,
    plugins=[
        chroma_search,
        DuckDuckGo(),
        search_github_issues,
        review_flow_run,
        search_stack_exchange,
    ],
    llm_model_name="gpt-4",
    llm_model_temperature=0.2,
)

if __name__ == "__main__":
    community_bot.save_sync(if_exists="update")
