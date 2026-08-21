from pydantic_ai.providers.anthropic import AnthropicProvider


def test_anthropic_provider_accepts_pydantic_ai_http_client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    AnthropicProvider()
