import httpx
from fastapi import status

from marvin.plugins import Plugin
from marvin.utilities.strings import html_to_content, slice_tokens


class VisitURL(Plugin):
    description: str = "Visit a URL to load its content"

    async def run(self, url: str) -> str:
        if not url.startswith("http"):
            url = f"http://{url}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=2) as client:
            try:
                response = await client.get(url)
            except httpx.ConnectTimeout:
                return "Failed to load URL: Connection timed out"
        if response.status_code == status.HTTP_200_OK:
            return slice_tokens(await html_to_content(response.text), 250)
        else:
            return f"Failed to load URL: {response.status_code}"
