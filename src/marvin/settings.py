import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, Optional, Union

from ._compat import OPENAI_V1, BaseSettings, SecretStr, model_dump

DEFAULT_ENV_PATH = Path(os.getenv("MARVIN_ENV_FILE", "~/.marvin/.env")).expanduser()

request_timeout_key = "timeout" if OPENAI_V1 else "request_timeout"


class MarvinBaseSettings(BaseSettings):
    class Config:
        env_file = (
            ".env",
            str(DEFAULT_ENV_PATH),
        )
        env_prefix = "MARVIN_"
        validate_assignment = True


class OpenAISettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""

    class Config:
        env_prefix = "MARVIN_OPENAI_"

    api_key: Optional[SecretStr] = None
    organization: Optional[str] = None
    embedding_engine: str = "text-embedding-ada-002"
    api_type: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        import os

        import openai as openai_sdk

        from marvin import openai as marvin_openai

        EXCLUDE_KEYS = {"stream_handler"}

        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens"] = settings.llm_max_tokens

        if os.environ.get("MARVIN_OPENAI_API_KEY"):
            print("MARVIN_OPENAI_API_KEY")
            response["api_key"] = os.environ["MARVIN_OPENAI_API_KEY"]
        elif os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY")
            response["api_key"] = os.environ["OPENAI_API_KEY"]
        elif not OPENAI_V1 and openai_sdk.api_key:
            print("openai_sdk.api_key")
            response["api_key"] = openai_sdk.api_key
        elif not OPENAI_V1 and marvin_openai.api_key:
            print("marvin_openai.api_key")
            response["api_key"] = marvin_openai.api_key
        response["temperature"] = settings.llm_temperature
        response[request_timeout_key] = settings.llm_request_timeout_seconds
        return {
            k: v for k, v in response.items() if v is not None and k not in EXCLUDE_KEYS
        }


class AnthropicSettings(MarvinBaseSettings):
    class Config:
        env_prefix = "MARVIN_ANTHROPIC_"

    api_key: Optional[SecretStr] = None

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens_to_sample"] = settings.llm_max_tokens
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        response["temperature"] = settings.llm_temperature
        response["timeout"] = settings.llm_request_timeout_seconds
        if os.environ.get("MARVIN_ANTHROPIC_API_KEY"):
            response["api_key"] = os.environ["MARVIN_ANTHROPIC_API_KEY"]
        if os.environ.get("ANTHROPIC_API_KEY"):
            response["api_key"] = os.environ["ANTHROPIC_API_KEY"]
        return {k: v for k, v in response.items() if v is not None}


class AzureOpenAI(MarvinBaseSettings):
    class Config:
        env_prefix = "MARVIN_AZURE_OPENAI_"

    api_key: Optional[SecretStr] = None
    api_type: Literal["azure", "azure_ad"] = "azure"
    # "The endpoint of the Azure OpenAI API. This should have the form https://YOUR_RESOURCE_NAME.openai.azure.com" # noqa
    api_base: Optional[str] = None
    api_version: Optional[str] = "2023-07-01-preview"
    # `deployment_name` will correspond to the custom name you chose for your deployment when # noqa
    # you deployed a model.
    deployment_name: Optional[str] = None

    def get_defaults(self, settings: "Settings") -> dict[str, Any]:
        import os

        import openai

        from marvin import openai as marvin_openai

        response: dict[str, Any] = {}
        if settings.llm_max_context_tokens > 0:
            response["max_tokens"] = settings.llm_max_tokens
        response["temperature"] = settings.llm_temperature
        response[request_timeout_key] = settings.llm_request_timeout_seconds
        response["api_key"] = self.api_key and self.api_key.get_secret_value()
        if os.environ.get("MARVIN_AZURE_OPENAI_API_KEY"):
            response["api_key"] = os.environ["MARVIN_AZURE_OPENAI_API_KEY"]
        if not OPENAI_V1 and openai.api_key:
            response["api_key"] = openai.api_key
        if marvin_openai.api_key:
            response["api_key"] = marvin_openai.api_key

        return model_dump(self, exclude_unset=True) | {
            k: v for k, v in response.items() if v is not None
        }


def initial_setup(home: Union[Path, None] = None) -> Path:
    if not home:
        home = Path.home() / ".marvin"
    home.mkdir(parents=True, exist_ok=True)
    return home


class Settings(MarvinBaseSettings):
    """Marvin settings"""

    home: Path = initial_setup()
    test_mode: bool = False

    # LOGGING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    verbose: bool = False

    # LLMS
    llm_model: str = "openai/gpt-3.5-turbo"
    llm_max_tokens: int = 1500
    llm_max_context_tokens: int = 3500
    llm_temperature: float = 0.8
    llm_request_timeout_seconds: Union[float, list[float]] = 600.0

    # AI APPLICATIONS
    ai_application_max_iterations: Optional[int] = None

    # providers
    openai: OpenAISettings = OpenAISettings()
    anthropic: AnthropicSettings = AnthropicSettings()
    azure_openai: AzureOpenAI = AzureOpenAI()

    # SLACK
    slack_api_token: Optional[SecretStr] = None

    # TOOLS

    # chroma
    chroma_server_host: Optional[str] = None
    chroma_server_http_port: Optional[int] = None

    # github
    github_token: Optional[SecretStr] = None

    # wolfram
    wolfram_app_id: Optional[SecretStr] = None

    def get_defaults(self, provider: Optional[str] = None) -> dict[str, Any]:
        response: dict[str, Any] = {}
        if provider == "openai":
            return self.openai.get_defaults(self)
        elif provider == "anthropic":
            return self.anthropic.get_defaults(self)
        elif provider == "azure_openai":
            return self.azure_openai.get_defaults(self)
        else:
            return response


settings = Settings()


@contextmanager
def temporary_settings(**kwargs: Any):
    """
    Temporarily override Marvin setting values. This will _not_ mutate values that have
    been already been accessed at module load time.

    This function should only be used for testing.

    Example:
        >>> from marvin.settings import settings
        >>> with temporary_settings(MARVIN_LLM_MAX_TOKENS=100):
        >>>    assert settings.llm_max_tokens == 100
        >>> assert settings.llm_max_tokens == 1500
    """
    old_env = os.environ.copy()
    old_settings = settings.copy()

    try:
        for setting in kwargs:
            value = kwargs.get(setting)
            if value is not None:
                os.environ[setting] = str(value)
            else:
                os.environ.pop(setting, None)

        new_settings = Settings()

        for field in settings.__fields__:
            object.__setattr__(settings, field, getattr(new_settings, field))

        yield settings
    finally:
        for setting in kwargs:
            value = old_env.get(setting)
            if value is not None:
                os.environ[setting] = value
            else:
                os.environ.pop(setting, None)

        for field in settings.__fields__:
            object.__setattr__(settings, field, getattr(old_settings, field))
