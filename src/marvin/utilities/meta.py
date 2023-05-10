import pendulum
from prefect.utilities.asyncutils import sync_compatible

import marvin
from marvin.infra.chroma import Chroma
from marvin.models.documents import Document


@sync_compatible
async def record_feedback(feedback: str, topic: str = None):
    """Record feedback on a given topic."""

    processed_feedback = await Document(
        text=feedback,
        metadata={
            "source": "user feedback",
            "created_at": pendulum.now().isoformat(),
        },
    ).to_excerpts()

    async with Chroma(topic or marvin.settings.default_topic) as chroma:
        await chroma.add(
            documents=processed_feedback,
            skip_existing=True,
        )
