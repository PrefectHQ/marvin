import pytest
from dirty_equals import IsStr

import marvin
from marvin import Thread
from marvin.agents.actor import get_current_actor
from marvin.agents.agent import Agent
from marvin.memory.memory import Memory


async def test_agent_initialization():
    """Test basic agent initialization."""
    agent = Agent(name="Test Agent")
    assert agent.name == "Test Agent"
    assert agent.tools == []
    assert agent.memories == []
    assert agent.model is None
    assert agent.model_settings == {}
    assert agent.verbose is False


async def test_agent_with_custom_name():
    """Test agent with custom name."""
    agent = Agent(name="Custom Agent")
    assert agent.name == "Custom Agent"
    assert agent.friendly_name() == f'Agent "Custom Agent" ({agent.id})'
    assert agent.friendly_name(verbose=False) == "Custom Agent"


async def test_agent_with_tools():
    """Test agent with custom tools."""

    def my_tool():
        pass

    agent = Agent(name="Tool Agent", tools=[my_tool])
    assert len(agent.tools) == 1
    assert agent.tools[0] is my_tool
    assert agent.get_tools() == [my_tool]


async def test_agent_with_memories():
    """Test agent with memories."""
    memory = Memory(key="test_memory")
    agent = Agent(name="Memory Agent", memories=[memory])
    assert len(agent.memories) == 1
    assert agent.memories[0] == memory
    assert agent.get_memories() == [memory]


async def test_agent_with_model():
    """Test agent with custom model."""
    agent = Agent(name="Model Agent", model="openai:gpt-4")
    assert agent.model == "openai:gpt-4"
    assert agent.get_model() == "openai:gpt-4"


async def test_agent_with_model_settings():
    """Test agent with custom model settings."""
    agent = Agent(name="Settings Agent", model_settings={"temperature": 0.7})
    assert agent.model_settings == {"temperature": 0.7}
    assert agent.get_model_settings() == {"temperature": 0.7}


async def test_agent_get_default_model():
    """Test getting default model when none specified."""
    agent = Agent(name="Default Model Agent")
    assert agent.model is None
    assert agent.get_model() is marvin.defaults.model


async def test_agent_context_management():
    """Test agent context management."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")

    # Outside context - no current agent
    assert get_current_actor() is None

    # Inside context - agent1 is current
    with agent1:
        assert get_current_actor() is agent1

        # Nested context - agent2 is current
        with agent2:
            assert get_current_actor() is agent2

        # Back to agent1
        assert get_current_actor() is agent1

    # Outside context - no current agent
    assert get_current_actor() is None


async def test_agent_context_with_different_agent_types():
    """Test agent context with different agent types."""
    # Create agents with different tools and settings
    tool_agent = Agent(name="Tool Agent")
    memory_agent = Agent(name="Memory Agent")
    model_agent = Agent(name="Model Agent")

    # Verify that context works correctly with different agent types
    with tool_agent:
        assert get_current_actor() is tool_agent

        with memory_agent:
            assert get_current_actor() is memory_agent

            with model_agent:
                assert get_current_actor() is model_agent

            # Back to memory_agent
            assert get_current_actor() is memory_agent

        # Back to tool_agent
        assert get_current_actor() is tool_agent

    # Outside context
    assert get_current_actor() is None


async def test_agent_context_after_exception():
    """Test that agent context is properly reset after an exception."""
    agent = Agent(name="Test Agent")

    try:
        with agent:
            assert get_current_actor() is agent
            raise ValueError("Test exception")
    except ValueError:
        # Context should be reset even after exception
        assert get_current_actor() is None


async def test_setting_agent_via_context():
    """Test getting the agent set from a context."""
    agent = Agent(name="Context Agent")

    # Before context
    assert get_current_actor() is None

    # Set agent via context
    with agent:
        # get_current_actor() should return the agent
        assert get_current_actor() is agent

    # After context
    assert get_current_actor() is None


class TestVerbose:
    @pytest.fixture
    def thread(self) -> marvin.Thread:
        return marvin.Thread()

    async def test_create_verbose_agent(self, thread: Thread):
        """Test that agents can be created with verbose=True."""
        agent = Agent(name="Verbose Agent", verbose=True)
        assert agent.verbose

    async def test_verbose_agent_start_turn(self, thread: Thread):
        """Test that verbose agents add a message to the thread when starting a turn."""
        agent = Agent(name="Verbose Agent", verbose=True)
        await agent.start_turn(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has started its turn\.$"
        )

    async def test_verbose_agent_start_turn_context_thread(self, thread: Thread):
        """Test that verbose agents use the context thread when starting a turn."""
        agent = Agent(name="Verbose Agent", verbose=True)
        with thread:
            await agent.start_turn(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has started its turn\.$"
        )

    async def test_non_verbose_agent_start_turn(self, thread: Thread):
        """Test that non-verbose agents don't add messages when starting a turn."""
        agent = Agent(name="Non-Verbose Agent", verbose=False)
        await agent.start_turn(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 0

    async def test_verbose_agent_end_turn(self, thread: Thread):
        """Test that verbose agents add a message to the thread when ending a turn."""
        agent = Agent(name="Verbose Agent", verbose=True)
        # Create a mock AgentRunResult
        result = type("AgentRunResult", (), {})()
        await agent.end_turn(thread=thread, result=result)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has finished its turn\.$"
        )

    async def test_verbose_agent_end_turn_context_thread(self, thread: Thread):
        """Test that verbose agents use the context thread when ending a turn."""
        agent = Agent(name="Verbose Agent", verbose=True)
        # Create a mock AgentRunResult
        result = type("AgentRunResult", (), {})()
        with thread:
            await agent.end_turn(thread=thread, result=result)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^ACTOR UPDATE: .* has finished its turn\.$"
        )

    async def test_non_verbose_agent_end_turn(self, thread: Thread):
        """Test that non-verbose agents don't add messages when ending a turn."""
        agent = Agent(name="Non-Verbose Agent", verbose=False)
        # Create a mock AgentRunResult
        result = type("AgentRunResult", (), {})()
        await agent.end_turn(thread=thread, result=result)
        messages = await thread.get_messages_async()
        assert len(messages) == 0


async def test_agent_prompt():
    """Test agent prompt generation."""
    agent = Agent(name="Prompt Agent")
    prompt = agent.get_prompt()
    assert isinstance(prompt, str)
    assert "Prompt Agent" in prompt


async def test_agent_hash():
    """Test that agents can be hashed (used as dictionary keys)."""
    agent = Agent(name="Hash Agent")
    agent_dict = {agent: "value"}
    assert agent_dict[agent] == "value"


async def test_agent_equality():
    """Test agent equality based on ID."""
    agent1 = Agent(name="Agent 1")
    agent2 = Agent(name="Agent 2")
    agent1_copy = agent1  # Same reference

    assert agent1 == agent1_copy
    assert agent1 != agent2
