import json
import os
import pickle
from pathlib import Path
from typing import Optional, TypeVar, Union

from pydantic import Field, field_validator
from typing_extensions import Literal

from marvin.kv.base import StorageInterface

K = TypeVar("K", bound=str)
V = TypeVar("V")


class DiskKV(StorageInterface[K, V, str]):
    """
    A key-value store that stores values on disk.

    Example:
        ```python
        from marvin.kv.disk_based import DiskBasedKV
        store = DiskBasedKV(storage_path="/path/to/storage")
        store.write("key", "value")
        assert store.read("key") == "value"
        ```
    """

    storage_path: Path = Field(...)
    serializer: Literal["json", "pickle"] = Field("json")

    @field_validator("storage_path")
    def _validate_storage_path(cls, v: Union[str, Path]) -> Path:
        expanded_path = Path(v).expanduser().resolve()
        if not expanded_path.exists():
            expanded_path.mkdir(parents=True, exist_ok=True)
        return expanded_path

    def _get_file_path(self, key: K) -> Path:
        file_extension = ".json" if self.serializer == "json" else ".pkl"
        return self.storage_path / f"{key}{file_extension}"

    def _serialize(self, value: V) -> bytes:
        if self.serializer == "json":
            return json.dumps(value).encode()
        else:
            return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> V:
        if self.serializer == "json":
            return json.loads(data)
        else:
            return pickle.loads(data)

    def write(self, key: K, value: V) -> str:
        file_path = self._get_file_path(key)
        serialized_value = self._serialize(value)
        with open(file_path, "wb") as file:
            file.write(serialized_value)
        return f"Stored {key}= {value}"

    def delete(self, key: K) -> str:
        file_path = self._get_file_path(key)
        try:
            os.remove(file_path)
            return f"Deleted {key}"
        except FileNotFoundError:
            return f"Key {key} not found"

    def read(self, key: K) -> Optional[V]:
        file_path = self._get_file_path(key)
        try:
            with open(file_path, "rb") as file:
                serialized_value = file.read()
                return self._deserialize(serialized_value)
        except FileNotFoundError:
            return None

    def read_all(self, limit: Optional[int] = None) -> dict[K, V]:
        files = os.listdir(self.storage_path)[:limit]
        return {file.split(".")[0]: self.read(file.split(".")[0]) for file in files}

    def list_keys(self) -> list[K]:
        return [file.split(".")[0] for file in os.listdir(self.storage_path)]
