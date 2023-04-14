import json

import httpx
from fastapi import status

from marvin.loaders.web import SitemapLoader, URLLoader
from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens
from marvin.utilities.web import url_is_ok


class VisitURL(Plugin):
    name: str = "visit-url"
    description: str = (
        "Visit a URL and return its contents. Don't provide a URL unless you're"
        " absolutely sure it exists."
    )

    async def run(self, url: str) -> str:
        if not url.startswith("http"):
            url = f"http://{url}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=2) as client:
            try:
                response = await client.get(url)
            except httpx.ConnectTimeout:
                return "Failed to load URL: Connection timed out"
        if response.status_code == status.HTTP_200_OK:
            text = response.text

            # try to parse as JSON in case the URL is an API
            try:
                content = str(json.loads(text))
            # otherwise parse as HTML
            except json.JSONDecodeError:
                content = html_to_content(text)
            return slice_tokens(content, 1000)
        else:
            return f"Failed to load URL: {response.status_code}"


class LoadAndStoreURL(Plugin):
    name: str = "load-and-store-url"
    description: str = (
        "Visit a URL and use a loader to load its contents. Don't provide a URL unless"
        " you're absolutely sure it exists. A topic name can be provided to store the"
        " documents in a particular topic."
    )

    async def run(self, url: str, topic_name: str = None) -> str:
        """
        Load and store the contents of a URL into a topic. If no topic name is provided,
        the Marvin default topic will be used.
        """
        if not url.startswith("http"):
            url = f"http://{url}"

        if url.endswith(".pdf"):
            return f"URL {url} is a PDF. Use the `load-and-store-pdf` plugin instead."
        if url.endswith(".xml"):
            return (
                f"URL {url} is a sitemap. Use the `load-and-store-sitemap` plugin"
                " instead."
            )

        if not await url_is_ok(url):
            return (
                "URL was not reachable - make sure it exists and is publicly accessible"
            )

        loader = URLLoader(urls=[url])
        await loader.load_and_store(topic_name=topic_name)
        return f"Loaded {url} into topic {topic_name!r}"


class LoadAndStorePDF(Plugin):
    name: str = "load-and-store-pdf"
    description: str = (
        "Load and store the contents of a PDF URL into a topic. if no topic name is"
        " provided, the Marvin default topic will be used."
    )

    async def run(self, pdf_url: str, topic_name: str = None) -> str:
        from marvin.loaders.pdf import PDFLoader

        loader = PDFLoader(file_path=pdf_url)
        await loader.load_and_store(topic_name=topic_name)
        return f"Loaded {pdf_url} into topic {topic_name!r}"


class LoadAndStoreSitemap(Plugin):
    name: str = "load-and-store-sitemap"
    description: str = (
        "Load and store the contents of a sitemap URL into a topic. if no topic name is"
        " provided, the Marvin default topic will be used."
    )

    async def run(self, sitemap_url: str, topic_name: str = None) -> str:
        loader = SitemapLoader(urls=[sitemap_url])
        await loader.load_and_store(topic_name=topic_name)
        return f"Loaded {sitemap_url} into topic {topic_name!r}"
