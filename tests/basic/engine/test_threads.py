"""Tests for thread functionality and message handling."""

from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart

from marvin.engine.llm import AgentMessage, SystemMessage, UserMessage
from marvin.thread import Thread


def test_basic_message_handling():
    """Test basic message operations with new message types."""
    thread = Thread()

    # Test user message
    user_msg = UserMessage("Hello")
    thread.add_messages([user_msg])
    messages = thread.get_messages()

    assert len(messages) == 1
    assert isinstance(messages[0], ModelRequest)
    assert len(messages[0].parts) == 1
    assert isinstance(messages[0].parts[0], UserPromptPart)
    assert messages[0].parts[0].content == "Hello"


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

    assert len(messages) == 5
    # Verify alternating message types
    assert isinstance(messages[0], ModelRequest)  # System
    assert isinstance(messages[1], ModelRequest)  # User
    assert isinstance(messages[2], ModelResponse)  # Agent
    assert isinstance(messages[3], ModelRequest)  # User
    assert isinstance(messages[4], ModelResponse)  # Agent


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
    assert isinstance(loaded_messages[0], ModelRequest)
    assert isinstance(loaded_messages[1], ModelResponse)
    assert loaded_messages[0].parts[0].content == "Save this message"
    assert loaded_messages[1].parts[0].content == "Message saved"


def test_thread_messages():
    thread = Thread()
    user_msg = UserMessage(content="Hello")

    thread.add_messages([user_msg])
    messages = thread.get_messages()

    assert len(messages) == 1
    assert messages[0].parts[0].content == "Hello"
