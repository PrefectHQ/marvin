from marvin.pydantic import Field, SecretStr, PrivateAttr
import tiktoken
from marvin.utilities.module_loading import import_string
from marvin.core.ChatCompletion.base import (
    BaseChatCompletion,
    BaseChatCompletionSettings,
    BaseChatRequest,
    BaseChatResponse,
)
import os
from marvin._compat import model_dump


class ChatCompletionSettings(BaseChatCompletionSettings):
    """
    Provider-specific settings.
    """

    model: str = "gpt-3.5-turbo"
    api_key: SecretStr = Field(None, env=["MARVIN_OPENAI_API_KEY", "OPENAI_API_KEY"])
    organization: str = Field(None)
    api_type: str = None
    api_base: str = Field(None, description="The endpoint the OpenAI API.")
    api_version: str = Field(None, description="The API version")
    max_tokens: int = Field(
        default=1500, description="The max number of tokens for AI completions"
    )
    temperature: float = Field(default=0.8)
    request_timeout: float = Field(default=600.0)

    def __init__(self, *args, **kwargs):
        from marvin import settings

        defaults = {
            k: v
            for (k, v) in model_dump(settings.openai).items()
            if k in self.__fields__ and v is not None
        }

        defaults["max_tokens"] = settings.llm_max_tokens
        defaults["temperature"] = settings.llm_temperature
        defaults["request_timeout"] = settings.llm_request_timeout_seconds

        super().__init__(*args, **{**defaults, **kwargs})

        from marvin import openai, settings

        if openai.api_key or settings.openai.api_key:
            """
            TODO: Simplify this experience. We're technically on the hook here
            since we provide mutating runtime settings AND setting openai.api_key
            = 'whatever.
            """
            from marvin import openai, settings

            if key := os.environ.get("MARVIN_OPENAI_API_KEY", None):
                self.api_key = key
            elif key := os.environ.get("OPENAI_API_KEY", None):
                self.api_key = key
            elif openai.api_key:
                self.api_key = openai.api_key
            elif settings.openai.api_key:
                self.api_key = settings.openai.api_key.get_secret_value()

    class Config(BaseChatCompletionSettings.Config):
        env_prefix = "MARVIN_OPENAI_"
        exclude_none = True


class ChatRequest(BaseChatRequest):
    _config: ChatCompletionSettings = PrivateAttr(
        default_factory=ChatCompletionSettings
    )


class ChatResponse(BaseChatResponse):
    @property
    def message(self):
        """
        This property extracts the message from the raw response.
        If there is only one choice, it returns the message from that choice.
        Otherwise, it returns a list of messages from all choices.
        """
        if len(self.raw.choices) == 1:
            return next(iter(self.raw.choices)).message
        return [x.message for x in self.raw.choices]

    def function_call(self, *args, **kwargs):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """
        if isinstance(self.message, list):
            return [x.function_call for x in self.message]
        return getattr(self.message, "function_call", None)


class ChatCompletion(BaseChatCompletion):
    _module: str = "openai.ChatCompletion"
    _create: str = "create"
    _acreate: str = "acreate"

    _request_class: ChatRequest = ChatRequest
    _response_class: ChatResponse = ChatResponse

    def prepare_request(self, **kwargs):
        """
        Nothing to change since BaseChatCompletion is designed
        off of the OpenAI API.
        """
        return super().prepare_request(**kwargs)

    def get_tokens(self, text: str, **kwargs) -> list[int]:
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return enc.encode(text)


OpenAIChatCompletion = ChatCompletion()
