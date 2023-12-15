from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class StorageInterface(BaseModel, Generic[T], ABC):
    @abstractmethod
    def write(self, key: str, value: T) -> None:
        pass

    @abstractmethod
    def read(self, key: str) -> Optional[T]:
        pass

    @abstractmethod
    def read_all(self) -> dict[str, T]:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        pass
