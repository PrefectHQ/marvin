"""Tests for MiniMax provider integration."""

import os
from unittest.mock import patch

import pytest
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from marvin.agents.agent import Agent

MINIMAX_API_URL = "https://api.minimax.io/v1"


def _make_minimax_model(
    model_name: str = "MiniMax-M2.7",
    api_key: str = "test-key",
) -> OpenAIModel:
    """Create a MiniMax model via OpenAI-compatible provider."""
    return OpenAIModel(
        model_name,
        provider=OpenAIProvider(api_key=api_key, base_url=MINIMAX_API_URL),
    )


class TestMiniMaxModelConfiguration:
    """Unit tests for MiniMax model configuration (no API calls)."""

    async def test_agent_with_minimax_model(self):
        """Test creating an agent with MiniMax model."""
        model = _make_minimax_model()
        agent = Agent(name="MiniMax Agent", model=model)
        assert agent.model is model
        assert agent.get_model() is model

    async def test_agent_with_minimax_m27_highspeed(self):
        """Test creating an agent with MiniMax-M2.7-highspeed model."""
        model = _make_minimax_model("MiniMax-M2.7-highspeed")
        agent = Agent(name="MiniMax Fast Agent", model=model)
        assert agent.model is model

    async def test_minimax_model_with_custom_temperature(self):
        """Test MiniMax model with custom temperature setting."""
        model = _make_minimax_model()
        agent = Agent(
            name="MiniMax Temp Agent",
            model=model,
            model_settings={"temperature": 0.7},
        )
        settings = agent.get_model_settings()
        assert settings["temperature"] == 0.7

    async def test_minimax_model_preserves_tools(self):
        """Test MiniMax agent preserves tool configuration."""

        def my_tool() -> str:
            """A test tool."""
            return "result"

        model = _make_minimax_model()
        agent = Agent(
            name="MiniMax Tool Agent",
            model=model,
            tools=[my_tool],
        )
        assert len(agent.get_tools()) == 1
        assert agent.get_tools()[0] is my_tool

    async def test_minimax_provider_base_url(self):
        """Test MiniMax provider uses correct base URL."""
        provider = OpenAIProvider(api_key="test-key", base_url=MINIMAX_API_URL)
        assert provider.base_url.rstrip("/") == MINIMAX_API_URL

    async def test_minimax_model_default_temperature(self):
        """Test MiniMax agent with default temperature (no override)."""
        model = _make_minimax_model()
        agent = Agent(name="MiniMax Default Agent", model=model)
        settings = agent.get_model_settings()
        assert "temperature" not in settings or settings.get("temperature") is None


class TestMiniMaxIntegration:
    """Integration tests for MiniMax API (requires MINIMAX_API_KEY)."""

    @pytest.fixture
    def minimax_api_key(self):
        key = os.getenv("MINIMAX_API_KEY")
        if not key:
            pytest.skip("MINIMAX_API_KEY not set")
        return key

    @pytest.fixture
    def minimax_model(self, minimax_api_key):
        return OpenAIModel(
            "MiniMax-M2.7",
            provider=OpenAIProvider(
                api_key=minimax_api_key,
                base_url=MINIMAX_API_URL,
            ),
        )

    @pytest.fixture
    def minimax_highspeed_model(self, minimax_api_key):
        return OpenAIModel(
            "MiniMax-M2.7-highspeed",
            provider=OpenAIProvider(
                api_key=minimax_api_key,
                base_url=MINIMAX_API_URL,
            ),
        )

    async def test_minimax_simple_run(self, minimax_model):
        """Test basic MiniMax API call via marvin.run."""
        import marvin

        agent = Agent(name="MiniMax Test", model=minimax_model)
        result = marvin.run(
            "Reply with exactly: hello",
            agents=[agent],
        )
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_minimax_structured_output(self, minimax_model):
        """Test MiniMax structured output extraction."""
        import marvin

        agent = Agent(name="MiniMax Extractor", model=minimax_model)
        result = marvin.run(
            "What is 2 + 2?",
            result_type=int,
            agents=[agent],
        )
        assert result == 4

    async def test_minimax_highspeed_model(self, minimax_highspeed_model):
        """Test MiniMax-M2.7-highspeed model works correctly."""
        import marvin

        agent = Agent(name="MiniMax Highspeed", model=minimax_highspeed_model)
        result = marvin.run(
            "Reply with exactly: fast",
            agents=[agent],
        )
        assert result is not None
        assert isinstance(result, str)
