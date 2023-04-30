import marvin
from marvin.loaders import (
    base,
    discourse,
    github,
    openapi,
    web,
)
from prefect import flow
from prefect.blocks.system import JSON

# Discourse categories
SHOW_AND_TELL_CATEGORY_ID = 26
HELP_CATEGORY_ID = 27

PREFECT_COMMUNITY_CATEGORIES = {
    SHOW_AND_TELL_CATEGORY_ID,
    HELP_CATEGORY_ID,
}


def include_topic_filter(topic):
    return (
        "marvin" in topic["tags"]
        and topic["category_id"] in PREFECT_COMMUNITY_CATEGORIES
    )


def get_prefect_loader():
    prefect_docs = web.SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_api_docs = openapi.OpenAPISpecLoader(  # gimme da api docs
        openapi_spec_url="https://api.prefect.cloud/api/openapi.json"
    )

    prefect_website = web.HTMLLoader(  # gimme da website
        urls=[
            "https://prefect.io/about/company/",
            "https://prefect.io/security/overview/",
            "https://prefect.io/security/sub-processors/",
            "https://prefect.io/security/gdpr-compliance/",
            "https://prefect.io/security/bug-bounty-program/",
        ],
    )

    prefect_source_code = github.GitHubRepoLoader(  # gimme da source
        repo="prefecthq/prefect",
        include_globs=["**/*.py"],
        exclude_globs=[
            "tests/**/*",
            "docs/**/*",
            "**/migrations/**/*",
            "**/__init__.py",
            "**/_version.py",
        ],
    )

    prefect_release_notes = github.GitHubRepoLoader(  # gimme da release notes
        repo="prefecthq/prefect",
        include_globs=["release-notes.md"],
    )

    prefect_discourse = discourse.DiscourseLoader(  # gimme da discourse
        url="https://discourse.prefect.io",
        n_topic=240,
        include_topic_filter=include_topic_filter,
    )

    prefect_recipes = (
        github.GitHubRepoLoader(  # gimme da recipes (or at least some of them)
            repo="prefecthq/prefect-recipes",
            include_globs=["flows-advanced/**/*.py"],
        )
    )
    return base.MultiLoader(
        loaders=[
            prefect_docs,
            prefect_api_docs,
            prefect_website,
            prefect_discourse,
            prefect_recipes,
            prefect_release_notes,
            prefect_source_code,
        ]
    )


@flow
async def update_marvin_knowledge(topic_name: str | None = None):
    prefect_loader = get_prefect_loader()

    chroma_client_settings = await JSON.load("internal-chroma-client-settings")

    updated_client_settings = {
        f"chroma.{key}": value for key, value in chroma_client_settings.value.items()
    }

    with marvin.config.temporary_settings(**updated_client_settings):
        await prefect_loader.load_and_store(topic_name=topic_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_marvin_knowledge())
