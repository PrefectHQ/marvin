import httpx


async def download_url_content(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.content


async def url_is_ok(url: str) -> bool:
    async with httpx.AsyncClient(follow_redirects=True, timeout=2) as client:
        response = await client.head(url, timeout=2)
        response.raise_for_status()
        return response.status_code == httpx.codes.OK
