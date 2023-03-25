import asyncio
import logging
import sys

import pytest

from .fixtures import *

# def pytest_collection_modifyitems(config, items):
#     if (
#         not marvin.settings.openai_api_key.get_secret_value()
#     ):
#         print("Skipping tests that require the OpenAI API key.")
#         skip_ai = pytest.mark.skip(reason="OpenAI API key is not set!")
#         for item in items:
#             for mark in item.iter_markers():
#                 if mark.name == "ai":
#                     item.add_marker(skip_ai)


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
        asyncio.run(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
