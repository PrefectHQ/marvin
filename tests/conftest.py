import asyncio
import logging
import os
import sys

import pytest

from .fixtures import *


@pytest.fixture(scope="session")
def event_loop(request):
    """
    Redefine the event loop to support session/module-scoped fixtures;
    see https://github.com/pytest-dev/pytest-asyncio/issues/68

    When running on Windows we need to use a non-default loop for subprocess support.
    """
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    policy = asyncio.get_event_loop_policy()

    loop: asyncio.BaseEventLoop = policy.new_event_loop()

    # configure asyncio logging to capture long running tasks
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.setLevel("WARNING")
    asyncio_logger.addHandler(logging.StreamHandler())
    loop.set_debug(True)
    loop.slow_callback_duration = 0.25

    try:
        yield loop
    finally:
        # ensure all background tasks are cancelled and awaited to avoid
        # spurious warnings / errors about "task destroyed but it is pending"
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        if tasks and loop.is_running():
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()


class SetEnv:
    def __init__(self):
        self.envars = set()

    def set(self, name, value):
        self.envars.add(name)
        os.environ[name] = value

    def pop(self, name):
        self.envars.remove(name)
        os.environ.pop(name)

    def clear(self):
        for n in self.envars:
            os.environ.pop(n)


@pytest.fixture
def env():
    setenv = SetEnv()

    yield setenv

    setenv.clear()


@pytest.fixture
def docs_test_env():
    setenv = SetEnv()

    # # envs for basic usage example
    # setenv.set('my_auth_key', 'xxx')
    # setenv.set('my_api_key', 'xxx')

    # envs for parsing environment variable values example
    setenv.set("V0", "0")
    setenv.set("SUB_MODEL", '{"v1": "json-1", "v2": "json-2"}')
    setenv.set("SUB_MODEL__V2", "nested-2")
    setenv.set("SUB_MODEL__V3", "3")
    setenv.set("SUB_MODEL__DEEP__V4", "v4")

    yield setenv

    setenv.clear()
