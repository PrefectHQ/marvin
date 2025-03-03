import uuid

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart

from marvin.engine.llm import AgentMessage, SystemMessage, UserMessage
from marvin.thread import Message, Thread


def test_basic_message_handling():
    """Test basic message operations with new message types."""
    thread = Thread()

    # Test user message
    user_msg = UserMessage("Hello")
    thread.add_messages([user_msg])
    messages = thread.get_messages()

    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert isinstance(messages[0].message, ModelRequest)
    assert len(messages[0].message.parts) == 1
    assert isinstance(messages[0].message.parts[0], UserPromptPart)
    assert messages[0].message.parts[0].content == "Hello"


def test_get_messages_doesnt_include_system_messages():
    thread = Thread()
    thread.add_messages([SystemMessage("You are a helpful assistant")])
    messages = thread.get_messages()
    assert len(messages) == 0

    all_messages = thread.get_messages(include_system_messages=True)
    assert len(all_messages) == 1
    assert isinstance(all_messages[0], Message)
    assert isinstance(all_messages[0].message, ModelRequest)
    assert all_messages[0].message.parts[0].content == "You are a helpful assistant"


def test_conversation_flow():
    """Test a complete conversation flow with different message types."""
    thread = Thread()

    conversation = [
        SystemMessage("You are a helpful assistant"),
        UserMessage("Hi there"),
        AgentMessage("Hello! How can I help?"),
        UserMessage("What's the weather?"),
        AgentMessage("I don't have access to weather data"),
    ]

    thread.add_messages(conversation)
    messages = thread.get_messages()
    all_messages = thread.get_messages(include_system_messages=True)

    assert len(messages) == 4
    assert len(all_messages) == 5
    assert messages == all_messages[1:]

    # Verify alternating message types
    assert isinstance(all_messages[0].message, ModelRequest)  # System
    assert isinstance(all_messages[1].message, ModelRequest)  # User
    assert isinstance(all_messages[2].message, ModelResponse)  # Agent
    assert isinstance(all_messages[3].message, ModelRequest)  # User
    assert isinstance(all_messages[4].message, ModelResponse)  # Agent


def test_thread_persistence():
    """Test thread persistence with new message structures."""
    # Create and populate first thread
    thread1 = Thread()
    messages = [
        UserMessage("Save this message"),
        AgentMessage("Message saved"),
    ]
    thread1.add_messages(messages)

    # Create new thread instance with same ID
    thread2 = Thread(id=thread1.id)
    loaded_messages = thread2.get_messages()

    assert len(loaded_messages) == 2
    assert isinstance(loaded_messages[0].message, ModelRequest)
    assert isinstance(loaded_messages[1].message, ModelResponse)
    assert loaded_messages[0].message.parts[0].content == "Save this message"
    assert loaded_messages[1].message.parts[0].content == "Message saved"


def test_thread_messages():
    thread = Thread()
    user_msg = UserMessage(content="Hello")

    thread.add_messages([user_msg])
    messages = thread.get_messages()

    assert len(messages) == 1
    assert messages[0].message.parts[0].content == "Hello"


def test_uuid_thread_id():
    with pytest.raises(ValueError):
        Thread(id=uuid.uuid4())
