from typing import Optional, TypeVar

from pydantic import Field

from marvin.kv.base import StorageInterface

K = TypeVar("K", bound=str)
V = TypeVar("V")


class InMemoryKV(StorageInterface[K, V, str]):
    """An in-memory key-value store.

    Example:
        ```python
        from marvin.kv.in_memory import InMemoryKV
        store = InMemoryKV()
        store.write("key", "value")
        assert store.read("key") == "value"
        ```
    """

    store: dict[K, V] = Field(default_factory=dict)

    def write(self, key: K, value: V) -> str:
        self.store[key] = value
        return f"Stored {key}= {value}"

    def delete(self, key: K) -> str:
        v = self.store.pop(key, None)
        return f"Deleted {key}= {v}"

    def read(self, key: K) -> Optional[V]:
        return self.store.get(key)

    def read_all(self, limit: Optional[int] = None) -> dict[K, V]:
        if limit is None:
            return self.store
        return dict(list(self.store.items())[:limit])

    def list_keys(self) -> list[K]:
        return list(self.store.keys())
