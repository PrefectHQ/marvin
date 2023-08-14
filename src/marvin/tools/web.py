import json
from itertools import islice
from typing import Dict

import httpx
from pydantic import Field, SecretStr
from typing_extensions import Literal

from marvin.settings import MarvinBaseSettings
from marvin.tools import Tool
from marvin.utilities.strings import html_to_content, slice_tokens


class SerpApiSettings(MarvinBaseSettings):
    api_key: SecretStr = Field(None, env="MARVIN_SERPAPI_API_KEY")


class VisitUrl(Tool):
    """Tool for visiting a URL - only to be used in special cases."""

    description: str = "Visit a valid URL and return its contents."

    async def run(self, url: str) -> str:
        if not url.startswith("http"):
            url = f"http://{url}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=2) as client:
            try:
                response = await client.get(url)
            except httpx.ConnectTimeout:
                return "Failed to load URL: Connection timed out"
        if response.status_code == 200:
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


class DuckDuckGoSearch(Tool):
    """Tool for searching the web with DuckDuckGo."""

    description: str = "Search the web with DuckDuckGo."
    backend: Literal["api", "html", "lite"] = "lite"

    async def run(self, query: str, n_results: int = 3) -> str:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise RuntimeError(
                "You must install the duckduckgo-search library to use this tool. "
                "You can do so by running `pip install 'marvin[ddg]'`."
            )

        with DDGS() as ddgs:
            return [
                r for r in islice(ddgs.text(query, backend=self.backend), n_results)
            ]


class GoogleSearch(Tool):
    description: str = """
        For performing a Google search and retrieving the results.
        
        Provide the search query to get answers.
    """

    async def run(self, query: str, n_results: int = 3) -> Dict:
        try:
            from serpapi import GoogleSearch as google_search
        except ImportError:
            raise RuntimeError(
                "You must install the serpapi library to use this tool. "
                "You can do so by running `pip install 'marvin[serpapi]'`."
            )

        if (api_key := SerpApiSettings().api_key) is None:
            raise RuntimeError(
                "You must provide a SerpApi API key to use this tool. You can do so by"
                " setting the MARVIN_SERPAPI_API_KEY environment variable."
            )

        search_params = {
            "q": query,
            "api_key": api_key.get_secret_value(),
        }
        results = google_search(search_params).get_dict()

        if "error" in results:
            raise RuntimeError(results["error"])
        return [
            {"title": r.get("title"), "href": r.get("link"), "body": r.get("snippet")}
            for r in results.get("organic_results", [])[:n_results]
        ]
