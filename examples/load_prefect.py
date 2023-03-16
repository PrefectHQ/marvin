import marvin
from marvin.loaders.github import GitHubRepoLoader


async def load_prefect_docs():
    await GitHubRepoLoader(
        repo="prefecthq/prefect", glob="**/*.md", exclude_glob="**/docs/api-ref/**"
    ).load_and_store(topic_name="prefect")


if __name__ == "__main__":
    import asyncio

    marvin.settings.log_level = "DEBUG"
    asyncio.run(load_prefect_docs())
