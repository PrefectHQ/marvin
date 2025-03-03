import pytest
from pydantic_ai import ImageUrl

from marvin import Thread
from marvin.agents.agent import Agent
from marvin.engine.orchestrator import Orchestrator
from marvin.tasks.task import Task
from marvin.thread import Message


@pytest.mark.asyncio
async def test_get_messages_empty_thread():
    """Test _get_messages with an empty thread."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == " "  # Default minimal prompt
    assert len(messages) == 1  # Only system message
    assert isinstance(messages[0], Message)


@pytest.mark.asyncio
async def test_get_messages_with_user_content():
    """Test _get_messages when there's a user message in the thread."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Add a user message to the thread
    await thread.add_user_message_async("Test user prompt")

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == "Test user prompt"
    assert len(messages) == 1  # Just the system message, user message was extracted
    assert isinstance(messages[0], Message)


@pytest.mark.asyncio
async def test_get_messages_with_multiple_messages():
    """Test _get_messages with multiple messages in history."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Add multiple messages to the thread
    await thread.add_user_message_async("First user message")
    await thread.add_agent_message_async("First AI message")
    await thread.add_user_message_async("Second user message")
    await thread.add_agent_message_async("Second AI message")
    await thread.add_user_message_async("Third user message")

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == "Third user message"

    # Check message count - should be 5 messages:
    # 1 new system message + 4 original messages (minus the last user message)
    assert len(messages) == 5

    # Verify content
    system_message = messages[0]
    assert isinstance(system_message, Message)


@pytest.mark.asyncio
async def test_get_messages_with_non_user_last_message():
    """Test _get_messages when the last message is not a user message."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Add messages with AI message at the end
    await thread.add_user_message_async("First user message")
    await thread.add_agent_message_async("First AI message")
    await thread.add_user_message_async("Second user message")
    await thread.add_agent_message_async("Second AI message")

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == " "  # Default minimal prompt

    # Should have 5 messages:
    # 1 new system message + 4 original messages
    assert len(messages) == 5


@pytest.mark.asyncio
async def test_get_messages_with_multiple_tasks():
    """Test _get_messages with multiple tasks."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task1 = Task("First task")
    task2 = Task("Second task")
    tasks = [task1, task2]

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == " "  # Default minimal prompt
    assert len(messages) == 1  # Only system message


@pytest.mark.asyncio
async def test_get_messages_extracts_user_prompt_correctly():
    """Test that _get_messages correctly extracts the user prompt."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Add a series of messages and ensure the last one is extracted
    await thread.add_user_message_async("First message")
    await thread.add_agent_message_async("First response")
    await thread.add_user_message_async("Second message")
    await thread.add_agent_message_async("Second response")
    await thread.add_user_message_async("Latest user prompt")

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == "Latest user prompt"

    # Should have 5 messages:
    # 1 new system message + 4 original messages (minus the last user message)
    assert len(messages) == 5

    # Verify each message is included except the last user message
    message_kinds = [msg.message.kind for msg in messages[1:]]
    assert message_kinds == ["request", "response", "request", "response"]


@pytest.mark.asyncio
async def test_get_messages_ignores_previous_system_messages():
    """Test that _get_messages ignores previous system messages from the history."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Add system messages and other messages to the thread
    await thread.add_system_message_async("First system message to ignore")
    await thread.add_user_message_async("User message")
    await thread.add_agent_message_async("AI response")
    await thread.add_system_message_async("Second system message to ignore")
    await thread.add_user_message_async("Final user message")

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    assert user_prompt == "Final user message"

    # The returned messages should only contain one system message (the new one)
    # and ignore all previous system messages from the history
    system_messages = [
        msg for msg in messages if msg.message.parts[0].part_kind == "system-prompt"
    ]
    assert len(system_messages) == 1

    # Verify the content of non-system messages
    non_system_messages = [
        msg for msg in messages if msg.message.parts[0].part_kind != "system-prompt"
    ]
    assert len(non_system_messages) == 2  # User message and AI response

    # Verify the content of these messages
    assert non_system_messages[0].message.parts[0].content == "User message"
    assert non_system_messages[1].message.parts[0].content == "AI response"


@pytest.mark.asyncio
async def test_get_messages_with_complex_user_prompt():
    """Test _get_messages handling a user message with text and ImageUrl."""
    # Create objects directly in the test
    thread = Thread()
    actor = Agent()
    orchestrator = Orchestrator(tasks=[], thread=thread)
    task = Task("Test task")
    tasks = [task]

    # Create a complex user message with text and ImageUrl
    text_and_image = [
        "Describe this image:",
        ImageUrl(url="https://example.com/image.jpg"),
    ]

    # Add messages to the thread, ending with the complex user message
    await thread.add_user_message_async("Previous message")
    await thread.add_agent_message_async("Previous response")
    await thread.add_user_message_async(text_and_image)

    # Call the method
    user_prompt, messages = await orchestrator._get_messages(actor, tasks)

    # Assertions
    # The entire complex message should be returned as the user prompt
    assert user_prompt == text_and_image

    # There should be system message + 2 previous messages (the complex one was extracted)
    assert len(messages) == 3
