import os
from typing import Dict

import httpx
from pydantic import BaseModel, Field, validator

from marvin.loaders.base import Loader
from marvin.models.documents import Document
from marvin.utilities.strings import count_tokens

COMMON_QUESTIONS_CATEGORY_ID = 24


class DiscoursePost(BaseModel):
    """Discourse post."""

    base_url: str

    id: int
    category_id: int
    cooked: str
    topic_id: int
    topic_slug: str
    topic_title: str

    @property
    def url(self) -> str:
        """Return the URL for the post."""
        return f"{self.base_url}/t/{self.topic_slug}/{self.topic_id}"


class DiscourseLoader(Loader):
    """Loader for Discourse posts."""

    url: str = Field(default="https://discourse.prefect.io")
    n_posts: int = Field(default=50)
    request_headers: Dict[str, str] = Field(default_factory=dict)

    _default_category_id: int = COMMON_QUESTIONS_CATEGORY_ID

    @validator("request_headers", always=True)
    def auth_headers(cls, v):
        """Add authentication headers if a Discourse token is available."""
        if (token := os.getenv("DISCOURSE_API_KEY")) and (
            user := os.getenv("DISCOURSE_API_USERNAME")
        ):
            v.update({"Api-Key": token, "Api-Username": user})
        return v

    async def load(self) -> list[Document]:
        """Load Discourse posts."""
        documents = []
        for post in await self._get_posts():
            documents.extend(
                await Document(
                    text=post.cooked,
                    metadata={
                        "title": post.topic_title,
                        "url": post.url,
                        "category": "Common Questions",
                    },
                    tokens=count_tokens(post.cooked),
                ).to_excerpts()
            )
        return documents

    async def _get_posts(self) -> list[DiscoursePost]:
        """Get posts from a Discourse forum."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/posts.json", headers=self.request_headers
            )
            response.raise_for_status()
            return [
                DiscoursePost(base_url=self.url, **post)
                for post in response.json()["latest_posts"]
                if post["category_id"] == self._default_category_id
            ]


if __name__ == "__main__":
    import asyncio

    asyncio.run(DiscourseLoader().load_and_store())
