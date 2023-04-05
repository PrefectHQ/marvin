import asyncio

import marvin
import uvicorn
from marvin.bots import Bot
from marvin.loaders.base import MultiLoader
from marvin.loaders.github import GitHubRepoLoader
from marvin.loaders.web import SitemapLoader
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues
from prefect.utilities.collections import listrepr


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    # prefect_source_code = GitHubRepoLoader(  # gimme da source
    #     repo="prefecthq/prefect",
    #     include_globs=["**/*.py"],
    #     exclude_globs=[
    #         "tests/**/*",
    #         "docs/**/*",
    #         "**/migrations/**/*",
    #         "**/__init__.py",
    #     ],
    # )

    # prefect_discourse = DiscourseLoader(  # gimme da discourse
    #     url="https://discourse.prefect.io",
    #     include_topic_filter=lambda topic: "marvin" in topic["tags"],
    #     include_post_filter=lambda post: post["accepted_answer"],
    # )

    prefect_recipes = GitHubRepoLoader(  # gimme da recipes (or at least some of them)
        repo="prefecthq/prefect-recipes",
        include_globs=["flows-advanced/**/*.py"],
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            # prefect_discourse,
            prefect_recipes,
        ]
    )

    await prefect_loader.load_and_store()


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
    "core",
    "cloud",
    "workspace",
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
    "Your job is to be a helpful slackbot for the Prefect community. Answering"
    " questions about Prefect requires using one of your plugins. Do not refer to your"
    " use of plugins in your answer. Utilize `chroma_search` to obtain context when"
    " encountering a question with any of the following Prefect keywords:"
    f" {listrepr(prefect_keywords)}. For questions about GitHub issues, employ the"
    " `search_github_issues` Always return relevant links from plugin outputs to the"
    " user. If asked about current events (or if all else fails) Use the DuckDuckGo"
    " plugin to search the web for answers. For reference, here's how to write a"
    f" Prefect flow: {how_to_write_a_prefect_2_flow}."
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

    asyncio.run(load_prefect_things())

    uvicorn.run("marvin.server:app", host="0.0.0.0", port=4200)
