import json
from itertools import islice
from typing import Dict, Optional

import httpx
from pydantic import Field, SecretStr
from typing_extensions import Literal

from marvin.utilities.strings import html_to_content, slice_tokens

from ..settings import MarvinBaseSettings
from . import Tool


class SerpApiSettings(MarvinBaseSettings):
    """
    Settings for the SerpApi.

    Attributes:
        api_key (SecretStr): The API key for SerpApi. This is fetched from the
        environment variable "MARVIN_SERPAPI_API_KEY".
    """

    api_key: SecretStr = Field(None, env="MARVIN_SERPAPI_API_KEY")


class VisitUrl(Tool):
    """
    Tool for visiting a URL - only to be used in special cases.

    Attributes:
        description (str): Description of the tool.
    """

    description: str = "Visit a valid URL and return its contents."

    async def run(self, url: str) -> Optional[str]:  # type: ignore
        """
        Visit the given URL and return its contents.

        Args:
            url (str): The URL to visit.

        Returns:
            Optional[str]: The contents of the URL if successful, else None.
        """
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
    """
    Tool for searching the web with DuckDuckGo.

    Attributes:
        description (str): Description of the tool.
        backend (Literal["api", "html", "lite"]): The backend to use for the search.
    """

    description: str = "Search the web with DuckDuckGo."
    backend: Literal["api", "html", "lite"] = "lite"

    async def run(self, query: str, n_results: int = 3) -> Optional[str]:  # type: ignore # noqa: E501
        """
        Search the web with DuckDuckGo and return the results.

        Args:
            query (str): The search query.
            n_results (int, optional): The number of results to return. Defaults to 3.

        Returns:
            Optional[str]: The search results if successful, else None.
        """
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
            ]  # type: ignore


class GoogleSearch(Tool):
    """
    Tool for performing a Google search and retrieving the results.

    Attributes:
        description (str): Description of the tool.
    """

    description: str = """
        For performing a Google search and retrieving the results.
        
        Provide the search query to get answers.
    """

    async def run(  # type: ignore
        self, query: str, n_results: int = 3
    ) -> Optional[Dict[str, str]]:
        """
        Perform a Google search and return the results.

        Args:
            query (str): The search query.
            n_results (int, optional): The number of results to return. Defaults to 3.

        Returns:
            Optional[Dict[str, str]]: The search results if successful, else None.
        """
        try:
            from serpapi import GoogleSearch as google_search  # type: ignore
        except ImportError:
            raise RuntimeError(
                "You must install the serpapi library to use this tool. "
                "You can do so by running `pip install 'marvin[serpapi]'`."
            )

        if (api_key := SerpApiSettings().api_key) is None:  # type: ignore
            raise RuntimeError(
                "You must provide a SerpApi API key to use this tool. You can do so by"
                " setting the MARVIN_SERPAPI_API_KEY environment variable."
            )

        search_params = {
            "q": query,
            "api_key": api_key.get_secret_value(),
        }
        results = google_search(search_params).get_dict()  # type: ignore

        if "error" in results:
            raise RuntimeError(results["error"])  # type: ignore
        return [
            {"title": r.get("title"), "href": r.get("link"), "body": r.get("snippet")}  # type: ignore # noqa: E501
            for r in results.get("organic_results", [])[:n_results]  # type: ignore
        ]  # type: ignore
