import asyncio

import httpx
from duckduckgo_search import DDGS

import marvin
from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens


async def safe_get(client, url):
    try:
        return await client.get(url)
    except httpx.ReadTimeout:
        pass


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


async def search_ddg(query: str, n: int = 5) -> str:
    answers, search_results = await asyncio.gather(
        *[
            marvin.utilities.async_utils.run_async(ddg_answer_search, query),
            marvin.utilities.async_utils.run_async(
                ddg_text_search, query, max_results=n
            ),
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


class DuckDuckGo(Plugin):
    description: str = (
        "Search the web with DuckDuckGo. Useful for current events. If you already know"
        " the answer, you don't need to use this unless asked to. Works best with"
        " simple, discrete queries for one question at a time."
    )

    async def run(self, query: str) -> str:
        return await search_ddg(query)
