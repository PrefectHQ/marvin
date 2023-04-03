import asyncio
import concurrent.futures
import functools
import multiprocessing as mp

import cloudpickle

import marvin

process_pool = concurrent.futures.ProcessPoolExecutor(mp_context=mp.get_context("fork"))


async def run_async(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _cloudpickle_wrapper(pickle):
    return cloudpickle.loads(pickle)()


async def run_async_process(func, *args, **kwargs):
    # in test mode, don't spawn processes
    if marvin.settings.test_mode:
        return await run_async(func, *args, **kwargs)

    pickled_func = cloudpickle.dumps(functools.partial(func, *args, **kwargs))
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(process_pool, _cloudpickle_wrapper, pickled_func)


def as_sync_fn(fn):
    """
    Wraps an async function and returns a sync function that runs it in an executor.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapper
