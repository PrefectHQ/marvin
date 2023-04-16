import marvin
from marvin.bot import Bot
from marvin.config import CHROMA_INSTALLED
from marvin.loaders.base import MultiLoader
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubRepoLoader
from marvin.loaders.web import SitemapLoader
from marvin.plugins.duckduckgo import DuckDuckGo
from marvin.plugins.github import search_github_issues

if not CHROMA_INSTALLED:
    marvin.get_logger().info_style(
        (
            "Chroma is not installed, so we don't have a vectorstore to load into."
            " Install with `pip install marvin[chromadb]` to store knowledge in"
            " ChromaDB."
        ),
        "yellow",
    )

    marvin.get_logger().info_style(
        "Now spinning up a bot with only github issue search and duckduckgo search",
        "blue",
    )

    input("Press Enter to continue...")


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_source_code = GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect",
        include_globs=["**/*.py"],
        exclude_globs=["tests/**/*", "docs/**/*", "**/migrations/**/*"],
    )

    prefect_discourse = DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
        include_topic_filter=lambda topic: "marvin" in topic["tags"],
        include_post_filter=lambda post: post["accepted_answer"],
    )

    prefect_recipes = GitHubRepoLoader(  # gimme da recipes (or at least some of them)
        repo="prefecthq/prefect-recipes",
        include_globs=["flows-advanced/**/*.py"],
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            prefect_discourse,
            prefect_recipes,
            prefect_source_code,
        ]
    )

    if CHROMA_INSTALLED:
        await prefect_loader.load_and_store()


prefect_keywords = [
    "prefect",
    "cloud",
    "server",
    "workspace",
    "ui",
    "agent",
    "flow",
    "task",
    "state",
    "result",
    "block",
    "schedule",
    "deployment",
    "kubernetes",
    "docker",
    "ecs",
    "worker",
    "work pool",
]


plugins = [search_github_issues, DuckDuckGo()]

# note that `chroma_search` requires the `chromadb` extra
if CHROMA_INSTALLED:
    from marvin.plugins.chroma import chroma_search

    plugins.append(chroma_search)


async def hello_marvin():
    await load_prefect_things()
    bot = Bot(
        name="marvin",
        personality="like the robot from HHGTTG, depressed but helpful",
        instructions=(
            "Use your plugins to help the user. Always provide relevant links from"
            " plugin outputs. If you don't know the answer, try to find it in the"
            " knowledgebase via `chroma_search`. Begin responses to the user with a"
            " short summary of their expressed intent."
        ),
        plugins=plugins,
    )
    bot.interactive_chat()

    print(await bot.history.log())


if __name__ == "__main__":
    import asyncio

    marvin.settings.log_level = "DEBUG"
    marvin.settings.openai_model_name = "gpt-4"
    asyncio.run(hello_marvin())
