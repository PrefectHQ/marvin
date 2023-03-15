import asyncio

import httpx
from duckduckgo_search import ddg, ddg_answers

import marvin
from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens


async def safe_get(client, url):
    try:
        await client.get(url)
    except httpx.ReadTimeout:
        pass


async def search_ddg(query: str, n: int = 5):
    answers, search_results = await asyncio.gather(
        *[
            marvin.utilities.async_utils.run_async(ddg_answers, query),
            marvin.utilities.async_utils.run_async(ddg, query, max_results=n),
        ]
    )

    async with httpx.AsyncClient(timeout=0.5) as client:
        responses = await asyncio.gather(
            *[safe_get(client, s["href"]) for s in search_results]
        )
        for i, r in enumerate(responses):
            if r is None:
                continue
            search_results[i]["content"] = slice_tokens(
                await html_to_content(r.text), 200
            )

    result = "\n\n".join(
        f"{s['title']} ({s['href']}): {s.get('content', s['body'])}"
        for s in search_results
    )
    if answers:
        result = "\n\n".join([answers[0]["text"], result])
    return result


class DuckDuckGo(Plugin):
    description: str = (
        "Search the web with DuckDuckGo. Use this plugin to answer questions that are"
        " unlikely to be in your training data or about current events. You can break"
        " queries into multiple parts to solve problems step-by-step."
    )

    async def run(self, query: str) -> str:
        return await search_ddg(query)
