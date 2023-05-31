import json
from typing import Optional

import httpx
import pendulum
from pydantic import BaseModel, Field, validator

import marvin
from marvin.infra.chroma import Chroma
from marvin.models.documents import Document


async def create_chroma_document(
    text: str,
    topic: str = None,
    **kwargs,
):
    processed_feedback = await Document(
        text=text,
        source="slack",
        metadata={
            "created_at": pendulum.now().isoformat(),
            **kwargs,
        },
    ).to_excerpts()

    async with Chroma(topic or marvin.settings.default_topic) as chroma:
        await chroma.add(
            documents=processed_feedback,
            skip_existing=True,
        )


@marvin.ai_model
class DiscoursePost(BaseModel):
    title: Optional[str] = Field(
        description="A fitting title for the post.",
        example="How to install Prefect",
    )
    question: Optional[str] = Field(
        description="The question that the thread poses to the community.",
        example="How do I install Prefect?",
    )
    answer: Optional[str] = Field(
        description=(
            "The complete answer to the question posed in the thread."
            " This answer should comprehensively answer the question, "
            " explain any relevant concepts, and have a friendly, academic tone."
        ),
        example="You can install Prefect by running `pip install -U prefect`.",
    )

    @validator("title", "question", "answer")
    def non_empty_string(cls, value):
        if not value:
            raise ValueError("this field cannot be empty")
        return value


async def create_discourse_topic(
    text: str,
    topic: str = None,
    category: int = marvin.settings.discourse_help_category_id,
    url: str = marvin.settings.discourse_url,
) -> str:
    discourse_post = DiscoursePost(text)

    headers = {
        "Api-Key": marvin.settings.discourse_api_key.get_secret_value(),
        "Api-Username": marvin.settings.discourse_api_username,
        "Content-Type": "application/json",
    }
    data = {
        "title": discourse_post.title,
        "raw": (
            f"## **{discourse_post.question}**\n\n{discourse_post.answer}"
            "\n\n---\n\n*This topic was created by Marvin.*"
        ),
        "category": category,
        "tags": [marvin.settings.default_topic],
    }

    if topic:
        data["tags"].append(topic)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"{url}/posts.json", headers=headers, data=json.dumps(data)
        )

    response.raise_for_status()

    response_data = response.json()
    topic_id = response_data.get("topic_id")
    post_number = response_data.get("post_number")

    new_topic_url = f"{url}/t/{topic_id}/{post_number}"
    return new_topic_url


async def record_feedback(feedback: str, topic: str = None, **kwargs):
    """Record feedback on a given topic."""

    feedback_mechanism = globals().get(marvin.settings.feedback_mechanism)

    await feedback_mechanism(text=feedback, topic=topic, **kwargs)
