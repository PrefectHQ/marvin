import asyncio
import functools

import redis.asyncio as async_redis

import marvin

_client_cache: dict[tuple, async_redis.Redis] = {}


def _running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError as e:
        if "no running event loop" in str(e):
            return None
        raise


def cached(fn):
    @functools.wraps(fn)
    def cached_fn(*args, **kwargs):
        key = (fn, args, tuple(kwargs.items()), _running_loop())
        if key not in _client_cache:
            _client_cache[key] = fn(*args, **kwargs)
        return _client_cache[key]

    return cached_fn


@cached
def async_redis_from_settings(
    options: dict[str, str] = None,
) -> async_redis.Redis:
    return async_redis.Redis(**marvin.settings.redis.model_dump() | (options or {}))


@cached
async def get_async_redis_client() -> async_redis.Redis:
    return await async_redis_from_settings()
