import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import lancedb
    from lancedb.embeddings import get_registry
    from lancedb.pydantic import LanceModel, Vector
except ImportError:
    raise ImportError(
        "LanceDB is not installed. Please install it with `pip install lancedb`.",
    )

from pydantic import Field

import marvin
from marvin.memory.memory import MemoryProvider


@dataclass(kw_only=True)
class LanceMemory(MemoryProvider):
    uri: Path = field(
        default=marvin.settings.home_path / "memory" / "lancedb",
        metadata={"description": "The URI of the Lance database to use."},
    )
    table_name: str = field(
        default="memory-{key}",
        metadata={
            "description": """
            Optional; the name of the table to use. This should be a 
            string optionally formatted with the variable `key`, which 
            will be provided by the memory module. The default is `"memory-{key}"`.
            """,
        },
    )
    embedding_fn: Callable[..., Any] = field(
        default_factory=lambda: get_registry()
        .get("openai")
        .create(name="text-embedding-ada-002"),
        metadata={
            "description": "The LanceDB embedding function to use. Defaults to `get_registry().get('openai').create(name='text-embedding-ada-002')`.",
        },
    )
    _cached_model: LanceModel | None = None

    def get_model(self) -> LanceModel:
        if self._cached_model is None:
            fn = self.embedding_fn

            class Memory(LanceModel):
                id: str = Field(..., description="The ID of the memory.")
                text: str = fn.SourceField()
                vector: Vector(fn.ndims()) = fn.VectorField()

            self._cached_model = Memory

        return self._cached_model

    def get_db(self) -> lancedb.DBConnection:
        return lancedb.connect(self.uri)

    def get_table(self, memory_key: str) -> lancedb.table.Table:
        table_name = self.table_name.format(key=memory_key)
        db = self.get_db()
        model = self.get_model()
        try:
            return db.open_table(table_name)
        except FileNotFoundError:
            return db.create_table(table_name, schema=model)

    def add(self, memory_key: str, content: str) -> str:
        memory_id = str(uuid.uuid4())
        table = self.get_table(memory_key)
        table.add([{"id": memory_id, "text": content}])
        return memory_id

    def delete(self, memory_key: str, memory_id: str) -> None:
        table = self.get_table(memory_key)
        table.delete(f'id = "{memory_id}"')

    def search(self, memory_key: str, query: str, n: int = 20) -> dict[str, str]:
        table = self.get_table(memory_key)
        results = table.search(query).limit(n).to_pydantic(self.get_model())
        return {r.id: r.text for r in results}
