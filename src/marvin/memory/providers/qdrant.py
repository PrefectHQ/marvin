import uuid
from dataclasses import dataclass, field

import marvin
from marvin.memory.memory import MemoryProvider

try:
    from qdrant_client import AsyncQdrantClient, models
except ImportError:
    raise ImportError(
        """To use Qdrant as a memory provider, install the `qdrant_client` package.
        Run `pip install 'qdrant_client[fastembed]`'"""
    )


@dataclass(kw_only=True)
class QdrantMemory(MemoryProvider):
    model_config = dict(arbitrary_types_allowed=True)
    client: AsyncQdrantClient = field(
        default_factory=lambda: AsyncQdrantClient(
            path=str(marvin.settings.home_path / "memory/qdrant"),
        ),
        metadata={
            "description": f"""
            An instance of `qdrant_client.AsyncQdrantClient`.
            Defaults to a local instance persisted at `{str(marvin.settings.home_path / "memory/qdrant")}`.
            """
        },
    )

    collection_name: str = field(
        default="memory-{key}",
        metadata={
            "description": """
            Optional; the name of the collection to use. This should be a 
            string optionally formatted with the variable `key`, which 
            will be provided by the memory module. The default is `"memory-{key}"`.
            """,
        },
    )

    async def get_collection(self, memory_key: str) -> models.CollectionInfo:
        collection_name = self.collection_name.format(key=memory_key)
        return await self.client.get_collection(collection_name=collection_name)

    async def add(self, memory_key: str, content: str) -> str:
        memory_id = str(uuid.uuid4())
        collection_name = self.collection_name.format(key=memory_key)
        await self.client.add(
            collection_name=collection_name,
            documents=[content],
            metadata=[{"id": memory_id}],
            ids=[memory_id],
        )
        return memory_id

    async def delete(self, memory_key: str, memory_id: str) -> None:
        collection_name = self.collection_name.format(key=memory_key)
        await self.client.delete(
            collection_name=collection_name, points_selector=[memory_id]
        )

    async def search(self, memory_key: str, query: str, n: int = 20) -> dict[str, str]:
        collection_name = self.collection_name.format(key=memory_key)
        results = await self.client.query(
            collection_name=collection_name,
            query_text=query,
            limit=n,
        )

        return {r.id: r.document for r in results}
