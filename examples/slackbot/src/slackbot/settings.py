import os
from pathlib import Path
from typing import ClassVar, Literal

from prefect.blocks.system import Secret
from prefect.variables import Variable
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# gpt-* must route to the responses api: openai reasoning models reject
# function tools + reasoning on /v1/chat/completions
_PROVIDER_PREFIXES = {"claude": "anthropic", "gpt": "openai-responses"}


def _ensure_provider(model: str) -> str:
    """Normalize a model name to pydantic-ai's `provider:model` format.

    Prefect Variables may hold bare legacy names like "claude-sonnet-4-6".
    """
    if ":" in model:
        return model
    for prefix, provider in _PROVIDER_PREFIXES.items():
        if model.startswith(prefix):
            return f"{provider}:{model}"
    return model


def bare_model_name(model: str) -> str:
    """Strip the provider prefix for consumers that want a bare model name
    (Claude Agent SDK, explicit `AnthropicModel(...)` construction)."""
    return model.split(":", 1)[-1]


def _model_from_variables(names: list[str], default: str) -> str:
    for name in names:
        value = Variable.get(name, default=None, _sync=True)  # type: ignore
        if value:
            return _ensure_provider(value)
    return default


class SlackbotSettings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="MARVIN_SLACKBOT_", env_file=".env", extra="allow"
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to run the server on")
    port: int = Field(default=4200, description="Port to run the server on")

    # Logging settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="\x1b[32m%(asctime)s\x1b[0m \x1b[34m%(name)-12s\x1b[0m %(levelname)-8s %(message)s",
    )
    log_date_format: str = Field(default="%Y-%m-%d %H:%M:%S")

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        return v.upper()

    # Used for ephemeral thread_status dedup state only; durable thread
    # message history lives in Prefect block documents — see
    # `_internal/message_store.py`.
    db_file: Path = Field(
        default=Path("marvin_chat.sqlite"),
        description="Path to SQLite database file used for thread dedup state.",
    )

    temperature: float = Field(
        default=0.2, description="Temperature for model inference"
    )
    user_message_max_tokens: int = Field(
        default=500, description="Maximum tokens allowed in user messages"
    )

    github_token_secret_name: str = Field(
        default="marvin-slackbot-github-token",
        description="Name of the Prefect secret block containing GitHub API token",
    )
    claude_key_secret_name: str = Field(
        default="claude-api-key",
        description="Name of the Prefect secret block containing Claude API key",
    )
    openai_api_key_secret_name: str = Field(
        default="openai-api-key",
        description="Name of the Prefect secret block containing OpenAI API key",
    )
    anthropic_key_secret_name: str = Field(
        default="anthropic-api-key",
        description="Name of the Prefect secret block containing Anthropic API key",
    )

    logfire_token_secret_name: str = Field(
        default="logfire-write-token",
        description="Name of the Prefect secret block containing the Logfire write token",
    )
    logfire_service_name: str = Field(
        default="marvin-slackbot",
        description="Service name reported to Logfire",
    )
    logfire_environment: str = Field(
        default="production",
        description="Environment reported to Logfire",
    )

    vector_store_type: Literal["turbopuffer"] = Field(
        default="turbopuffer", description="Type of vector store to use"
    )
    user_facts_namespace_prefix: str = Field(
        default="user-facts-",
        description="Prefix for user facts namespaces in vector store",
    )

    # Development settings
    test_mode: bool = Field(
        default=False, description="Enable test mode with auto-reload"
    )

    slack_api_token: str = Field(default=..., description="Slack API bot user token")

    # Admin notification settings
    admin_slack_user_id: str = Field(
        default="",
        description="Slack user ID to notify when discussions are created (e.g., U1234567890)",
    )

    # Tool use limits
    max_tool_calls_per_turn: int = Field(
        default=50,
        description="Maximum number of tool calls allowed per agent turn to prevent runaway tool use",
    )

    @model_validator(mode="after")
    def _apply_post_validation_defaults(self) -> "SlackbotSettings":
        if "gpt-5" in self.bot_model:
            self.temperature = 1.0
        if not os.getenv("TURBOPUFFER_API_KEY"):
            try:
                api_key = Secret.load("tpuf-api-key", _sync=True).get()  # type: ignore
                os.environ["TURBOPUFFER_API_KEY"] = api_key
            except Exception:
                pass  # If secret doesn't exist, turbopuffer will handle the error
        if not self.admin_slack_user_id:
            self.admin_slack_user_id = Variable.get("admin-slack-id", _sync=True)
        return self

    # Model tiers. All values are full pydantic-ai `provider:model` strings,
    # overridable at runtime via Prefect Variables (legacy variable names kept
    # as fallbacks). The bot model is the product-facing voice and stays on the
    # strong tier; everything structured and non-voice runs on the utility tier.

    @property
    def bot_model(self) -> str:
        """Main answering agent."""
        return _model_from_variables(
            ["marvin_bot_model", "marvin_ai_model"],
            default="anthropic:claude-sonnet-5",
        )

    @property
    def utility_model(self) -> str:
        """Cheap tier for structured non-voice work: memory/profile synthesis,
        thread summarization."""
        return _model_from_variables(
            ["marvin_utility_model", "marvin_memory_synthesis_model"],
            default="anthropic:claude-haiku-4-5",
        )

    @property
    def research_model(self) -> str:
        """Claude Agent SDK subagent that reads Prefect source."""
        return _model_from_variables(
            ["marvin_research_model"],
            default="anthropic:claude-haiku-4-5",
        )


settings = SlackbotSettings()
