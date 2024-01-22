import asyncio
from datetime import datetime, timedelta

import cloudpickle
from marvin._rag.documents import Document
from marvin._rag.loaders.base import Loader
from marvin._rag.loaders.github import GitHubRepoLoader
from marvin._rag.loaders.web import SitemapLoader
from marvin._rag.utils import patch_html_parser
from marvin._rag.vectorstores.tpuf import TurboPuffer
from prefect import flow, task, unmapped
from prefect.tasks import task_input_hash
from prefect.utilities.annotations import quote
from prefect_gcp import GcsBucket


def html_parser(html: str) -> str:
    import trafilatura

    trafilatura_config = trafilatura.settings.use_config()
    # disable signal, so it can run in a worker thread
    # https://github.com/adbar/trafilatura/issues/202
    trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
    return trafilatura.extract(html, favor_precision=True, config=trafilatura_config)


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


@task
async def write_documents_to_gcs(
    bucket: GcsBucket, path: str, documents: list[Document]
):
    await asyncio.gather(
        *[
            bucket.write_path(
                path=f"{path}/{document.id}.pkl",
                content=cloudpickle.dumps(document),
            )
            for document in documents
        ]
    )


@flow(name="Save Documents to GCS", log_prints=True)
async def save_documents(
    bucket: GcsBucket, path: str, documents: list[Document], chunk_size: int = 10
):
    await write_documents_to_gcs.map(
        bucket=unmapped(bucket),
        path=path,
        documents=[
            documents[i : i + chunk_size] for i in range(0, len(documents), chunk_size)
        ],
    )


@flow(name="Update Marvin's Knowledge", log_prints=True)
async def update_marvin_knowledge_in_tpuf(
    namespace: str = "marvin", test_mode: bool = False
):
    """Flow updating Marvin's knowledge with info from the Prefect community."""

    if test_mode:
        print(
            f"Running in test mode - only loading data from {prefect_loaders[-1].__class__.__name__!r}"
        )

    with patch_html_parser(html_parser=html_parser):
        document_sources = prefect_loaders if not test_mode else prefect_loaders[-1:]
        documents = [
            doc
            for future in await run_loader.map(quote(document_sources))
            for doc in await future.result()
        ]

    print(f"Loaded {len(documents)} documents from the Prefect community.")

    bucket: GcsBucket = await GcsBucket.load("marvin-tpuf-document-storage")

    async with TurboPuffer() as tpuf:
        await task(tpuf.upsert)(documents=documents)

        n_doc = len(documents)

        print(f"Upserted {n_doc} documents to TurboPuffer.")

        base_path = f"{namespace}/serialized"
        path = (
            f"{base_path}/{datetime.now().strftime('%Y-%m-%d')}"
            if not test_mode
            else f"{base_path}/test"
        )

        await save_documents(bucket, path, documents=documents)

        print(f"Saved {n_doc} documents to GCS @ {path!r}")

        if test_mode:
            vector_result = await tpuf.query(text="pokemon", top_k=1)
            doc_id = vector_result.data[0].id
            document: Document = cloudpickle.loads(
                await bucket.read_path(f"{path}/{doc_id}.pkl")
            )
            print(document.text)


if __name__ == "__main__":
    asyncio.run(update_marvin_knowledge_in_tpuf(test_mode=True))
