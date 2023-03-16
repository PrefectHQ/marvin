import httpx
from fastapi import status

from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens


class VisitURL(Plugin):
    name: str = "visit-url"
    description: str = (
        "Visit a URL and return its contents. Do not guess URLs; only supply ones that"
        " you know for certain."
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
            return slice_tokens(html_to_content(response.text), 2500)
        else:
            return f"Failed to load URL: {response.status_code}"
