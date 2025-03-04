import json
import re
from typing import Any, TypedDict

from atproto import Client
from atproto.exceptions import BadRequestError
from atproto_client.models.app.bsky.feed.defs import ThreadViewPost
from pydantic_ai import ImageUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

import marvin
from marvin.utilities.logging import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    """App settings loaded from environment variables"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bsky_handle: str
    bsky_password: str


class Snapshot(TypedDict):
    """A snapshot of a single moment in a conversation timeline"""

    time_step: int
    event: str
    important_quotes: list[str]
    known_facts: list[str]
    possible_interpretations: list[str]
    uncertainties: list[str]


settings = Settings()  # type: ignore

visual_extraction_agent = marvin.Agent()


def extract_post_id(bluesky_url: str) -> tuple[str, str]:
    """Extract the profile and post ID from a Bluesky URL"""
    pattern = r"https?://bsky\.app/profile/([^/]+)/post/([a-zA-Z0-9]+)"
    match = re.match(pattern, bluesky_url)
    if not match:
        raise ValueError(f"Invalid Bluesky URL format: {bluesky_url}")
    return match.group(1), match.group(2)


def build_context(thread: ThreadViewPost) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if thread and thread.post:
        context["bsky post"] = {
            "author": thread.post.author.handle,
            "text": thread.post.record.text,
        }

        if hasattr(thread.post.record, "embed") and hasattr(
            thread.post.embed, "images"
        ):
            image_description_result = visual_extraction_agent.run(
                [
                    "summarize this image concisely, include direct quotes from the image",
                    ImageUrl(url=thread.post.embed.images[0].fullsize),
                ]
            )
            context["bsky post"]["embed"] = image_description_result

        if hasattr(thread, "replies"):
            context["replies"] = [
                {
                    "author": reply.post.author.handle,
                    "text": reply.post.record.text,
                    **(
                        {
                            "embed": visual_extraction_agent.run(
                                "summarize this image concisely, include direct quotes from the image",
                                attachments=[
                                    ImageUrl(url=reply.post.embed.images[0].fullsize),
                                ],
                            )
                        }
                        if hasattr(reply.post.record, "embed")
                        and hasattr(reply.post.embed, "images")
                        else {}
                    ),
                }
                for reply in thread.replies or []
                if hasattr(reply, "post")
            ]

    return context


def explain_bsky_post(
    bsky_post_url: str, details: dict[str, Any] | None = None
) -> None:
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

    assert isinstance(thread, ThreadViewPost)
    context = build_context(thread)

    if details:
        context |= details

    logger.info(json.dumps(context, indent=2))

    analysis = marvin.run(
        """
        Hypothesize the background of the bsky post based on provided facts.
        Identify actors that are implied to exist, what exactly they say, and what
        they can possibly know at each point in time based on existing information.
        Recall images describe the past, and therefore imply prior events.
        Dramatize the story, focusing on the the juciest interpersonal details.
        Be as concise as possible while being complete.
        """,
        context=context,
        result_type=list[Snapshot],
    )
    logger.info(analysis)
    print(marvin.summarize(analysis, instructions="very concise summary"))


if __name__ == "__main__":
    explain_theres_no_tension = True
    revealing_detail = "later, jeremiah said to nate 'lol I thought it was hilarious'"

    details = {
        "facts": [
            "@<username> on blue sky will tag someone in a post",
            "a post embed is an image that goes with a post",
            "jlowin.dev | jeremiah is Prefect's CEO, who is the original poster",
            "zzstoatzz | alternatebuild.dev | nate is an engineer at Prefect",
        ],
    }

    if explain_theres_no_tension:
        details["facts"].append(revealing_detail)

    explain_bsky_post(
        "https://bsky.app/profile/jlowin.dev/post/3ljgaagblxk2k", details=details
    )
