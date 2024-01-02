from typing import Union

from pydantic import BaseModel

from marvin.beta.applications.state import State

try:
    from prefect.blocks.system import JSON
    from prefect.exceptions import ObjectNotFound
except ImportError:
    raise ModuleNotFoundError(
        "The `prefect` package is required to use the JSONBlockState class. You can"
        " install it with `pip install prefect` or `pip install marvin[prefect]`."
    )
from pydantic import Field, model_validator

from marvin.utilities.asyncio import run_sync, run_sync_if_awaitable


async def load_json_block(block_name: str) -> JSON:
    try:
        return await JSON.load(name=block_name)
    except Exception as exc:
        if "Unable to find block document" in str(exc):
            json_block = JSON(value={})
            await json_block.save(name=block_name)
            return json_block
        raise ObjectNotFound(f"Unable to load JSON block {block_name}") from exc


class JSONBlockState(State):
    block_name: str = Field(default="marvin-kv")

    @model_validator(mode="after")
    def get_state(self) -> "JSONBlockState":
        json_block = run_sync(load_json_block(self.block_name))
        self.value = json_block.value or {}

    def set_state(self, state: Union[BaseModel, dict]):
        super().set_state()
        json_block = run_sync(load_json_block(self.block_name))
        json_block.value = self.value
        run_sync_if_awaitable(json_block.save(name=self.block_name, overwrite=True))
