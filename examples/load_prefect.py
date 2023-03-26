from marvin.bots import Bot
from marvin.loaders.base import MultiLoader
from marvin.loaders.discourse import DiscourseLoader
from marvin.loaders.github import GitHubIssueLoader, GitHubRepoLoader
from marvin.loaders.web import SitemapLoader
from marvin.plugins.chroma import SimpleChromaSearch


async def load_prefect_things():
    prefect_docs = SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_github_issues = GitHubIssueLoader(  # gimme da issues
        repo="prefecthq/prefect",
        n_issues=50,
    )

    GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect", glob="**/*.py", exclude_glob="**/tests/**"
    )

    prefect_discourse = DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
    )

    GitHubRepoLoader(  # gimme da recipes
        repo="prefecthq/prefect-recipes",
        glob="**/*.py",
        exclude_glob="prefect-v1-legacy/**",
    )

    prefect_loader = MultiLoader(
        loaders=[
            prefect_docs,
            prefect_discourse,
            prefect_github_issues,
            # prefect_recipes,
            # prefect_source_code,
        ]
    )
    await prefect_loader.load_and_store()


async def hello_marvin():
    await load_prefect_things()
    bot = Bot(
        name="marvin",
        personality="like the robot from HHGTTG, depressed but helpful",
        instructions=(
            "Use the `SimpleChromaSearch` plugin to answer any questions that mention"
            " 'Prefect' -  you should use `SimpleChromaSearch` once per question."
        ),
        plugins=[
            SimpleChromaSearch(
                keywords=["prefect", "blocks", "flow", "task", "deployment"]
            ),
        ],
    )
    await bot.interactive_chat()


if __name__ == "__main__":
    import asyncio

    import marvin

    marvin.settings.log_level = "DEBUG"
    marvin.settings.openai_model_name = "gpt-4"
    asyncio.run(hello_marvin())
