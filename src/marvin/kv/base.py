from abc import ABC, abstractmethod
from typing import Generic, List, Mapping, Optional, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type
R = TypeVar("R")  # Return type for write/delete operations
P = ParamSpec("P")  # Additional parameters


class StorageInterface(BaseModel, Generic[K, V, R], ABC):
    """An abstract key-value store interface.

    Example:
        ```python
        store = SomeStorageInterface()

        store.write("foo", "bar")
        store.write("baz", "qux")
        assert store.read("foo") == "bar"
        assert store.read_all() == {"foo": "bar", "baz": "qux"}
        assert store.list_keys() == ["foo", "baz"]
        store.delete("foo")
        assert store.read("foo") is None
        assert store.read_all() == {"baz": "qux"}
    """

    @abstractmethod
    def write(self, key: K, value: V, *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
        pass

    @abstractmethod
    def read(self, key: K, *args: P.args, **kwargs: P.kwargs) -> Optional[V]:
        pass

    @abstractmethod
    def read_all(self, *args: P.args, **kwargs: P.kwargs) -> Mapping[K, V]:
        pass

    @abstractmethod
    def delete(self, key: K, *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
        pass

    @abstractmethod
    def list_keys(self, *args: P.args, **kwargs: P.kwargs) -> List[K]:
        pass
