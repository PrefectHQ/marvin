async def load_release_notes():
    """Load release notes from Prefect's GitHub repo."""
    from marvin.loaders.github import GitHubRepoLoader

    loader = GitHubRepoLoader(
        repo="prefecthq/prefect",
        glob="*.md",
    )
    return (await loader.load())[0]


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(load_release_notes())

    print(result)
