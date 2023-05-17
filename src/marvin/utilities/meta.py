import json

import httpx
import pendulum

import marvin
from marvin.infra.chroma import Chroma
from marvin.models.documents import Document


@marvin.ai_fn(llm_model_name="gpt-3.5-turbo")
async def make_post_title(interaction: str) -> str:
    """Generates a title for a post that describes the text from the interaction.
    Ideally, it should be in the form of "How to {do something} with {some concept}"."""


async def save_to_chroma(
    title: str,
    text: str,
    topic: str = None,
    **kwargs,
):
    processed_feedback = await Document(
        text=text,
        metadata={
            "title": title,
            "source": "user feedback",
            "created_at": pendulum.now().isoformat(),
            **kwargs,
        },
    ).to_excerpts()

    async with Chroma(topic or marvin.settings.default_topic) as chroma:
        await chroma.add(
            documents=processed_feedback,
            skip_existing=True,
        )


async def save_to_discourse(
    title: str,
    text: str,
    topic: str = None,
    category: int = marvin.settings.discourse_help_category_id,
    url: str = marvin.settings.discourse_url,
):
    headers = {
        "Api-Key": marvin.settings.discourse_api_key.get_secret_value(),
        "Api-Username": marvin.settings.discourse_api_username,
        "Content-Type": "application/json",
    }
    data = {
        "title": title,
        "raw": text,
        "category": category,
        "tags": [marvin.settings.default_topic],
    }

    if topic:
        data["tags"].append(topic)

    async with httpx.AsyncClient() as client:
        await client.post(
            url=f"{url}/posts.json", headers=headers, data=json.dumps(data)
        )


async def record_feedback(feedback: str, topic: str = None, **kwargs):
    """Record feedback on a given topic."""

    feedback_title = await make_post_title(feedback)

    feedback_mechanism = globals().get(marvin.settings.feedback_mechanism)

    await feedback_mechanism(title=feedback_title, text=feedback, topic=topic, **kwargs)
