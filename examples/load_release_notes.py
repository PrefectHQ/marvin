async def load_release_notes():
    """Load release notes from Prefect's GitHub repo."""
    from marvin.loaders.github import GitHubRepoLoader

    loader = GitHubRepoLoader(
        repo="prefecthq/prefect",
        glob="*.md",
    )
    return (await loader.load())[0]


async def create_excerpts():
    from marvin.utilities.loaders import create_excerpts_from_split_text

    release_notes = await load_release_notes()
    return await create_excerpts_from_split_text(release_notes)


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(create_excerpts())

    print(result)
