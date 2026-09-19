"""Tests for running a coroutine synchronously."""

import asyncio
import threading

from marvin.utilities.asyncio import run_sync


def test_run_sync_without_an_event_loop() -> None:
    calls = []

    async def f(value: int) -> int:
        calls.append(value)
        return value + 1

    assert run_sync(f(1)) == 2
    assert calls == [1]


def test_run_sync_inside_a_running_loop() -> None:
    calls = []

    async def f(value: int) -> int:
        calls.append(value)
        return value + 1

    async def main() -> int:
        return run_sync(f(2))

    assert asyncio.run(main()) == 3
    assert calls == [2]


def test_run_sync_with_a_closed_event_loop() -> None:
    """A closed loop is replaced by a thread, it is not an error."""
    calls = []

    async def f(value: int) -> int:
        calls.append(value)
        return value + 1

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.close()
    try:
        assert run_sync(f(3)) == 4
    finally:
        asyncio.set_event_loop(None)
    assert calls == [3]


def test_run_sync_in_a_thread_without_an_event_loop() -> None:
    calls = []
    results: list[int] = []

    async def f(value: int) -> int:
        calls.append(value)
        return value + 1

    thread = threading.Thread(target=lambda: results.append(run_sync(f(4))))
    thread.start()
    thread.join()

    assert results == [5]
    assert calls == [4]


def test_run_sync_coroutine_runs_once() -> None:
    """The fallback path must not run the coroutine that already ran."""
    calls = []

    async def f() -> str:
        calls.append("run")
        return "done"

    async def main() -> str:
        return run_sync(f())

    assert asyncio.run(main()) == "done"
    assert calls == ["run"]
