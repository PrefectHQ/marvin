import asyncio
import concurrent.futures
import functools
import multiprocessing as mp
import platform

import cloudpickle

import marvin

if platform.system() == "Windows":
    mp_context = "spawn"
else:
    mp_context = "fork"

process_pool = concurrent.futures.ProcessPoolExecutor(
    mp_context=mp.get_context(mp_context)
)

BACKGROUND_TASKS = set()


def create_task(coro):
    """
    Creates background tasks in a way that is safe.

    See https://textual.textualize.io/blog/2023/02/11/the-heisenbug-lurking-in-your-async-code/
    """  # noqa: E501
    task = asyncio.create_task(coro)
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    return task


async def run_async(func, *args, **kwargs):
    async def wrapper():
        try:
            return await loop.run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )
        except Exception as e:
            # propagate the exception to the caller
            raise e

    loop = asyncio.get_event_loop()
    return await wrapper()


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


def retry_async(max_retries=3, sleep_between_retries=1, exceptions=None):
    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for retry_count in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if retry_count < max_retries - 1:
                        await asyncio.sleep(sleep_between_retries)
                    else:
                        raise e

        return wrapper

    return decorator
