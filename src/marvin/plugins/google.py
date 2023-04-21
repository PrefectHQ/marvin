import inspect

import marvin
from marvin.plugins import Plugin


class GoogleSearchAPI(Plugin):
    description: str = (
        "Search the web with Google. Useful for when you need to answer questions about"
        " current events. You should ask targeted questions. The results will include a"
        " snippet and a URL that you could visit for more information."
    )

    async def run(self, query: str):
        return await search_google(query)


async def search_google(query, n: int = 10, return_as_text=False, **kwargs):
    from googleapiclient.discovery import build

    service = build(
        "customsearch",
        "v1",
        developerKey=marvin.settings.google_api_key.get_secret_value(),
    ).cse()

    api_results = []
    for start in range(0, n, 10):
        req = service.list(
            q=query,
            cx=marvin.settings.google_cse_id,
            num=min(10, n - start),
            start=start + 1,
            **kwargs,
        )
        api_results.append(await marvin.utilities.async_utils.run_async(req.execute))
    results = [r for result in api_results for r in result["items"]]

    if not return_as_text:
        return results

    template = inspect.cleandoc("""
        
        Result {i}: {title}
        URL: {url}
        Summary: {summary}
        """)

    return "\n\n".join(
        template.format(i=i + 1, title=r["title"], url=r["link"], summary=r["snippet"])
        for i, r in enumerate(results)
    )
