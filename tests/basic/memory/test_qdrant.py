import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from marvin.memory.providers.qdrant import QdrantMemory


async def test_persistent_qdrant_memory_isolation_and_limits(tmp_path):
    path = str(tmp_path / "qdrant")
    client = AsyncQdrantClient(path=path)
    provider = QdrantMemory(client=client, collection_name="notes-{key}")
    content = "The user prefers concise answers."
    try:
        memory_id = await provider.add("preferences", content)
        await provider.add("preferences", "The office opens at nine.")
        other_id = await provider.add("other", "The backup code is 12345.")
    finally:
        await client.close()

    client = AsyncQdrantClient(path=path)
    provider = QdrantMemory(client=client, collection_name="notes-{key}")
    try:
        assert await provider.search("preferences", content, n=1) == {
            memory_id: content
        }
        assert len(await provider.search("preferences", "user", n=10)) == 2
        assert await provider.search("other", "backup") == {
            other_id: "The backup code is 12345."
        }
        await provider.delete("preferences", memory_id)
        assert memory_id not in await provider.search("preferences", content)
        await provider.add("preferences", "The user prefers Python.")
        assert len(await provider.search("preferences", "user")) == 2
    finally:
        await client.close()


@pytest.mark.skipif(
    not hasattr(AsyncQdrantClient, "add"), reason="requires legacy seeding API"
)
async def test_existing_legacy_collection(tmp_path):
    path = str(tmp_path / "qdrant")
    client = AsyncQdrantClient(path=path)
    memory_id = str(uuid.uuid4())
    content = "The number is 42."
    try:
        await client.add(
            collection_name="memory-legacy",
            documents=[content],
            metadata=[{"id": memory_id}],
            ids=[memory_id],
        )
    finally:
        await client.close()

    client = AsyncQdrantClient(path=path)
    provider = QdrantMemory(client=client)
    try:
        assert await provider.search("legacy", "number") == {memory_id: content}
        await provider.add("legacy", "The number is 43.")
        assert len(await provider.search("legacy", "number")) == 2
        await provider.delete("legacy", memory_id)
        assert memory_id not in await provider.search("legacy", "number")
    finally:
        await client.close()
