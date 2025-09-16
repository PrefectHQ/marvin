"""Unit tests for concurrent task execution."""

import asyncio

import pytest

from marvin import Task
from marvin.agents.agent import Agent
from marvin.fns.run import _tasks_are_independent, run_tasks, run_tasks_async


class TestTaskIndependenceDetection:
    """Test the independence detection logic."""

    def test_independent_tasks(self):
        """Test that truly independent tasks are detected as such."""
        task1 = Task("Say 'one'", result_type=str)
        task2 = Task("Say 'two'", result_type=str)
        task3 = Task("Say 'three'", result_type=str)

        assert _tasks_are_independent([task1, task2, task3])

    def test_dependent_tasks_depends_on(self):
        """Test that tasks with depends_on are not independent."""
        task1 = Task("Say 'one'", result_type=str)
        task2 = Task("Say 'two'", result_type=str, depends_on=[task1])

        assert not _tasks_are_independent([task1, task2])

    def test_dependent_tasks_parent_child(self):
        """Test that parent-child tasks are not independent."""
        parent = Task("Parent task", result_type=str)
        child = Task("Child task", result_type=str)
        parent.subtasks.add(child)  # subtasks is a set, not list
        child.parent = parent

        assert not _tasks_are_independent([parent, child])

    def test_single_task_is_independent(self):
        """Test that a single task is considered independent."""
        task = Task("Solo task", result_type=str)
        assert _tasks_are_independent([task])

    def test_empty_task_list(self):
        """Test empty task list."""
        assert _tasks_are_independent([])


class TestConcurrentExecution:
    """Test actual concurrent execution behavior."""

    @pytest.mark.asyncio
    async def test_independent_tasks_run_without_errors(self):
        """Test that independent tasks run without Multiple EndTurn warnings or errors."""
        task1 = Task("Say 'one'", result_type=str)
        task2 = Task("Say 'two'", result_type=str)
        task3 = Task("Say 'three'", result_type=str)

        # Should not raise any errors (no Multiple EndTurn warnings, no infinite loops)
        results = await run_tasks_async([task1, task2, task3])

        assert len(results) == 3
        assert all(task.is_successful() for task in results)

        # Verify results
        result_values = [task.result for task in results]
        assert set(result_values) == {"one", "two", "three"}

    @pytest.mark.asyncio
    async def test_dependent_tasks_run_in_order(self):
        """Test that dependent tasks run in correct order."""
        task1 = Task("Say 'A'", result_type=str)
        task2 = Task("Say 'B'", result_type=str, depends_on=[task1])
        task3 = Task("Say 'C'", result_type=str, depends_on=[task2])

        results = await run_tasks_async([task1, task2, task3])

        assert len(results) == 3
        assert all(task.is_successful() for task in results)

        # Verify correct order
        result_values = [task.result for task in results]
        assert result_values == ["A", "B", "C"]

    def test_sync_run_tasks_independent(self):
        """Test synchronous run_tasks with independent tasks."""
        task1 = Task("Say 'one'", result_type=str)
        task2 = Task("Say 'two'", result_type=str)

        results = run_tasks([task1, task2])

        assert len(results) == 2
        assert all(task.is_successful() for task in results)
        assert set(t.result for t in results) == {"one", "two"}

    def test_sync_run_tasks_dependent(self):
        """Test synchronous run_tasks with dependent tasks."""
        task1 = Task("Say 'A'", result_type=str)
        task2 = Task("Say 'B'", result_type=str, depends_on=[task1])

        results = run_tasks([task1, task2])

        assert len(results) == 2
        assert all(task.is_successful() for task in results)

        # Verify correct order
        result_values = [task.result for task in results]
        assert result_values == ["A", "B"]


class TestAsyncioGatherCompatibility:
    """Test that asyncio.gather works without ContextVar errors."""

    @pytest.mark.asyncio
    async def test_asyncio_gather_no_context_errors(self):
        """Test that asyncio.gather doesn't throw ContextVar errors."""
        task1 = Task("Say 'async1'", result_type=str)
        task2 = Task("Say 'async2'", result_type=str)
        task3 = Task("Say 'async3'", result_type=str)

        # This should not raise ContextVar token errors
        results = await asyncio.gather(
            task1.run_async(), task2.run_async(), task3.run_async()
        )

        assert len(results) == 3
        assert set(results) == {"async1", "async2", "async3"}

    @pytest.mark.asyncio
    async def test_mixed_execution_patterns(self):
        """Test mixing run_tasks_async and asyncio.gather in same event loop."""
        # First batch via run_tasks_async
        task1 = Task("Say 'batch1'", result_type=str)
        task2 = Task("Say 'batch2'", result_type=str)
        batch1_results = await run_tasks_async([task1, task2])

        # Second batch via asyncio.gather
        task3 = Task("Say 'gather1'", result_type=str)
        task4 = Task("Say 'gather2'", result_type=str)
        batch2_results = await asyncio.gather(task3.run_async(), task4.run_async())

        # Both should work without errors
        assert len(batch1_results) == 2
        assert all(task.is_successful() for task in batch1_results)
        assert len(batch2_results) == 2
        assert set(batch2_results) == {"gather1", "gather2"}


class TestContextVarHandling:
    """Test ContextVar token handling across async contexts."""

    @pytest.mark.asyncio
    async def test_actor_context_across_asyncio_gather(self):
        """Test that Actor context management handles asyncio.gather correctly."""
        from marvin.agents.actor import _current_actor

        async def task_with_actor(name):
            actor = Agent(name=f"Agent_{name}")
            # This should not raise an error even with asyncio.gather
            with actor:
                assert _current_actor.get() == actor
                await asyncio.sleep(0.1)  # Simulate async work
            # Context should be reset without errors
            return name

        # Test that concurrent context management works
        results = await asyncio.gather(
            task_with_actor("1"), task_with_actor("2"), task_with_actor("3")
        )

        assert results == ["1", "2", "3"]
        # Context should be None after all tasks complete
        assert _current_actor.get() is None

    def test_actor_context_sequential(self):
        """Test that Actor context works normally in sequential execution."""
        from marvin.agents.actor import _current_actor

        actor1 = Agent(name="Sequential_1")
        actor2 = Agent(name="Sequential_2")

        # Test nested contexts work correctly
        assert _current_actor.get() is None

        with actor1:
            assert _current_actor.get() == actor1
            with actor2:
                assert _current_actor.get() == actor2
            assert _current_actor.get() == actor1

        assert _current_actor.get() is None
