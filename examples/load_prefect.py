import marvin
from marvin.bots import Bot
from marvin.loaders.github import GitHubRepoLoader
from marvin.plugins.chroma import ChromaSearch


async def load_prefect_docs():
    await GitHubRepoLoader(
        repo="prefecthq/prefect", glob="**/*.md", exclude_glob="**/docs/api-ref/**"
    ).load_and_store(topic_name="marvin")


async def hello_marvin():
    await load_prefect_docs()
    bot = Bot(
        name="marvin",
        personality="like the robot from HHGTTG, depressed but helpful",
        plugins=[ChromaSearch()],
    )
    await bot.say(
        "What are the steps to create a new Prefect deployment?"
        " I'm trying to deploy Prefect on a Kubernetes cluster."
        " I'm getting an error about s3fs."
    )
    try:
        while True:
            user_input = input(">>> ")
            if user_input.strip() == "exit":
                raise KeyboardInterrupt
            await bot.say(user_input)
    except KeyboardInterrupt:
        print("👋")


if __name__ == "__main__":
    marvin.settings.log_level = "DEBUG"

    import asyncio

    asyncio.run(hello_marvin())
