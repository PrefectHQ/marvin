import pytest

from marvin.settings import Settings


@pytest.mark.parametrize(
    "model",
    ["openai:gpt-4o", "anthropic:claude-model-not-in-known-names"],
)
def test_agent_model_accepts_names_outside_known_model_names(
    monkeypatch: pytest.MonkeyPatch, model: str
):
    monkeypatch.setenv("MARVIN_AGENT_MODEL", model)

    assert Settings().agent_model == model


def test_agent_model_default_validates(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MARVIN_AGENT_MODEL", raising=False)

    assert Settings().agent_model == "openai:gpt-4o"
