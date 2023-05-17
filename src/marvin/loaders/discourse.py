import math
from typing import Callable, Dict

import httpx
import pendulum
from pydantic import BaseModel, Field, validator

import marvin
from marvin.loaders.base import Loader
from marvin.models.documents import Document


class DiscoursePost(BaseModel):
    """Discourse post."""

    base_url: str
    id: int
    topic_id: int
    cooked: str
    created_at: pendulum.DateTime
    topic_slug: str

    @property
    def url(self) -> str:
        """Return the URL for the post."""
        return f"{self.base_url}/t/{self.topic_slug}/{self.topic_id}"


class DiscourseLoader(Loader):
    """Loader for Discourse topics."""

    source_type: str = Field(default="discourse")

    url: str = Field(default="https://discourse.prefect.io")
    n_topic: int = Field(default=30)
    per_page: int = Field(default=30)
    request_headers: Dict[str, str] = Field(default_factory=dict)
    include_topic_filter: Callable[[dict], bool] = Field(default=lambda _: True)
    include_post_filter: Callable[[dict], bool] = Field(default=lambda _: True)

    @validator("request_headers", always=True)
    def auth_headers(cls, v):
        """Add authentication headers if a Discourse token is available."""
        if not (api_key := marvin.settings.discourse_api_key.get_secret_value()):
            marvin.get_logger().warning(
                "No Discourse API key found - some endpoints may be inaccessible. You"
                " can set `DISCOURSE_API_KEY` and `DISCOURSE_API_USERNAME` in your"
                " environment."
            )
        v.update(
            {
                "Api-Key": api_key,
                "Api-Username": marvin.settings.discourse_api_username,
            }
        )
        return v

    async def load(self) -> list[Document]:
        """Load Discourse posts."""
        documents = []
        for post in await self._get_all_posts():
            documents.extend(
                await Document(
                    text=post.cooked,
                    metadata={
                        "source": self.source_type,
                        "title": post.topic_slug.replace("-", " ").capitalize(),
                        "link": post.url,
                        "created_at": post.created_at.timestamp(),
                    },
                ).to_excerpts()
            )
        return documents

    async def _get_posts_for_topic(self, topic_id: int) -> list[dict]:
        """Get posts for a specific topic."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/t/{topic_id}.json", headers=self.request_headers
            )
            response.raise_for_status()
            return [
                post
                for post in response.json()["post_stream"]["posts"]
                if self.include_post_filter(post)
            ]

    async def _get_all_posts(self) -> list[DiscoursePost]:
        """Get topics and posts from a Discourse forum filtered by a specific tag."""
        all_topics = []
        pages = math.ceil(self.n_topic / self.per_page)

        async with httpx.AsyncClient() as client:
            for page in range(pages):
                response = await client.get(
                    f"{self.url}/latest.json",
                    headers=self.request_headers,
                    params={"page": page, "per_page": self.per_page},
                )
                response.raise_for_status()

                topics = response.json()["topic_list"]["topics"]
                all_topics.extend(topics)

                # Break the loop if we have fetched the desired number of topics
                if len(all_topics) >= self.n_topic:
                    break

            filtered_topics = [
                topic for topic in all_topics if self.include_topic_filter(topic)
            ]

            all_posts = []
            for topic in filtered_topics:
                self.logger.info(
                    f"Fetching posts for retrieved topic {topic['title']!r}"
                )
                posts = await self._get_posts_for_topic(topic["id"])
                all_posts.append(
                    DiscoursePost(base_url=self.url, **posts[0])
                )  # original post
                all_posts.extend(
                    [
                        DiscoursePost(base_url=self.url, **post)
                        for post in posts[1:]
                        if self.include_post_filter(post)
                    ]
                )
            return all_posts
