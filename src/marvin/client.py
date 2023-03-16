from httpx import AsyncClient

from marvin.infra.chroma import Chroma
from marvin.models.digests import Digest


class MarvinClient(AsyncClient):
    """To be replaced by a client that uses the Marvin API."""

    async def write_to_topic(self, topic_name: str, digest: Digest):
        """(Will call endpoint to) Write a digest to a topic."""
        await Chroma(topic_name=topic_name).add(**digest.dict())

    async def delete_from_topic(
        self, topic_name: str, ids: list[str] = None, where: dict = None
    ):
        """(Will call endpoint to) Delete documents from a topic."""
        await Chroma(topic_name=topic_name).delete(ids=ids, where=where)
