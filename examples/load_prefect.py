import pendulum
from marvin.bots import Bot
from marvin.loaders.base import MultiLoader
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubIssueLoader, GitHubRepoLoader
from marvin.loaders.web import SitemapLoader
from marvin.plugins.chroma import ChromaSearch
from marvin.plugins.duckduckgo import DuckDuckGo
from prefect.utilities.collections import listrepr


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_github_issues = GitHubIssueLoader(  # gimme da issues
        repo="prefecthq/prefect",
        n_issues=50,
    )

    prefect_source_code = GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect", glob="**/*.py", exclude_glob="**/tests/**"
    )

    prefect_discourse = DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
    )

    prefect_recipes = GitHubRepoLoader(  # gimme da recipes
        repo="prefecthq/prefect-recipes",
        glob="**/*.py",
        exclude_glob="prefect-v1-legacy/**",
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            prefect_github_issues,
            prefect_source_code,
            prefect_discourse,
            prefect_recipes,
        ]
    )
    await prefect_loader.load_and_store()
    return set(loader.source for loader in prefect_loader.loaders)


async def hello_marvin():
    sources = await load_prefect_things()
    bot = Bot(
        name="marvin",
        personality="like the robot from HHGTTG, depressed but helpful",
        instructions=(
            "Unless making a conversational response, use the `ChromaSearch` plugin to"
            " answer questions. Provide relevant links based on any plugin output."
            " You should NEVER attempt to write your own code to answer a question."
            f" For future reference, the time now is {pendulum.now().isoformat()}."
        ),
        plugins=[
            ChromaSearch(
                description=(
                    "Semantic search of Prefect documentation, GitHub issues, and"
                    " related material. To use, provide a detailed, natural language"
                    " `query`. If useful, also provide a `where` clause as a `dict`"
                    " that has a `source`  key that MUST point to one of the following"
                    f" values: {listrepr(sources)}. If the user asks about information"
                    " since a certain date, provide a `created_at` key to the `where`"
                    " dict with a dict that has an operator key `$gte` and a value"
                    " key. The value for that key MUST be a valid ISO 8601 timestamp."
                )
            ),
            DuckDuckGo(),
        ],
    )
    await bot.interactive_chat()


if __name__ == "__main__":
    import asyncio

    import marvin

    marvin.settings.log_level = "DEBUG"
    asyncio.run(hello_marvin())
