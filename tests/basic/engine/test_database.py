from marvin.engine.database import create_db_and_tables, get_async_session, get_session
from marvin.engine.models import DBMessage, DBThread
from sqlmodel import select


def test_sync_session():
    """Test that sync sessions are properly created and closed."""
    with get_session() as session:
        # Do some operation to ensure session works
        session.exec(select(DBThread)).all()
        assert session.is_active

    # After context exit, should not be able to execute queries
    try:
        session.exec(select(DBThread)).all()
        assert False, "Session should be closed"
    except Exception:
        assert True


async def test_async_session():
    """Test that async sessions are properly created and closed."""
    async with get_async_session() as session:
        # Do some operation to ensure session works
        await session.exec(select(DBThread))
        assert session.is_active

    # After context exit, should not be able to execute queries
    try:
        await session.exec(select(DBThread))
        assert False, "Session should be closed"
    except Exception:
        assert True


def test_force_recreate_tables():
    """Test that tables can be force recreated."""
    create_db_and_tables(force=True)

    # First phase: Create data
    with get_session() as session:
        thread = DBThread(id="test-thread")
        session.add(thread)
        session.commit()

        message = DBMessage(
            thread_id=thread.id,
            message={"role": "user", "content": "test", "kind": "request"},
        )
        session.add(message)
        session.commit()

    # Second phase: Verify data exists
    with get_session() as session:
        assert (
            session.exec(select(DBThread).where(DBThread.id == "test-thread")).first()
            is not None
        )
        assert (
            session.exec(
                select(DBMessage).where(DBMessage.thread_id == "test-thread")
            ).first()
            is not None
        )

    # Recreate tables
    create_db_and_tables(force=True)

    # Final phase: Verify data is gone
    with get_session() as session:
        assert (
            session.exec(select(DBThread).where(DBThread.id == "test-thread")).first()
            is None
        )
        assert (
            session.exec(
                select(DBMessage).where(DBMessage.thread_id == "test-thread")
            ).first()
            is None
        )


def test_relationship_operations():
    """Test database operations with relationships."""
    create_db_and_tables(force=True)

    with get_session() as session:
        # Create thread and messages
        thread = DBThread(id="test-thread")
        session.add(thread)
        session.commit()

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
        session.commit()

        # Test relationship loading
        loaded_thread = session.exec(
            select(DBThread).where(DBThread.id == "test-thread")
        ).one()
        assert len(loaded_thread.messages) == 2
        assert loaded_thread.messages[0].message["content"] == "test1"
        assert loaded_thread.messages[1].message["content"] == "test2"

        # Delete messages first
        for message in loaded_thread.messages:
            session.delete(message)
        session.commit()

        # Then delete thread
        session.delete(loaded_thread)
        session.commit()

        # Verify all gone
        assert (
            session.exec(
                select(DBMessage).where(DBMessage.thread_id == "test-thread")
            ).first()
            is None
        )
        assert (
            session.exec(select(DBThread).where(DBThread.id == "test-thread")).first()
            is None
        )
