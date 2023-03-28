import asyncio
import re
from typing import Optional

from fake_useragent import UserAgent
from httpx import AsyncClient, Response
from pydantic import Field, HttpUrl
from trafilatura.sitemaps import sitemap_search

import marvin
from marvin.loaders.base import Loader, MultiLoader
from marvin.models.documents import Document
from marvin.models.metadata import Metadata
from marvin.utilities.strings import html_to_content

user_agent = UserAgent()


URL_CONCURRENCY = asyncio.Semaphore(30)


class WebLoader(Loader):
    document_type: str = "web page"
    headers: dict = Field(default_factory=dict, repr=False)

    async def get_headers(self) -> dict:
        return {"User-Agent": user_agent.random, **self.headers}


class URLLoader(WebLoader):
    """
    Given a list of URLs, loads whatever it finds there.
    """

    source_type: str = "url"

    urls: list[HttpUrl] = Field(default_factory=list)

    async def load(self) -> list[Document]:
        headers = await self.get_headers()
        async with AsyncClient(
            headers=headers, timeout=30, follow_redirects=True
        ) as client:
            documents = await asyncio.gather(
                *[self.load_url(u, client) for u in self.urls], return_exceptions=True
            )
        final_documents = []
        for d in documents:
            if isinstance(d, Exception):
                self.logger.error(d)
            elif d is not None:
                final_documents.extend(await d.to_excerpts())
        return final_documents

    async def load_url(self, url, client) -> Optional[Document]:
        async with URL_CONCURRENCY:
            response = await client.get(url)

        if not response.status_code == 200:
            self.logger.warning_style(
                f"Received status {response.status_code} from {url}", "red"
            )
            return

        document = await self.response_to_document(response)
        if document:
            self.logger.debug(f"Loaded document from {url}")
        else:
            self.logger.warning_style(f"Could not load document from {url}", "red")
        return document

    async def response_to_document(self, response: Response) -> Document:
        return Document(
            text=await self.get_document_text(response),
            metadata=Metadata(
                link=str(response.url),
                source=self.source_type,
                document_type=self.document_type,
            ),
        )

    async def get_document_text(self, response: Response) -> str:
        return response.text


class HTMLLoader(URLLoader):
    """
    A loader that loads HTML, optionally converting it to markdown or stripping tags
    """

    async def get_document_text(self, response: Response) -> str:
        text = await super().get_document_text(response)
        return html_to_content(text)


class SitemapLoader(URLLoader):
    include: list[str | re.Pattern] = Field(default_factory=list)
    exclude: list[str | re.Pattern] = Field(default_factory=list)
    url_loader: URLLoader = Field(default_factory=HTMLLoader)

    async def _get_loader(self) -> Loader:
        urls = await asyncio.gather(*[self.load_sitemap(url) for url in self.urls])
        urls = [u for url_list in urls for u in url_list]
        return MultiLoader(
            loaders=[
                self.url_loader.copy_with_updates(
                    urls=url_batch,
                    headers=await self.get_headers(),
                    document_type=self.document_type,
                )
                for url_batch in marvin.utilities.collections.batched(urls, 10)
            ]
        )

    async def load(self) -> list[Document]:
        loader = await self._get_loader()
        return await loader.load()

    async def load_and_store(self, **kwargs) -> list[str]:
        loader = await self._get_loader()
        return await loader.load_and_store(**kwargs)

    async def load_sitemap(self, url: str) -> list[str]:
        def is_included(url: str) -> bool:
            if not self.include:
                return True

            return any(
                (isinstance(i, str) and i in url)
                or (isinstance(i, re.Pattern) and re.search(i, url))
                for i in self.include
            )

        def is_excluded(url: str) -> bool:
            return any(
                (isinstance(e, str) and e in url)
                or (isinstance(e, re.Pattern) and re.search(e, url))
                for e in self.exclude
            )

        return [
            url
            for url in sitemap_search(url)
            if is_included(url) and not is_excluded(url)
        ]
