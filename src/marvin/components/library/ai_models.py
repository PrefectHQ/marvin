import json
from typing import Optional

import httpx
from pydantic import BaseModel, Field, validator
from typing_extensions import Self

import marvin


@marvin.ai_model(instructions="Produce a comprehensive Discourse post from text.")
class DiscoursePost(BaseModel):
    title: Optional[str] = Field(
        description="A fitting title for the post.",
        example="How to install Prefect",
    )
    question: Optional[str] = Field(
        description="The question that is posed in the text.",
        example="How do I install Prefect?",
    )
    answer: Optional[str] = Field(
        description=(
            "The complete answer to the question posed in the text."
            " This answer should comprehensively answer the question, "
            " explain any relevant concepts, and have a friendly, academic tone,"
            " and provide any links to relevant resources found in the thread."
            " This answer should be written in Markdown, with any code blocks"
            " formatted as `code` or ```<language_name>\n<the code block itself>```."
        )
    )

    topic_url: Optional[str] = Field(None)

    @validator("title", "question", "answer")
    def non_empty_string(cls, value):
        if not value:
            raise ValueError("this field cannot be empty")
        return value

    @classmethod
    def from_slack_thread(cls, messages: list[str]) -> Self:
        return cls("\n".join(messages))

    async def publish(
        self,
        topic: str = None,
        category: int = marvin.settings.discourse_help_category_id,
        url: str = marvin.settings.discourse_url,
        tags: list[str] = None,
    ) -> str:
        headers = {
            "Api-Key": marvin.settings.discourse_api_key.get_secret_value(),
            "Api-Username": marvin.settings.discourse_api_username,
            "Content-Type": "application/json",
        }
        data = {
            "title": self.title,
            "raw": (
                f"## **{self.question}**\n\n{self.answer}"
                "\n\n---\n\n*This topic was created by Marvin.*"
            ),
            "category": category,
            "tags": tags or ["marvin"],
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

        self.topic_url = f"{url}/t/{topic_id}/{post_number}"

        return self.topic_url
