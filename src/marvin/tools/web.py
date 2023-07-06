import asyncio
import json

import httpx

from marvin.tools import Tool
from marvin.utilities.async_utils import run_async
from marvin.utilities.strings import html_to_content, slice_tokens


async def safe_get(client, url):
    try:
        return await client.get(url)
    except httpx.ReadTimeout:
        pass


async def search_ddg(query: str, n: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        raise ImportError(
            "Please install the DDG extra to use this tool: `pip install 'marvin[ddg]'`"
        )

    def ddg_answer_search(keywords: str):
        results = []
        for r in DDGS().answers(keywords=keywords):
            results.append(r)
            if len(results) >= 1:
                break
        return results

    def ddg_text_search(keywords: str, max_results: int = None, page: int = None):
        results = []
        for r in DDGS().text(keywords=keywords):
            results.append(r)
            if (max_results and len(results) >= max_results) or (
                page and len(results) >= 20
            ):
                break
        return results

    answers, search_results = await asyncio.gather(
        *[
            run_async(ddg_answer_search, query),
            run_async(ddg_text_search, query, max_results=n),
        ]
    )

    async with httpx.AsyncClient(timeout=0.5) as client:
        responses = await asyncio.gather(
            *[safe_get(client, s["href"]) for s in search_results]
        )
        for i, r in enumerate(responses):
            if r is None:
                continue
            search_results[i]["content"] = slice_tokens(html_to_content(r.text), 400)

    result = "\n\n".join(
        f"{s['title']} ({s['href']}): {s.get('content', s['body'])}"
        for s in search_results
    )
    if answers:
        result = "\n\n".join([answers[0]["text"], result])
    return result


class VisitUrl(Tool):
    """Tool for visiting a URL."""

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

    async def run(self, query: str) -> str:
        return await search_ddg(query)
