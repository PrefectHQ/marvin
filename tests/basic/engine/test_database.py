from sqlalchemy import select
from sqlalchemy.orm import selectinload

from marvin.database import (
    DBMessage,
    DBThread,
    create_db_and_tables,
)


def test_sync_session(session_sync):
    """Test that sync sessions are properly created and closed."""
    # Do some operation to ensure session works
    result = session_sync.execute(select(DBThread))
    result.all()  # Explicitly consume the result
    assert session_sync.is_active


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
    create_db_and_tables(force=True)

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
    assert loaded_thread.messages[0].message["content"] == "test1"
    assert loaded_thread.messages[1].message["content"] == "test2"

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
