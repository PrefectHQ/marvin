from typing import Optional, TypeVar

from pydantic import Field

from marvin.kv.base import StorageInterface

T = TypeVar("T")


class InMemoryStorage(StorageInterface[T]):
    store: dict[str, T] = Field(default_factory=dict)

    def write(self, key: str, value: T) -> None:
        self.store[key] = value

    def read(self, key: str) -> Optional[T]:
        return self.store.get(key)

    def read_all(self) -> dict[str, T]:
        return self.store

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    def list_keys(self) -> list[str]:
        return list(self.store.keys())
