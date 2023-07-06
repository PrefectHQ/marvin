import asyncio
import functools
from typing import TypeVar

T = TypeVar("T")


async def run_async(func, *args, **kwargs) -> T:
    async def wrapper() -> T:
        try:
            return await loop.run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )
        except Exception as e:
            # propagate the exception to the caller
            raise e

    loop = asyncio.get_event_loop()
    return await wrapper()
