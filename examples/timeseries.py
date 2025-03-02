import json
import re
from typing import Any, TypedDict

from atproto import Client
from atproto.exceptions import BadRequestError
from pydantic_ai import Agent, ImageUrl
from pydantic_ai.models.gemini import GeminiModel
from pydantic_settings import BaseSettings, SettingsConfigDict

import marvin
from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


class Snapshot(TypedDict):
    """A snapshot of a single moment in a conversation timeline"""

    timeStep: int
    event: str
    knownFacts: list[str]
    possibleInterpretations: list[str]
    uncertainties: list[str]


class Settings(BaseSettings):
    """App settings loaded from environment variables"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bsky_handle: str
    bsky_password: str

    gemini_api_key: str


def extract_post_id(bluesky_url: str) -> tuple[str, str]:
    """Extract the profile and post ID from a Bluesky URL"""
    pattern = r"https?://bsky\.app/profile/([^/]+)/post/([a-zA-Z0-9]+)"
    match = re.match(pattern, bluesky_url)
    if not match:
        raise ValueError(f"Invalid Bluesky URL format: {bluesky_url}")
    return match.group(1), match.group(2)


def main(bsky_post_url: str, details: dict[str, Any] | None = None) -> None:
    settings = Settings()  # type: ignore
    client = Client()
    client.login(settings.bsky_handle, settings.bsky_password)

    try:
        profile, post_id = extract_post_id(bsky_post_url)
        thread = client.app.bsky.feed.get_post_thread(
            {"uri": f"at://{profile}/app.bsky.feed.post/{post_id}"}
        ).thread
    except (ValueError, KeyError, BadRequestError) as e:
        logger.error(f"Error fetching thread: {e}")
        return

    context: dict[str, Any] = {}

    if thread and thread.post:
        context["bsky post"] = {
            "author": thread.post.author.handle,
            "text": thread.post.record.text,
        }

        if hasattr(thread.post.record, "embed") and hasattr(
            thread.post.embed, "images"
        ):
            image_description_result = Agent(
                model=GeminiModel(
                    model_name="gemini-2.0-flash-exp",
                    api_key=settings.gemini_api_key,
                ),
            ).run_sync(
                [
                    "summarize this image concisely, include direct quotes from the image",
                    ImageUrl(url=thread.post.embed.images[0].fullsize),
                ]
            )
            context["bsky post"]["embed"] = image_description_result.data

        if hasattr(thread, "replies"):
            context["replies"] = []
            for reply in thread.replies:
                if hasattr(reply, "post"):
                    context["replies"].append(
                        {
                            "author": reply.post.author.handle,
                            "text": reply.post.record.text,
                        }
                    )

    if details:
        context |= details

    logger.info(json.dumps(context, indent=2))

    analysis = marvin.run(
        """
        Tell a story explaining the likely background of this bsky post.
        At each point in time consider info available to each actor. 
        Focus on exactly what actors say and do, and what this likely implies.
        Deduce a reasonable timeline of events, recall images are of the past.
        """,
        context=context,
        result_type=list[Snapshot],
    )
    logger.info(analysis)


if __name__ == "__main__":
    main(
        "https://bsky.app/profile/jlowin.dev/post/3ljgaagblxk2k",
        details={
            "facts": [
                "this interaction takes place on bluesky (bsky)"
                "@<username> on bsky will tag someone in a post",
                "a post emebed is an image that goes with a post",
                "jlowin.dev | jeremiah is Prefect's CEO, who is the original poster",
                "zzstoatzz | alternatebuild.dev | nate is an engineer at Prefect",
            ],
        },
    )
