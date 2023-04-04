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
    "blocks",
    "results",
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
    "Your job is to be a helpful slackbot for the Prefect community."
    " Answering questions about Prefect requires using one of the plugins. Rely on"
    " the provided keywords to determine if a question pertains to Prefect. Here's an"
    f" example of how to write a Prefect 2 flow: {how_to_write_a_prefect_2_flow}."
    " Utilize `chroma_search` to obtain context when encountering a question with any"
    f" of the following keywords: {listrepr(prefect_keywords)}. For questions about"
    " GitHub issues, employ the `search_github_issues` plugin, selecting the most"
    " suitable repository based on the user's inquiry. Always include relevant links"
    " from plugin outputs. If all else fails, resort to the DuckDuckGo plugin to"
    " search the web for answers."
)

community_bot = Bot(
    name="Marvin",
    personality="like the robot from HHGTTG, mildly depressed but helpful",
    instructions=chroma_search_instructions,
    plugins=[chroma_search, search_github_issues, DuckDuckGo()],
)

if __name__ == "__main__":
    marvin.config.settings.log_level = "DEBUG"
    marvin.config.settings.openai_model_name = "gpt-4"
    marvin.config.settings.openai_model_temperature = 0.1
    marvin.config.settings.slackbot = community_bot

    uvicorn.run("marvin.server:app", port=4200)
