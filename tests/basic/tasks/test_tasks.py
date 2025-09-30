import enum
import re
from typing import Literal

import pytest
from dirty_equals import IsStr
from pydantic_ai import ImageUrl

import marvin
from marvin import Thread
from marvin.agents.agent import Agent
from marvin.agents.team import Swarm
from marvin.tasks.task import Task, TaskState
from marvin.utilities.types import Labels


def normalize_whitespace(text: str) -> str:
    # Replace all whitespace sequences with a single space and strip
    return " ".join(text.split())


class Colors(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestClassification:
    async def test_auto_enum_conversion(self):
        """Test automatic conversion of list to Labels."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

    async def test_literal_classifier(self):
        """Test using Literal as classifier."""
        task = Task("Choose sentiment", result_type=Literal["positive", "negative"])
        assert task.is_classifier()

        # Test validation returns raw values
        await task.mark_successful(0)
        assert task.result == "positive"
        await task.mark_successful(1)
        assert task.result == "negative"

    async def test_enum_classifier(self):
        """Test using Enum as classifier."""
        task = Task("Choose color", result_type=Colors)
        assert task.is_classifier()

        # Test validation returns enum members
        await task.mark_successful(0)
        assert task.result == Colors.RED
        assert task.result.value == "red"

    async def test_raw_list_classifier(self):
        """Test using raw list as classifier."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

        # Test validation returns raw values
        await task.mark_successful(0)
        assert task.result == "red"
        await task.mark_successful(1)
        assert task.result == "green"

    async def test_multi_label_classifier(self):
        """Test multi-label classification."""
        # Using list[Literal]
        task1 = Task("Choose colors", result_type=list[Literal["red", "green", "blue"]])
        assert task1.is_classifier()
        assert task1.get_result_type() == list[int]

        # Test validation returns raw values
        await task1.mark_successful([0, 2])
        assert task1.result == ["red", "blue"]

        # Using list[Enum]
        task2 = Task("Choose colors", result_type=list[Colors])
        assert task2.is_classifier()
        assert task2.get_result_type() == list[int]

        # Test validation returns enum members
        await task2.mark_successful([0, 2])
        assert task2.result == [Colors.RED, Colors.BLUE]
        assert [v.value for v in task2.result] == ["red", "blue"]

    async def test_labels_classifier(self):
        """Test using list[list] syntax for multi-label classification."""
        # Test single-label with raw list
        task = Task("Choose color", result_type=["red", "green", "blue"])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == ("red", "green", "blue")

        # Test validation returns raw values
        await task.mark_successful(0)
        assert task.result == "red"

        # Test multi-label with list[list]
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])
        assert task.is_classifier()
        assert task.get_result_type() == list[int]

        # Test validation returns raw values
        await task.mark_successful([0, 2])
        assert task.result == ["red", "blue"]

    async def test_classifier_validation_errors(self):
        """Test validation error cases for classifiers."""
        # Test single-label
        task = Task("Choose color", result_type=["red", "green", "blue"])

        with pytest.raises(ValueError, match="Expected an integer index"):
            await task.mark_successful("red")  # Wrong type
        with pytest.raises(ValueError, match="between 0 and"):
            await task.mark_successful(3)  # Out of range
        with pytest.raises(ValueError, match="Expected an integer index"):
            await task.mark_successful([0])  # List when single expected

        # Test multi-label
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])

        with pytest.raises(ValueError, match="Expected a list of indices"):
            await task.mark_successful(0)  # Single when list expected
        with pytest.raises(ValueError, match="All elements must be integers"):
            await task.mark_successful(["red"])  # Wrong element type
        with pytest.raises(ValueError, match="between 0 and"):
            await task.mark_successful([3])  # Out of range index

    async def test_classifier_prompt_instruction(self):
        """Test that classifier tasks include the additional instruction in their default prompt."""
        task = Task("Choose color", result_type=["red", "green", "blue"])
        prompt = task.get_prompt()
        expected_instruction = (
            "Provide the integer indices of your chosen "
            """labels: {0: "'red'", 1: "'green'", 2: "'blue'"}"""
        )
        assert expected_instruction in prompt[0]

        # Test that custom prompts don't include the instruction
        task = Task(
            "Choose color",
            result_type=["red", "green", "blue"],
            prompt_template="Custom prompt: {{task.instructions}}",
        )
        prompt = task.get_prompt()
        assert expected_instruction not in prompt[0]
        assert prompt[0] == "Custom prompt: Choose color"

    async def test_classifier_edge_cases(self):
        """Test edge cases for classifier types."""
        # Empty lists
        with pytest.raises(ValueError):
            Task("Empty", result_type=[])
        with pytest.raises(ValueError):
            Task("Empty nested", result_type=[[]])

        # Wrong nested format
        with pytest.raises(ValueError):
            Task("Wrong nesting", result_type=[[], []])

        # Mixed types are allowed
        task = Task("Mixed", result_type=[1, "red", True])
        assert task.is_classifier()
        assert isinstance(task.result_type, Labels)
        assert task.result_type.labels == (1, "red", True)

    async def test_type_preservation(self):
        """Test that type hints are preserved for IDE support."""
        # Enum types
        task1: Task[Colors] = Task("Colors", result_type=Colors)
        assert task1.is_classifier()
        await task1.mark_successful(0)
        assert isinstance(task1.result, Colors)
        assert task1.result == Colors.RED

        # Multi-label enum
        task2: Task[list[Colors]] = Task("Colors", result_type=list[Colors])
        assert task2.is_classifier()
        await task2.mark_successful([0, 1])
        assert isinstance(task2.result, list)
        assert all(isinstance(x, Colors) for x in task2.result)
        assert task2.result == [Colors.RED, Colors.GREEN]

        # Literal types
        task3: Task[Literal["a", "b"]] = Task("Literal", result_type=Literal["a", "b"])
        assert task3.is_classifier()
        await task3.mark_successful(0)
        assert isinstance(task3.result, str)
        assert task3.result == "a"

    async def test_validation_edge_cases(self):
        """Test edge cases for validation."""
        # Single-label
        task = Task("Choose color", result_type=["red", "green", "blue"])

        with pytest.raises(ValueError):
            await task.mark_successful(None)  # None value

        # Multi-label
        task = Task("Choose colors", result_type=[["red", "green", "blue"]])

        with pytest.raises(ValueError):
            await task.mark_successful([])  # Empty list
        with pytest.raises(ValueError):
            await task.mark_successful(None)  # None value
        with pytest.raises(ValueError):
            await task.mark_successful([0, 0])  # Duplicate indices


async def test_task_initialization():
    """Test basic task initialization."""
    task = Task(instructions="Test task")
    assert isinstance(task.id, str)
    assert task.instructions == "Test task"
    assert task.result_type is str
    assert task.state == TaskState.PENDING
    assert task.result is None
    assert task.context == {}
    assert task.name is None
    assert task.subtasks == set()
    assert task.parent is None
    assert task.verbose is False


async def test_task_with_agent():
    """Test task with custom agent."""
    agent = Agent()
    task = Task(instructions="Test with agent", agents=[agent])
    assert task.get_actor() is agent


async def test_task_with_multiple_agents():
    """Test task with multiple agents."""
    agent1 = Agent()
    agent2 = Agent()
    task = Task(instructions="Test with multiple agents", agents=[agent1, agent2])
    actor = task.get_actor()
    assert isinstance(actor, Swarm)
    assert actor.members == [agent1, agent2]


async def test_task_get_default_agent():
    """Test getting default agent when none specified."""
    task = Task(instructions="Test default agent")
    assert task.get_actor() is marvin.defaults.agent


async def test_task_mark_successful():
    """Test marking task as successful."""
    task = Task(instructions="Test success")
    await task.mark_successful("test result")
    assert task.state == TaskState.SUCCESSFUL
    assert task.result == "test result"


async def test_task_optional_result_type():
    """Test that tasks with Optional result types can validate None."""
    task = Task(instructions="test", result_type=str | None)
    validated = task.validate_result(None)
    assert validated is None


async def test_task_mark_failed():
    """Test marking task as failed."""
    task = Task(instructions="Test failure")
    error_msg = "Test error"
    await task.mark_failed(error_msg)
    assert task.state == TaskState.FAILED
    assert task.result == error_msg


async def test_task_with_custom_validator():
    """Test task with custom result validator."""

    def validate_positive(x: int) -> int:
        if x <= 0:
            raise ValueError("Number must be positive")
        return x

    task = Task(
        instructions="Test validation",
        result_type=int,
        result_validator=validate_positive,
    )

    # Test successful validation
    await task.mark_successful(5)
    assert task.result == 5

    # Test failed validation
    with pytest.raises(ValueError):
        await task.mark_successful(-1)


async def test_task_parent_child_relationship():
    """Test parent-child task relationship."""
    parent_task = Task(instructions="Parent task")
    child_task = Task(instructions="Child task", parent=parent_task)

    assert child_task.parent is parent_task
    assert child_task in parent_task.subtasks


async def test_task_parent_child_bidirectional():
    """Test that parent-child relationship is properly maintained when changed."""
    parent1 = Task(instructions="Parent 1")
    parent2 = Task(instructions="Parent 2")
    child = Task(instructions="Child task")

    # Test setting parent directly
    child.parent = parent1
    assert child.parent is parent1
    assert child in parent1.subtasks

    # Test changing parent
    child.parent = parent2
    assert child.parent is parent2
    assert child in parent2.subtasks
    assert child not in parent1.subtasks

    # Test removing parent
    child.parent = None
    assert child.parent is None
    assert child not in parent2.subtasks


async def test_task_dependencies():
    """Test task dependencies."""
    task1 = Task(instructions="Task 1")
    task2 = Task(instructions="Task 2")
    task3 = Task(instructions="Task 3", depends_on=[task1, task2])

    assert task1 in task3.depends_on
    assert task2 in task3.depends_on

    # Test initialization with empty dependencies
    task4 = Task(instructions="Task 4", depends_on=[])
    assert len(task4.depends_on) == 0

    # Test initialization with None dependencies
    task5 = Task(instructions="Task 5", depends_on=None)
    assert len(task5.depends_on) == 0


async def test_task_complex_relationships():
    """Test complex task relationships with multiple parents, children, and dependencies."""
    # Create a network of tasks
    root = Task(instructions="Root")
    child1 = Task(instructions="Child 1", parent=root)
    child2 = Task(instructions="Child 2", parent=root)
    grandchild = Task(instructions="Grandchild", parent=child1, depends_on=[child2])

    # Test parent relationships
    assert child1.parent is root
    assert child2.parent is root
    assert grandchild.parent is child1

    # Test subtasks
    assert child1 in root.subtasks
    assert child2 in root.subtasks
    assert grandchild in child1.subtasks

    # Test dependencies
    assert child2 in grandchild.depends_on

    # Test relationship changes
    # Move grandchild to child2
    grandchild.parent = child2
    assert grandchild.parent is child2
    assert grandchild not in child1.subtasks
    assert grandchild in child2.subtasks
    assert child2 in grandchild.depends_on  # Dependencies remain unchanged


async def test_task_context_basic():
    """Test that tasks created in a context inherit the parent."""
    parent = Task(instructions="Parent")

    # Outside context - no parent
    task1 = Task(instructions="Task 1")
    assert task1.parent is None

    # Inside context - inherits parent
    with parent:
        task2 = Task(instructions="Task 2")
        task3 = Task(instructions="Task 3")
        assert task2.parent is parent
        assert task3.parent is parent
        assert task2 in parent.subtasks
        assert task3 in parent.subtasks


async def test_task_context_nested():
    """Test that tasks use the most recent context as parent."""
    parent1 = Task(instructions="Parent 1")
    parent2 = Task(instructions="Parent 2")

    with parent1:
        task1 = Task(instructions="Task 1")  # uses parent1
        assert task1.parent is parent1

        with parent2:
            task2 = Task(instructions="Task 2")  # uses parent2
            assert task2.parent is parent2
            assert task2 not in parent1.subtasks

        task3 = Task(instructions="Task 3")  # uses parent1 again
        assert task3.parent is parent1


async def test_task_context_override():
    """Test that explicitly passed parent overrides context parent."""
    context_parent = Task(instructions="Context parent")
    manual_parent = Task(instructions="Manual parent")

    with context_parent:
        # Uses context
        task1 = Task(instructions="Task 1")
        assert task1.parent is context_parent

        # Overrides context
        task2 = Task(instructions="Task 2", parent=manual_parent)
        assert task2.parent is manual_parent
        assert task2 not in context_parent.subtasks
        assert task2 in manual_parent.subtasks


async def test_task_context_reenter():
    """Test that reentering a context works correctly."""
    parent = Task(instructions="Parent")

    with parent:
        task1 = Task(instructions="Task 1")
        assert task1.parent is parent

    # Outside context
    task2 = Task(instructions="Task 2")
    assert task2.parent is None

    # Reenter context
    with parent:
        task3 = Task(instructions="Task 3")
        assert task3.parent is parent
        assert task3 in parent.subtasks


async def test_task_with_context():
    """Test task with context data."""
    context = {"key": "value"}
    task = Task(instructions="Test context", context=context)
    assert task.context == context


class TestTaskPrompt:
    async def test_task_prompt_generation(self):
        """Test customizing task prompts."""
        # Test default prompt
        task = Task(
            name="test task",
            instructions="Do something",
            context={"key": "value"},
        )
        prompt = task.get_prompt()
        assert prompt[0] == IsStr(
            regex=re.compile(
                rf"^<task>.*<id>\s*{task.id}\s*</id>.*<\/task>", flags=re.DOTALL
            )
        )
        assert prompt[0] == IsStr(
            regex=re.compile(
                rf"^<task>.*<name>\s*{task.name}\s*</name>.*<\/task>", flags=re.DOTALL
            )
        )
        assert prompt[0] == IsStr(
            regex=re.compile(
                rf"^<task>.*<instructions>\s*{task.instructions}\s*<\/instructions>.*<\/task>",
                flags=re.DOTALL,
            )
        )
        assert prompt[0] == IsStr(
            regex=re.compile(
                r"^<task>.*<context>.*<\/context>.*<\/task>",
                flags=re.DOTALL,
            )
        )

    async def test_task_prompt_template(self):
        # Test custom prompt
        task = Task(
            name="test task",
            instructions="Do something",
            context={"key": "value"},
            prompt_template="Task {{task.name}}: {{task.instructions}}",
        )
        prompt = task.get_prompt()
        assert prompt[0] == "Task test task: Do something"

    async def test_task_prompt_jinja_template(self):
        # Test custom prompt with conditional logic
        task = Task(
            name="test task",
            instructions="Do something",
            context={"key": "value"},
            prompt_template="""
                {% if task.name %}NAME: {{task.name}}{% endif %}
                INSTRUCTIONS: {{task.instructions}}
                {% if task.context %}CONTEXT: {{task.context}}{% endif %}
            """.strip(),
        )
        prompt = task.get_prompt()
        assert "NAME: test task" in prompt[0]
        assert "INSTRUCTIONS: Do something" in prompt[0]
        assert "CONTEXT: {'key': 'value'}" in prompt[0]

    async def test_task_prompt_jinja_template_with_methods(self):
        # Test accessing task methods in template
        task = Task(
            instructions="Do something",
            prompt_template="Task is complete: {{task.is_complete()}}",
        )
        prompt = task.get_prompt()
        assert prompt[0] == "Task is complete: False"
        await task.mark_successful("test result")
        prompt = task.get_prompt()
        assert prompt[0] == "Task is complete: True"


class TestVerbose:
    @pytest.fixture
    def thread(self) -> marvin.Thread:
        return marvin.Thread()

    async def test_create_verbose_task(self, thread: Thread):
        """Test that tasks can be created with verbose=True."""
        task = Task(instructions="Test verbose", verbose=True)
        assert task.verbose

    async def test_mark_verbose_task_successful(self, thread: Thread):
        """Test that verbose tasks add a message to the thread when marked successful."""
        task = Task(instructions="Test verbose", verbose=True)
        await task.mark_successful("test result", thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* successful with result.*$"
        )

    async def test_mark_verbose_task_successful_context_thread(self, thread: Thread):
        """Test that verbose tasks use the context thread when marking successful."""
        task = Task(instructions="Test verbose", verbose=True)
        with thread:
            await task.mark_successful("test result")
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* successful with result.*$"
        )

    async def test_mark_non_verbose_task_successful(self, thread: Thread):
        """Test that non-verbose tasks don't add messages when marked successful."""
        task = Task(instructions="Test verbose", verbose=False)
        await task.mark_successful("test result", thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 0

    async def test_mark_verbose_task_failed(self, thread: Thread):
        """Test that verbose tasks add a message to the thread when marked failed."""
        task = Task(instructions="Test verbose", verbose=True)
        await task.mark_failed("test error", thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* failed with error.*$"
        )

    async def test_mark_verbose_task_failed_context_thread(self, thread: Thread):
        """Test that verbose tasks use the context thread when marking failed."""
        task = Task(instructions="Test verbose", verbose=True)
        with thread:
            await task.mark_failed("test error")
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* failed with error.*$"
        )

    async def test_mark_non_verbose_task_failed(self, thread: Thread):
        """Test that non-verbose tasks don't add messages when marked failed."""
        task = Task(instructions="Test verbose", verbose=False)
        await task.mark_failed("test error", thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 0

    async def test_mark_verbose_task_skipped(self, thread: Thread):
        """Test that verbose tasks add a message to the thread when marked skipped."""
        task = Task(instructions="Test verbose", verbose=True)
        await task.mark_skipped(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* skipped$"
        )

    async def test_mark_verbose_task_skipped_context_thread(self, thread: Thread):
        """Test that verbose tasks use the context thread when marking skipped."""
        task = Task(instructions="Test verbose", verbose=True)
        with thread:
            await task.mark_skipped()
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content == IsStr(
            regex=r"^Task state updated: .* skipped$"
        )

    async def test_mark_non_verbose_task_skipped(self, thread: Thread):
        """Test that non-verbose tasks don't add messages when marked skipped."""
        task = Task(instructions="Test verbose", verbose=False)
        await task.mark_skipped(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 0

    async def test_mark_verbose_task_running(self, thread: Thread):
        """Test that verbose tasks add a message to the thread when marked running."""
        task = Task(instructions="Test running", verbose=True)
        await task.mark_running(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content[0] == IsStr(
            regex=re.compile(
                r"^<task>.*<instructions>\s*Test running\s*<\/instructions>.*<\/task>$",
                flags=re.DOTALL,
            )
        )

    async def test_mark_verbose_task_running_context_thread(self, thread: Thread):
        """Test that verbose tasks use the context thread when marking running."""
        task = Task(instructions="Test running", verbose=True)
        with thread:
            await task.mark_running()
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content[0] == IsStr(
            regex=re.compile(
                r"^<task>.*<instructions>\s*Test running\s*<\/instructions>.*<\/task>$",
                flags=re.DOTALL,
            )
        )

    async def test_mark_non_verbose_task_running(self, thread: Thread):
        """Test that non-verbose tasks still add messages when marked running."""
        task = Task(instructions="Test running", verbose=False)
        with thread:
            await task.mark_running()
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content[0] == IsStr(
            regex=re.compile(
                r"^<task>.*<instructions>\s*Test running\s*<\/instructions>.*<\/task>$",
                flags=re.DOTALL,
            )
        )

    async def test_mark_task_with_attachments_running(self, thread: Thread):
        """Test that tasks with attachments add a message to the thread when marked running."""
        task = Task(
            instructions="Test running", verbose=True, attachments=[ImageUrl("abc")]
        )
        await task.mark_running(thread=thread)
        messages = await thread.get_messages_async()
        assert len(messages) == 1
        assert messages[0].message.parts[0].content[0] == IsStr(
            regex=re.compile(
                r"^<task>.*<instructions>\s*Test running\s*<\/instructions>.*<\/task>$",
                flags=re.DOTALL,
            )
        )
        assert messages[0].message.parts[0].content[1] == ImageUrl("abc")
