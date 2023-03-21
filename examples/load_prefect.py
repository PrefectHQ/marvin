from marvin.bots import Bot
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubIssueLoader, GitHubRepoLoader
from marvin.plugins.chroma import ChromaSearch


async def load_prefect_things():
    await GitHubRepoLoader(  # gimme da docs
        repo="prefecthq/prefect", glob="**/*.md", exclude_glob="**/docs/api-ref/**"
    ).load_and_store()

    await GitHubIssueLoader(  # gimme da issues
        repo="prefecthq/prefect",
        n_issues=50,
    ).load_and_store()

    await GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect", glob="**/*.py", exclude_glob="**/tests/**"
    ).load_and_store()

    await DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
    ).load_and_store()


async def hello_marvin():
    await load_prefect_things()
    bot = Bot(
        name="marvin",
        personality="like the robot from HHGTTG, depressed but helpful",
        instructions=(
            "Unless making a conversational response, use the ChromaSearch plugin to"
            " answer questions."
        ),
        plugins=[
            ChromaSearch(
                description=(
                    "Semantic search of Prefect documentation, GitHub issues, and"
                    " related material. Useful for learning or supporting Prefect,"
                    " workflows, flows, tasks, infrastructure, and more. Provide"
                    " detailed, natural language queries."
                )
            )
        ],
    )
    await bot.interactive_chat()


if __name__ == "__main__":
    import asyncio

    asyncio.run(hello_marvin())
