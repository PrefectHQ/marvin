from contextlib import contextmanager

import redis

import marvin


@contextmanager
def redis_client(**kwargs):
    print(marvin.settings.redis.model_dump())
    print(kwargs)
    client = redis.StrictRedis(**marvin.settings.redis.model_dump() | kwargs)
    yield client
    client.close()
