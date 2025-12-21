import asyncio
import threading

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from marvin.database import (
    DBMessage,
    DBThread,
    _async_engine_cache,
    create_db_and_tables,
)


async def test_async_session(session):
    """Test that async sessions are properly created and closed."""
    # Do some operation to ensure session works
    result = await session.execute(select(DBThread))
    result.all()  # Explicitly consume the result
    assert session.is_active


async def test_force_recreate_tables(session):
    """Test that tables can be force recreated."""
    # First phase: Create data
    thread = DBThread(id="test-thread")
    session.add(thread)
    await session.commit()
    await session.refresh(thread)

    message = DBMessage(
        thread_id=thread.id,
        message={"role": "user", "content": "test", "kind": "request"},
    )
    session.add(message)
    await session.commit()

    # Second phase: Verify data exists
    result = await session.execute(select(DBThread).where(DBThread.id == "test-thread"))
    assert result.scalars().first() is not None

    result = await session.execute(
        select(DBMessage).where(DBMessage.thread_id == "test-thread"),
    )
    assert result.scalars().first() is not None

    # Recreate tables
    await create_db_and_tables(force=True)

    # Final phase: Verify data is gone
    result = await session.execute(select(DBThread).where(DBThread.id == "test-thread"))
    assert result.scalars().first() is None

    result = await session.execute(
        select(DBMessage).where(DBMessage.thread_id == "test-thread"),
    )
    assert result.scalars().first() is None


async def test_relationship_operations(session):
    """Test database operations with relationships."""
    # Create thread and messages
    thread = DBThread(id="test-thread")
    session.add(thread)
    await session.commit()
    await session.refresh(thread)

    message1 = DBMessage(
        thread_id=thread.id,
        message={"role": "user", "content": "test1", "kind": "request"},
    )
    message2 = DBMessage(
        thread_id=thread.id,
        message={"role": "assistant", "content": "test2", "kind": "response"},
    )
    session.add(message1)
    session.add(message2)
    await session.commit()

    # Test relationship loading
    result = await session.execute(
        select(DBThread)
        .where(DBThread.id == "test-thread")
        .options(selectinload(DBThread.messages))
    )
    loaded_thread = result.scalar_one()
    assert len(loaded_thread.messages) == 2
    assert {
        loaded_thread.messages[0].message["content"],
        loaded_thread.messages[1].message["content"],
    } == {"test1", "test2"}

    # Delete messages first
    for message in loaded_thread.messages:
        await session.delete(message)
    await session.commit()
    await session.refresh(loaded_thread)

    # Then delete thread
    await session.delete(loaded_thread)
    await session.commit()

    # Verify all gone
    result = await session.execute(
        select(DBMessage).where(DBMessage.thread_id == "test-thread"),
    )
    assert result.scalars().first() is None

    result = await session.execute(select(DBThread).where(DBThread.id == "test-thread"))
    assert result.scalars().first() is None


def test_create_db_and_tables_with_dispose_cleans_up_engine():
    """Test that create_db_and_tables with dispose_engine=True cleans up resources.

    Regression test for issue #1255: process hangs on exit after importing marvin.

    When create_db_and_tables is called with dispose_engine=True (as it is from
    ensure_db_tables_exist), the engine should be disposed and removed from
    the cache. This ensures the aiosqlite worker thread is cleaned up and
    doesn't prevent Python from exiting.
    """

    def get_non_daemon_threads():
        """Return non-daemon threads excluding the main thread."""
        return [
            t
            for t in threading.enumerate()
            if t is not threading.main_thread() and not t.daemon
        ]

    # record initial state
    initial_cache_size = len(_async_engine_cache)
    initial_threads = len(get_non_daemon_threads())

    # run create_db_and_tables with dispose_engine=True
    asyncio.run(create_db_and_tables(dispose_engine=True))

    # verify engine was removed from cache
    assert len(_async_engine_cache) == initial_cache_size

    # verify no new non-daemon threads were left behind
    current_threads = get_non_daemon_threads()
    assert len(current_threads) == initial_threads, (
        f"expected {initial_threads} non-daemon threads, "
        f"found {len(current_threads)}: {[t.name for t in current_threads]}"
    )
