import asyncio
import re
from typing import Optional, Union
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from httpx import AsyncClient, Response
from pydantic import Field

from marvin._rag.documents import Document, document_to_excerpts
from marvin._rag.loaders.base import Loader, MultiLoader
from marvin._rag.utils import batched, html_to_content

user_agent = UserAgent()

URL_CONCURRENCY = asyncio.Semaphore(30)


def ensure_http(url):
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url


async def sitemap_search(sitemap_url) -> list[str]:
    async with AsyncClient() as client:
        response = await client.get(sitemap_url, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.content, "xml")

    return [loc.text for loc in soup.find_all("loc")]


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

    urls: list[str] = Field(default_factory=list)

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
                final_documents.extend(await document_to_excerpts(d))
        return final_documents

    async def load_url(self, url, client) -> Optional[Document]:
        async with URL_CONCURRENCY:
            response = await client.get(url, follow_redirects=True)

        if not response.status_code == 200:
            self.logger.warning_style(
                f"Received status {response.status_code} from {url}", "red"
            )
            return

        # check for a meta refresh redirect in the response content
        soup = BeautifulSoup(response.text, "html.parser")
        meta_refresh = soup.find(
            "meta", attrs={"http-equiv": re.compile(r"refresh", re.I)}
        )
        if meta_refresh:
            refresh_content = meta_refresh.get("content")
            redirect_url_match = re.search(r"url=([\S]+)", refresh_content, re.I)
            if redirect_url_match:
                redirect_url = redirect_url_match.group(1)
                # join base url with relative url
                redirect_url = urljoin(str(response.url), redirect_url)
                # Now ensure the URL includes the protocol
                redirect_url = ensure_http(redirect_url)
                response = await client.get(redirect_url, follow_redirects=True)

        document = await self.response_to_document(response)
        if document:
            self.logger.info(f"Loaded document from {url}")
        else:
            self.logger.warning_style(f"Could not load document from {url}", "red")
        return document

    async def response_to_document(self, response: Response) -> Document:
        return Document(
            text=await self.get_document_text(response),
            metadata=dict(
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
    include: list[Union[str, re.Pattern]] = Field(default_factory=list)
    exclude: list[Union[str, re.Pattern]] = Field(default_factory=list)
    url_loader: URLLoader = Field(default_factory=HTMLLoader)

    async def _get_loader(self) -> Loader:
        urls = await asyncio.gather(*[self.load_sitemap(url) for url in self.urls])
        urls = [u for url_list in urls for u in url_list]
        return MultiLoader(
            loaders=[
                type(self.url_loader)(urls=url_batch, headers=await self.get_headers())
                for url_batch in batched(urls, 10)
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
            for url in await sitemap_search(url)
            if is_included(url) and not is_excluded(url)
        ]
