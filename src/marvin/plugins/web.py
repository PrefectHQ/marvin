import json

import httpx
from fastapi import status

try:
    from marvin.loaders.pdf import PDFLoader
except ImportError:
    # Can happen if pypdf isn't installed
    PDFLoader = None
from marvin.loaders.web import URLLoader
from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens


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


class LoadURL(Plugin):
    name: str = "load-url"
    description: str = (
        "Visit a URL and use a loader to load its contents. Don't provide a URL unless"
        " you're absolutely sure it exists. A topic name can be provided to store the"
        " documents in a particular topic."
    )

    async def run(self, url: str, topic_name: str = None) -> str:
        """
        Load the contents of a URL into a topic. If no topic name is provided,
        the Marvin default topic will be used.
        """
        if not url.startswith("http"):
            url = f"http://{url}"
        loader = URLLoader(urls=[url])
        await loader.load_and_store(topic_name=topic_name)
        return f"Loaded {url} into topic {topic_name}"


class LoadPDF(Plugin):
    name: str = "load-pdf"
    description: str = (
        "Load the contents of a PDF URL into a topic. If no topic name is provided, the"
        " Marvin default topic will be used."
    )

    async def run(self, pdf_url: str, topic_name: str = None) -> str:
        """
        Load the contents of a PDF URL into a topic. If no topic name is provided,
        the Marvin default topic will be used.
        """
        if PDFLoader is None:
            return (
                "PDFLoader is not available. Install it with `pip install marvin[pdf]`"
                " to use this plugin."
            )
        loader = PDFLoader(pdf_paths=[pdf_url])
        await loader.load_and_store(topic_name=topic_name)
        return f"Loaded {pdf_url} into topic {topic_name}"
