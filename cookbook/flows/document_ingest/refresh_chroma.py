from datetime import timedelta
from functools import partial
from typing import Literal
from unittest.mock import patch

from marvin._rag.documents import Document
from marvin._rag.loaders.base import Loader
from marvin._rag.loaders.github import GitHubRepoLoader
from marvin._rag.loaders.web import SitemapLoader
from marvin._rag.utils import html_to_content
from marvin._rag.vectorstores.chroma import Chroma
from prefect import flow, task
from prefect.tasks import task_input_hash
from prefect.utilities.annotations import quote


def html_parser(html: str) -> str:
    import trafilatura

    trafilatura_config = trafilatura.settings.use_config()
    # disable signal, so it can run in a worker thread
    # https://github.com/adbar/trafilatura/issues/202
    trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
    return trafilatura.extract(html, config=trafilatura_config)


prefect_loaders = [
    SitemapLoader(
        urls=["https://docs.prefect.io/sitemap.xml", "https://prefect.io/sitemap.xml"],
        exclude=["api-ref", "/events/"],
    ),
    GitHubRepoLoader(
        repo="prefecthq/prefect",
        include_globs=[
            "flows/**",
            "tests/*.py",
            "README.md",
            "RELEASE-NOTES.md",
            "src/prefect/*.py",
        ],
        exclude_globs=[
            "**/__init__.py",
            "**/_version.py",
        ],
    ),
    GitHubRepoLoader(
        repo="prefecthq/prefect-recipes",
        include_globs=[
            "flows-advanced/**/*.py",
            "README.md",
            "flows-starter/*.py",
        ],
    ),
]


@task(
    retries=2,
    retry_delay_seconds=[3, 60],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
    task_run_name="Run {loader.__class__.__name__}",
    persist_result=True,
    refresh_cache=True,
)
async def run_loader(loader: Loader) -> list[Document]:
    return await loader.load()


@flow(name="Update Marvin's Knowledge", log_prints=True)
async def update_marvin_knowledge(
    collection_name: str = "marvin",
    chroma_client_type: str = "base",
    mode: Literal["upsert", "reset"] = "upsert",
):
    """Flow updating Marvin's knowledge with info from the Prefect community."""
    with patch(
        "marvin._rag.loaders.web.html_to_content",
        partial(html_to_content, parsing_fn=html_parser),
    ):
        documents = [
            doc
            for future in await run_loader.map(quote(prefect_loaders))
            for doc in await future.result()
        ]

        print(f"Loaded {len(documents)} documents from the Prefect community.")

    async with Chroma(
        collection_name=collection_name, client_type=chroma_client_type
    ) as chroma:
        if mode == "reset":
            await chroma.reset_collection()
            docs = await chroma.add(documents)
        elif mode == "upsert":
            docs = await chroma.upsert(documents)
        else:
            raise ValueError(f"Unknown mode: {mode!r} (expected 'upsert' or 'reset')")

        print(f"Added {len(docs)} documents to the {collection_name} collection.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        update_marvin_knowledge(collection_name="marvin", chroma_client_type="base")
    )
