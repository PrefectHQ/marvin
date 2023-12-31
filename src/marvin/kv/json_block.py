from typing import Mapping, Optional, TypeVar

try:
    from prefect.blocks.system import JSON
    from prefect.exceptions import ObjectNotFound
except ImportError:
    raise ModuleNotFoundError(
        "The `prefect` package is required to use the JSONBlockKV class."
        " You can install it with `pip install prefect` or `pip install marvin[prefect]`."
    )
from pydantic import Field, PrivateAttr, model_validator

from marvin.kv.base import StorageInterface
from marvin.utilities.asyncio import run_sync, run_sync_if_awaitable

K = TypeVar("K", bound=str)
V = TypeVar("V")


async def load_json_block(block_name: str) -> JSON:
    try:
        return await JSON.load(name=block_name)
    except Exception as exc:
        if "Unable to find block document" in str(exc):
            json_block = JSON(value={})
            await json_block.save(name=block_name)
            return json_block
        raise ObjectNotFound(f"Unable to load JSON block {block_name}") from exc


class JSONBlockKV(StorageInterface):
    block_name: str = Field(default="marvin-kv")
    _state: dict[K, Mapping] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def load_state(self) -> "JSONBlockKV":
        json_block = run_sync(load_json_block(self.block_name))
        self._state = json_block.value or {}
        return self

    def write(self, key: K, value: V) -> str:
        self._state[key] = value
        json_block = run_sync(load_json_block(self.block_name))
        json_block.value = self._state
        run_sync_if_awaitable(json_block.save(name=self.block_name, overwrite=True))
        return f"Stored {key}= {value}"

    def delete(self, key: K) -> str:
        if key in self._state:
            self._state.pop(key, None)
        json_block = run_sync(load_json_block(self.block_name))
        if key in json_block.value:
            json_block.value = self._state
            run_sync_if_awaitable(json_block.save(name=self.block_name, overwrite=True))
        return f"Deleted {key}"

    def read(self, key: K) -> Optional[V]:
        json_block = run_sync(load_json_block(self.block_name))
        return json_block.value.get(key)

    def read_all(self, limit: Optional[int] = None) -> dict[K, V]:
        json_block = run_sync(load_json_block(self.block_name))

        limited_items = dict(list(json_block.value.items())[:limit])
        return limited_items

    def list_keys(self) -> list[K]:
        json_block = run_sync(load_json_block(self.block_name))
        return list(json_block.value.keys())
