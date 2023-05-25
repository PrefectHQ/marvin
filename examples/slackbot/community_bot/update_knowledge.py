import tempfile
from pathlib import Path

import marvin
from chromadb.config import Settings as ChromaSettings
from google.cloud import storage
from langchain.document_loaders.pdf import PyMuPDFLoader
from marvin.loaders import (
    base,
    discourse,
    github,
    langchain_documents,
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


async def download_pdfs(file_path: Path):
    BUCKET_NAME = "marvin-internal-documents"

    client = storage.Client()

    bucket = client.get_bucket(BUCKET_NAME)

    blobs = client.list_blobs(bucket)

    async def download_blob(blob):
        destination_path = file_path / blob.name
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(destination_path))

    download_tasks = [
        download_blob(blob) for blob in blobs if blob.name.endswith(".pdf")
    ]
    await asyncio.gather(*download_tasks)


def include_topic_filter(topic):
    return (
        "marvin" in topic["tags"]
        and topic["category_id"] in PREFECT_COMMUNITY_CATEGORIES
    )


async def generate_policy_document_loaders(
    glob="*.pdf",
) -> list[langchain_documents.LangChainLoader]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        await download_pdfs(temp_path)

        policy_document_loaders = [
            langchain_documents.LangChainLoader(
                documents=PyMuPDFLoader(file_path=str(pdf_file)).load(),
            )
            for pdf_file in temp_path.glob(glob)
        ]

    return policy_document_loaders


async def get_prefect_loader():
    prefect_docs = web.SitemapLoader(  # gimme da docs
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    )

    prefect_api_docs = openapi.OpenAPISpecLoader(  # gimme da api docs
        openapi_spec_url="https://api.prefect.cloud/api/openapi.json",
        api_doc_url="https://app.prefect.cloud/api",
    )

    policy_document_loaders = await generate_policy_document_loaders()

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
        n_topic=500,
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
            *policy_document_loaders,
        ]
    )


@flow(name="Update Marvin's Knowledge")
async def update_marvin_knowledge(topic_name: str | None = None):
    """A flow that updates Marvin's knowledgebase with information from the Prefect community.

    the `json/chroma-client-settings` Block should look like this:
    {
        "chroma_db_impl": "clickhouse",
        "chroma_api_impl": "rest",
        "chroma_server_host": "<chroma-server-host>",
        "chroma_server_http_port": 8000
    }
    """  # noqa: E501
    marvin.settings.log_level = "DEBUG"

    # comment out the next 2 lines if you want to use in-memory DuckDB (default)
    chroma_client_settings = await JSON.load("chroma-client-settings")
    marvin.settings.chroma = ChromaSettings(**chroma_client_settings.value)

    prefect_loader = await get_prefect_loader()

    await prefect_loader.load_and_store(topic_name=topic_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_marvin_knowledge())
