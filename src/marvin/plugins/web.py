import json

import httpx
from fastapi import status

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
