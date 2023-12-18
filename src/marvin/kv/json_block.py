from typing import Optional, TypeVar

try:
    from prefect.blocks.system import JSON
    from prefect.exceptions import ObjectNotFound
except ImportError:
    raise ModuleNotFoundError(
        "The `prefect` package is required to use the JSONBlockKV class."
        " You can install it with `pip install prefect` or `pip install marvin[prefect]`."
    )
from pydantic import Field

from marvin.kv.base import StorageInterface
from marvin.utilities.asyncio import run_sync

K = TypeVar("K", bound=str)
V = TypeVar("V")


class JSONBlockKV(StorageInterface[K, V, str]):
    """
    A key-value store that uses Prefect's JSON blocks under the hood.
    """

    block_name: str = Field(default="marvin-kv")

    async def _load_json_block(self) -> JSON:
        try:
            return await JSON.load(name=self.block_name)
        except Exception as exc:
            if "Unable to find block document" in str(exc):
                json_block = JSON(value={})
                await json_block.save(name=self.block_name)
                return json_block
            raise ObjectNotFound(
                f"Unable to load JSON block {self.block_name}"
            ) from exc

    def write(self, key: K, value: V) -> str:
        json_block = run_sync(self._load_json_block())
        json_block.value[key] = value
        run_sync(json_block.save(name=self.block_name, overwrite=True))
        return f"Stored {key}= {value}"

    def delete(self, key: K) -> str:
        json_block = run_sync(self._load_json_block())
        if key in json_block.value:
            del json_block.value[key]
            run_sync(json_block.save(name=self.block_name, overwrite=True))
        return f"Deleted {key}"

    def read(self, key: K) -> Optional[V]:
        json_block = run_sync(self._load_json_block())
        return json_block.value.get(key)

    def read_all(self, limit: Optional[int] = None) -> dict[K, V]:
        json_block = run_sync(self._load_json_block())
        return dict(list(json_block.value.items())[:limit])

    def list_keys(self) -> list[K]:
        json_block = run_sync(self._load_json_block())
        return list(json_block.value.keys())
