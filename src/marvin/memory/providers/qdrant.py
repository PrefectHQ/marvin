import uuid
from dataclasses import dataclass, field

import marvin
from marvin.memory.memory import MemoryProvider

try:
    from qdrant_client import AsyncQdrantClient, models
except ImportError:
    raise ImportError(
        """To use Qdrant as a memory provider, install the `qdrant_client` package.
        Run `pip install 'qdrant-client[fastembed]'`"""
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

    def _embedding_model(self) -> tuple[str, str]:
        # Collections written by `AsyncQdrantClient.add` in qdrant-client
        # before 1.20 use this model and vector name. Reusing them keeps
        # those collections searchable.
        return "BAAI/bge-small-en", "fast-bge-small-en"

    async def add(self, memory_key: str, content: str) -> str:
        memory_id = str(uuid.uuid4())
        collection_name = self.collection_name.format(key=memory_key)
        model, vector_name = self._embedding_model()
        if not await self.client.collection_exists(collection_name):
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    vector_name: models.VectorParams(
                        size=self.client.get_embedding_size(model),
                        distance=models.Distance.COSINE,
                    )
                },
            )
        await self.client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=memory_id,
                    vector={vector_name: models.Document(text=content, model=model)},
                    payload={"id": memory_id, "document": content},
                )
            ],
            wait=True,
        )
        return memory_id

    async def delete(self, memory_key: str, memory_id: str) -> None:
        collection_name = self.collection_name.format(key=memory_key)
        await self.client.delete(
            collection_name=collection_name, points_selector=[memory_id]
        )

    async def search(self, memory_key: str, query: str, n: int = 20) -> dict[str, str]:
        collection_name = self.collection_name.format(key=memory_key)
        model, vector_name = self._embedding_model()
        results = await self.client.query_points(
            collection_name=collection_name,
            query=models.Document(text=query, model=model),
            using=vector_name,
            limit=n,
            with_payload=True,
        )

        return {
            str(r.id): (r.payload or {}).get("document", "") for r in results.points
        }
