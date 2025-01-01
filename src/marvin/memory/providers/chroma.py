import uuid
from dataclasses import dataclass, field
from typing import Dict

import chromadb

import marvin
from marvin.memory.memory import MemoryProvider


@dataclass(kw_only=True)
class ChromaMemory(MemoryProvider):
    model_config = dict(arbitrary_types_allowed=True)
    client: chromadb.ClientAPI = field(
        default_factory=lambda: chromadb.PersistentClient(
            path=str(marvin.settings.home_path / "memory/chroma")
        )
    )
    collection_name: str = field(
        default="memory-{key}",
        metadata={
            "description": """
            Optional; the name of the collection to use. This should be a 
            string optionally formatted with the variable `key`, which 
            will be provided by the memory module. The default is `"memory-{key}"`.
            """
        },
    )

    def get_collection(self, memory_key: str) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            self.collection_name.format(key=memory_key)
        )

    def add(self, memory_key: str, content: str) -> str:
        collection = self.get_collection(memory_key)
        memory_id = str(uuid.uuid4())
        collection.add(
            documents=[content], metadatas=[{"id": memory_id}], ids=[memory_id]
        )
        return memory_id

    def delete(self, memory_key: str, memory_id: str) -> None:
        collection = self.get_collection(memory_key)
        collection.delete(ids=[memory_id])

    def search(self, memory_key: str, query: str, n: int = 20) -> Dict[str, str]:
        results = self.get_collection(memory_key).query(
            query_texts=[query], n_results=n
        )
        return dict(zip(results["ids"][0], results["documents"][0]))


def ChromaEphemeralMemory(**kwargs) -> ChromaMemory:
    return ChromaMemory(client=chromadb.EphemeralClient(**kwargs))


def ChromaPersistentMemory(path: str = None, **kwargs) -> ChromaMemory:
    return ChromaMemory(
        client=chromadb.PersistentClient(
            path=path or str(marvin.settings.home_path / "memory" / "chroma"),
            **kwargs,
        )
    )


def ChromaCloudMemory(
    tenant: str | None = None,
    database: str | None = None,
    api_key: str | None = None,
    **kwargs,
) -> ChromaMemory:
    return ChromaMemory(
        client=chromadb.CloudClient(
            api_key=api_key or marvin.settings.chroma_cloud_api_key,
            tenant=tenant or marvin.settings.chroma_cloud_tenant,
            database=database or marvin.settings.chroma_cloud_database,
            **kwargs,
        )
    )
