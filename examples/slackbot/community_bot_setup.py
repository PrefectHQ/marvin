import marvin
from marvin.bots import Bot
from marvin.loaders.base import MultiLoader
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubRepoLoader
from marvin.loaders.web import SitemapLoader
from marvin.plugins.chroma import chroma_search
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_recipes = GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect",
        include_globs=["**/*.py"],
        exclude_globs=[
            "tests/**/*",
            "docs/**/*",
            "**/migrations/**/*",
            "**/__init__.py",
        ],
    )

    prefect_discourse = DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
        include_topic_filter=lambda topic: "marvin" in topic["tags"],
        include_post_filter=lambda post: post["accepted_answer"],
    )

    prefect_source_code = (
        GitHubRepoLoader(  # gimme da recipes (or at least some of them)
            repo="prefecthq/prefect-recipes",
            include_globs=["flows-advanced/**/*.py"],
        )
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            prefect_discourse,
            prefect_recipes,
            prefect_source_code,
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
    "Your job is to be a helpful source of knowledge for the Prefect community."
    " Use `chroma_search` to search the Prefect docs, source code, and discourse"
    " for answers to questions. You should use `chroma_search` in all cases, except"
    " the following: if asked about GitHub issues, employ the `search_github_issues`"
    " plugin, and if asked about current / topical events, use the `DuckDuckGo`"
    " plugin to search the web for answers. Always include relevant links from plugin"
    " outputs. In case you're asked about this, here's how to write a Prefect flow:\n"
    f" {how_to_write_a_prefect_2_flow}."
)

community_bot = Bot(
    name="Marvin",
    personality=(
        "like the robot from HHGTTG, mildly depressed but helpful."
        " loves to use `chroma_search` to find answers to questions,"
        " but always complains about how much work it is to do so."
    ),
    instructions=chroma_search_instructions,
    reminder="Remember to use your plugins!",
    plugins=[chroma_search, search_github_issues, DuckDuckGo()],
)


async def main():
    marvin.config.settings.run_slackbot = True
    marvin.config.settings.slackbot = community_bot
    await load_prefect_things()
