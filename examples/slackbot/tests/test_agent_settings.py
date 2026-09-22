from unittest.mock import Mock

from pydantic_ai.models.test import TestModel
from slackbot import core


def test_agent_sends_no_temperature(monkeypatch):
    """Claude Opus 5.5 rejects `temperature` with a 400."""
    monkeypatch.setattr(core, "get_run_logger", Mock())
    monkeypatch.setattr(core, "_base_system_prompt", lambda: "")
    agent = core.create_agent(model=TestModel())
    assert "temperature" not in (agent.model_settings or {})
