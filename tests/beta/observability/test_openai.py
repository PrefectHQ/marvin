"""
Tests for the Prefect + OpenAI observability integration module.
"""

from prefect import flow, task

import marvin
from marvin.beta.observability.openai import (
    get_prefect_context,
    observable,
    openai_request_kwargs,
)


class TestGetPrefectContext:
    """Tests for get_prefect_context()"""

    def test_returns_empty_dict_outside_flow(self):
        """Outside a flow, context should be empty."""
        ctx = get_prefect_context()
        assert ctx == {}

    async def test_returns_flow_context_inside_flow(self):
        """Inside a flow, context should include flow_run metadata."""

        @flow
        async def test_flow():
            return get_prefect_context()

        ctx = await test_flow()

        assert "prefect.flow_run.id" in ctx
        assert "prefect.flow_run.name" in ctx
        assert "prefect.flow_run.flow_name" in ctx
        # Prefect normalizes flow names (underscores -> hyphens)
        assert ctx["prefect.flow_run.flow_name"] == "test-flow"

        # Should NOT have task info (not in a task)
        assert "prefect.task_run.id" not in ctx

    async def test_returns_task_context_inside_task(self):
        """Inside a task, context should include both flow and task metadata."""

        @task
        def get_context():
            return get_prefect_context()

        @flow
        async def test_flow():
            return get_context()

        ctx = await test_flow()

        assert "prefect.flow_run.id" in ctx
        assert "prefect.task_run.id" in ctx
        assert "prefect.task_run.task_name" in ctx
        assert "get_context" in ctx["prefect.task_run.task_name"]

    async def test_all_values_are_strings(self):
        """All context values must be strings (OpenAI requirement)."""

        @flow
        async def test_flow():
            return get_prefect_context()

        ctx = await test_flow()

        for key, value in ctx.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestObservable:
    """Tests for observable()"""

    def test_returns_new_agent_instance(self):
        """Should return a new agent, not mutate the original."""
        original = marvin.Agent(name="original", model="openai:gpt-4o-mini")
        wrapped = observable(original)

        assert wrapped is not original
        assert original.name == "original"
        assert wrapped.name == "original"

    def test_original_agent_unchanged(self):
        """Original agent's model_settings should not be modified."""
        original = marvin.Agent(
            name="original",
            model="openai:gpt-4o-mini",
            model_settings={"temperature": 0.5},
        )
        observable(original)

        assert original.model_settings == {"temperature": 0.5}

    def test_merges_with_existing_settings(self):
        """Should merge observability settings with existing model_settings."""
        original = marvin.Agent(
            name="original",
            model="openai:gpt-4o-mini",
            model_settings={"temperature": 0.5},
        )
        wrapped = observable(original)

        assert wrapped.model_settings["temperature"] == 0.5
        assert wrapped.model_settings["extra_body"]["store"] is True

    def test_includes_custom_metadata(self):
        """Custom metadata should be included."""
        original = marvin.Agent(name="original", model="openai:gpt-4o-mini")
        wrapped = observable(original, customer_id="abc123")

        metadata = wrapped.model_settings["extra_body"]["metadata"]
        assert metadata["customer_id"] == "abc123"

    async def test_captures_prefect_context_in_task(self):
        """When called inside a task, should capture task context."""

        @task
        def wrap_agent():
            agent = marvin.Agent(name="test", model="openai:gpt-4o-mini")
            return observable(agent)

        @flow
        async def test_flow():
            return wrap_agent()

        wrapped = await test_flow()

        metadata = wrapped.model_settings["extra_body"]["metadata"]
        assert "prefect.flow_run.id" in metadata
        assert "prefect.task_run.id" in metadata

    def test_deep_merges_extra_body(self):
        """Should deep merge extra_body if it already exists."""
        original = marvin.Agent(
            name="original",
            model="openai:gpt-4o-mini",
            model_settings={
                "extra_body": {
                    "existing_key": "existing_value",
                }
            },
        )
        wrapped = observable(original)

        extra_body = wrapped.model_settings["extra_body"]
        assert extra_body["existing_key"] == "existing_value"
        assert extra_body["store"] is True


class TestOpenaiRequestKwargs:
    """Tests for openai_request_kwargs() - direct OpenAI SDK usage."""

    def test_returns_store_outside_flow(self):
        """Outside a flow, should return store=True."""
        kwargs = openai_request_kwargs()
        assert kwargs["store"] is True

    def test_includes_custom_metadata(self):
        """Custom metadata should be included."""
        kwargs = openai_request_kwargs(env="production")
        assert kwargs["store"] is True
        assert kwargs["metadata"]["env"] == "production"

    async def test_includes_prefect_context_in_flow(self):
        """Inside a flow, should include Prefect context."""

        @flow
        async def test_flow():
            return openai_request_kwargs()

        kwargs = await test_flow()

        assert kwargs["store"] is True
        assert "prefect.flow_run.id" in kwargs["metadata"]
