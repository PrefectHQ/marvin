from unittest.mock import patch

from slackbot.settings import _ensure_provider, _model_from_variables, bare_model_name


def test_ensure_provider_normalizes_bare_names():
    assert _ensure_provider("claude-sonnet-4-6") == "anthropic:claude-sonnet-4-6"
    assert _ensure_provider("gpt-5") == "openai:gpt-5"
    assert _ensure_provider("anthropic:claude-sonnet-4-6") == (
        "anthropic:claude-sonnet-4-6"
    )
    assert _ensure_provider("some-unknown-model") == "some-unknown-model"


def test_bare_model_name():
    assert bare_model_name("anthropic:claude-haiku-4-5-20251001") == (
        "claude-haiku-4-5-20251001"
    )
    assert bare_model_name("claude-haiku-4-5-20251001") == "claude-haiku-4-5-20251001"


def test_model_from_variables_prefers_first_set_variable():
    variables = {
        "marvin_utility_model": None,
        "marvin_memory_synthesis_model": "claude-haiku-4-5-20251001",
    }
    with patch(
        "slackbot.settings.Variable.get",
        side_effect=lambda name, default=None, _sync=True: variables.get(name, default),
    ):
        assert (
            _model_from_variables(
                ["marvin_utility_model", "marvin_memory_synthesis_model"],
                default="anthropic:claude-haiku-4-5-20251001",
            )
            == "anthropic:claude-haiku-4-5-20251001"
        )


def test_model_from_variables_falls_back_to_default():
    with patch(
        "slackbot.settings.Variable.get",
        side_effect=lambda name, default=None, _sync=True: default,
    ):
        assert (
            _model_from_variables(
                ["marvin_research_model"], default="anthropic:claude-haiku-4-5-20251001"
            )
            == "anthropic:claude-haiku-4-5-20251001"
        )
