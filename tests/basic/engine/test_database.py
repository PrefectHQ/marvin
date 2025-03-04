from pydantic_ai import BinaryContent
from pydantic_ai.messages import ModelRequest, UserPromptPart
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from marvin.database import (
    DBBinaryContent,
    DBMessage,
    DBThread,
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


async def test_binary_content_operations(session):
    """Test database operations with binary content."""
    # Create thread and message
    thread = DBThread(id="test-thread")
    session.add(thread)
    await session.commit()
    await session.refresh(thread)

    # Create a message with binary content
    test_data = b"test binary data"
    test_media_type = "audio/wav"

    # Create a user message with binary content
    user_message = ModelRequest(
        parts=[
            UserPromptPart(
                content=[
                    "Hello",
                    BinaryContent(data=test_data, media_type=test_media_type),
                ],
            )
        ]
    )

    # Convert to DB message
    db_message = DBMessage.from_message(thread_id=thread.id, message=user_message)
    session.add(db_message)
    await session.commit()
    await session.refresh(db_message, ["binary_contents"])

    # Verify binary content was stored
    assert len(db_message.binary_contents) == 1
    binary_content = db_message.binary_contents[0]
    assert binary_content.data == test_data
    assert binary_content.media_type == test_media_type
    assert binary_content.part_index == 0
    assert binary_content.content_index == 1

    # Test loading with relationships
    result = await session.execute(
        select(DBMessage)
        .where(DBMessage.thread_id == "test-thread")
        .options(selectinload(DBMessage.binary_contents))
    )
    loaded_message = result.scalar_one()
    assert len(loaded_message.binary_contents) == 1
    assert loaded_message.binary_contents[0].data == test_data

    # Test message conversion back to thread message
    thread_message = loaded_message.to_message()
    assert isinstance(thread_message.message, ModelRequest)
    assert len(thread_message.message.parts) == 1
    assert len(thread_message.message.parts[0].content) == 2
    assert thread_message.message.parts[0].content[0] == "Hello"
    assert isinstance(thread_message.message.parts[0].content[1], BinaryContent)
    assert thread_message.message.parts[0].content[1].data == test_data
    assert thread_message.message.parts[0].content[1].media_type == test_media_type

    # Test cascade delete
    await session.delete(loaded_message)
    await session.commit()

    # Verify binary content was deleted
    result = await session.execute(
        select(DBBinaryContent).where(DBBinaryContent.message_id == loaded_message.id)
    )
    assert result.scalars().first() is None
