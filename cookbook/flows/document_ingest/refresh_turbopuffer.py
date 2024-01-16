from datetime import timedelta
from functools import partial
from unittest.mock import patch

import marvin
import turbopuffer as tpuf
from marvin._rag.documents import Document
from marvin._rag.loaders.base import Loader
from marvin._rag.loaders.github import GitHubRepoLoader
from marvin._rag.loaders.web import SitemapLoader
from marvin._rag.utils import create_openai_embeddings, html_to_content
from prefect import flow, task
from prefect.tasks import task_input_hash
from prefect.utilities.annotations import quote

tpuf.api_key = marvin.settings.turbopuffer_api_key


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
    # refresh_cache=True,
)
async def run_loader(loader: Loader) -> list[Document]:
    return await loader.load()


@flow(name="Update Marvin's Knowledge", log_prints=True)
async def update_marvin_knowledge_in_tpuf(namespace: str = "marvin"):
    """Flow updating Marvin's knowledge with info from the Prefect community."""

    ns = tpuf.Namespace(namespace)

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

        embeddable_documents = []
        for document in documents:
            try:
                document.embedding = await task(create_openai_embeddings)(document.text)
                embeddable_documents.append(document)
            except Exception as e:
                print(
                    f"Failed to create embedding for {document.id}: {document.text[:100]}..: {e}"
                )
        await task(ns.upsert)(
            ids=[document.id for document in embeddable_documents],
            vectors=[document.embedding for document in embeddable_documents],
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_marvin_knowledge_in_tpuf())
