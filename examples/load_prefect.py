import marvin
from marvin.bots import Bot
from marvin.loaders.github import GitHubRepoLoader
from marvin.plugins.chroma import ChromaVectorstore


async def load_prefect_docs():
    await GitHubRepoLoader(
        repo="prefecthq/prefect", glob="**/*.md", exclude_glob="**/docs/api-ref/**"
    ).load_and_store(topic_name="prefect")


async def hello_marvin():
    await load_prefect_docs()
    bot = Bot(
        name="marvin", personality="depressed", extend_plugins=[ChromaVectorstore()]
    )
    await bot.say("What are the steps to create a new Prefect deployment?")


if __name__ == "__main__":
    marvin.settings.log_level = "DEBUG"

    import asyncio

    asyncio.run(hello_marvin())
