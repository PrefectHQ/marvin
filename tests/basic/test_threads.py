"""
Tests for thread functionality and message handling.
"""

from marvin.engine.llm import AgentMessage, SystemMessage, UserMessage
from marvin.engine.thread import Thread
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart


async def test_basic_message_handling():
    """Test basic message operations with new message types."""
    thread = Thread()

    # Test user message
    user_msg = UserMessage("Hello")
    await thread.add_messages([user_msg])
    messages = await thread.get_messages()

    assert len(messages) == 1
    assert isinstance(messages[0], ModelRequest)
    assert len(messages[0].parts) == 1
    assert isinstance(messages[0].parts[0], UserPromptPart)
    assert messages[0].parts[0].content == "Hello"


async def test_conversation_flow():
    """Test a complete conversation flow with different message types."""
    thread = Thread()

    conversation = [
        SystemMessage("You are a helpful assistant"),
        UserMessage("Hi there"),
        AgentMessage("Hello! How can I help?"),
        UserMessage("What's the weather?"),
        AgentMessage("I don't have access to weather data"),
    ]

    await thread.add_messages(conversation)
    messages = await thread.get_messages()

    assert len(messages) == 5
    # Verify alternating message types
    assert isinstance(messages[0], ModelRequest)  # System
    assert isinstance(messages[1], ModelRequest)  # User
    assert isinstance(messages[2], ModelResponse)  # Agent
    assert isinstance(messages[3], ModelRequest)  # User
    assert isinstance(messages[4], ModelResponse)  # Agent


async def test_thread_persistence():
    """Test thread persistence with new message structures."""
    # Create and populate first thread
    thread1 = Thread()
    messages = [
        UserMessage("Save this message"),
        AgentMessage("Message saved"),
    ]
    await thread1.add_messages(messages)

    # Create new thread instance with same ID
    thread2 = Thread(id=thread1.id)
    loaded_messages = await thread2.get_messages()

    assert len(loaded_messages) == 2
    assert isinstance(loaded_messages[0], ModelRequest)
    assert isinstance(loaded_messages[1], ModelResponse)
    assert loaded_messages[0].parts[0].content == "Save this message"
    assert loaded_messages[1].parts[0].content == "Message saved"


async def test_thread_inheritance():
    """Test thread branching with new message types."""
    # Parent thread
    parent = Thread()
    await parent.add_messages(
        [
            UserMessage("Parent message"),
            AgentMessage("Parent response"),
        ]
    )

    # Child thread
    child = Thread(parent_id=parent.id)
    await child.add_messages([UserMessage("Child message")])

    # Verify inheritance
    child_messages = await child.get_messages()
    assert len(child_messages) == 3
    assert child_messages[0].parts[0].content == "Parent message"
    assert child_messages[1].parts[0].content == "Parent response"
    assert child_messages[2].parts[0].content == "Child message"

    # Verify parent remains unchanged
    parent_messages = await parent.get_messages()
    assert len(parent_messages) == 2

    # Test sibling isolation
    sibling = Thread(parent_id=parent.id)
    await sibling.add_messages([UserMessage("Sibling message")])

    child_messages = await child.get_messages()
    sibling_messages = await sibling.get_messages()

    assert len(child_messages) == 3
    assert len(sibling_messages) == 3
    assert child_messages[-1].parts[0].content == "Child message"
    assert sibling_messages[-1].parts[0].content == "Sibling message"
