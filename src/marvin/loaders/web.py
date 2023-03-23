import asyncio
import re
from typing import Literal, Optional

import html2text
import pendulum
import readability
from fake_useragent import UserAgent
from httpx import AsyncClient, Response
from markdownify import markdownify
from pydantic import Field, HttpUrl
from selectolax.parser import HTMLParser

import marvin
from marvin.loaders.base import Loader, MultiLoader
from marvin.models.documents import Document

user_agent = UserAgent()

MULTIPLE_NEWLINES = re.compile(r"\n{2,}")
MULTIPLE_WHITESPACE = re.compile(r"[\t ]+")

URL_CONCURRENCY = asyncio.Semaphore(30)


async def html_to_content(
    html: str,
    library: Literal["readability", "html2text"] = None,
):
    return await marvin.utilities.async_utils.run_async_process(
        _html_to_content, html=html, library=library
    )


def _html_to_content(
    html: str,
    library: Literal["readability", "html2text"] = None,
) -> str:
    library = library or "readability"

    if library == "readability":
        readability_doc = readability.Document(html)
        text = readability_doc.summary()
        text = markdownify(
            text, heading_style="ATX", escape_underscores=False, escape_asterisks=True
        )
    else:
        text = html2text.html2text(html)

    text = condense_newlines(text)
    return text


def condense_newlines(text: str) -> str:
    text = text.replace("\r", "\n")
    text = MULTIPLE_NEWLINES.sub("\n", text)
    return MULTIPLE_WHITESPACE.sub(" ", text)


def parse_html(html) -> HTMLParser:
    return HTMLParser(html)


class WebLoader(Loader):
    document_type: str = "web page"
    headers: dict = Field(default_factory=dict, repr=False)

    async def get_headers(self) -> dict:
        return {"User-Agent": user_agent.random, **self.headers}


class URLLoader(WebLoader):
    """
    Given a list of URLs, loads whatever it finds there.
    """

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

    async def response_to_document(self, response: Response) -> list[Document]:
        return Document(
            text=response.text,
            metadata={
                "link": str(response.url),
                "document_type": self.document_type,
                "source": self.source,
                "created_at": pendulum.now().timestamp(),
            },
        )


class HTMLLoader(URLLoader):
    """
    A loader that loads HTML, optionally converting it to markdown or stripping tags
    """

    library: Literal["readability", "html2text"] = "readability"

    async def get_document_text(self, response: Response) -> str:
        text = await super().get_document_text(response)
        return await html_to_content(text, library=self.library)

    async def get_document_kwargs(self, response: Response) -> dict:
        kwargs = await super().get_document_kwargs(response)
        readability_doc = readability.Document(response.text)
        kwargs["name"] = await marvin.utilities.async_utils.run_async_process(
            readability_doc.title
        )
        return kwargs


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

    async def load_sitemap(self, url) -> list[str]:
        headers = await self.get_headers()
        async with AsyncClient(headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = parse_html(response.text)
        url_locs = html.css("loc")
        urls = []
        for loc in url_locs:
            valid_url = True
            url = loc.text()

            # If we have an include list, make sure the url is in it
            if self.include:
                valid_url = False
                for i in self.include:
                    if isinstance(i, str) and i in url:
                        valid_url = True
                    elif isinstance(i, re.Pattern) and re.search(i, url):
                        valid_url = True

            # If we have an exclude list, make sure the url is not in it
            for e in self.exclude:
                if isinstance(e, str) and e in url:
                    valid_url = False
                elif isinstance(e, re.Pattern) and re.search(e, url):
                    valid_url = False

            if valid_url:
                urls.append(url)
        return urls
