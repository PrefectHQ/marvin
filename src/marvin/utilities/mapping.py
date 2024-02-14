"""Utilities for mapping."""

import asyncio
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


async def map_async(
    fn: Callable[..., Coroutine[Any, Any, T]],
    map_args: tuple = None,
    map_kwargs: dict = None,
    unmapped_kwargs: dict = None,
):
    """
    Asynchronously maps a function over a list of arguments.

    This function takes a function and multiple lists of arguments, and applies
    the function to each combination of arguments. The function is applied
    concurrently to each combination of arguments using asyncio's gather
    function.

    Args:
        fn (Callable[..., Coroutine[Any, Any, T]]): The async function to map.
        map_args (list, optional): A list of lists, where each inner list
            contains positional arguments to map over.
        unmapped_kwargs (dict, optional): A dictionary of arguments to pass to
            the function as is.
        map_kwargs (dict, optional): A dictionary where each key-value pair
            represents the keyword arguments to map over.

    Returns:
        A list of return values from the function, gathered using asyncio.gather.

    Example:
        Basic usage:
        async def add(x, y):
            return x + y

        result = await map_async(add, map_args=[[1, 2, 3], [4, 5, 6]])
        # result is [5, 7, 9]
    """
    if map_args is None:
        map_args = []
    if map_kwargs is None:
        map_kwargs = {}
    if unmapped_kwargs is None:
        unmapped_kwargs = {}

    tasks = []
    if map_args:
        max_length = max(len(arg) for arg in map_args)
    else:
        max_length = max(len(v) for v in map_kwargs.values())

    for i in range(max_length):
        call_args = [arg[i] if i < len(arg) else None for arg in map_args]
        call_kwargs = (
            {k: v[i] if i < len(v) else None for k, v in map_kwargs.items()}
            if map_kwargs
            else {}
        )
        tasks.append(fn(*call_args, **call_kwargs, **unmapped_kwargs))

    return await asyncio.gather(*tasks)
