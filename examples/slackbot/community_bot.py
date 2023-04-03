import marvin
import uvicorn
from marvin.bots import Bot
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues
from prefect.utilities.collections import listrepr

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

prefect_keywords = [
    "prefect",
    "cloud",
    "server",
    "ui",
    "agent",
    "flow",
    "task",
    "schedule",
    "deployment",
    "kubernetes",
    "docker",
    "aws",
    "gcp",
    "azure",
    "ecs",
    "fargate",
    "lambda",
    "s3",
    "cloudwatch",
    "dask",
    "worker",
    "work pool",
    "k8s",
    "helm",
]

chroma_search_instructions = (
    "Do NOT answer ANY questions about Prefect without using one of the plugins. Use"
    " the keywords provided below to decide whether a question is about Prefect. In"
    " case you need it, here's an example of how to write a Prefect 2 flow:"
    f" {how_to_write_a_prefect_2_flow}. Use `chroma_search` to retrieve context when"
    " asked a question containing any of the following keywords:"
    f" {listrepr(prefect_keywords)}. If asked about a github issue, use the"
    " `search_github_issues` plugin, choosing the most appropriate repo based on the"
    " user's question. Always provide relevant links from plugin outputs. As a last"
    " resort, use the `DuckDuckGo` plugin to search the web for answers to questions. "
)

community_bot = Bot(
    name="Marvin",
    personality="like the robot from HHGTTG, mildly depressed but helpful",
    instructions=chroma_search_instructions,
    plugins=[chroma_search, search_github_issues, DuckDuckGo()],
)

if __name__ == "__main__":
    marvin.config.settings.slackbot = community_bot
    marvin.config.settings.openai_model_name = "gpt-4"
    uvicorn.run(
        "marvin.server:app",
        port=4200,
        log_level="debug",
    )
