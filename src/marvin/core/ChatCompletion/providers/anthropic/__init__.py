from marvin.pydantic import Field, SecretStr, BaseModel, PrivateAttr
import re
from marvin.utilities.module_loading import import_string
from typing import Optional
from anthropic import AI_PROMPT, HUMAN_PROMPT
from functools import cached_property
from .prompts import FUNCTION_PROMPT as FunctionCallPrompt
from marvin.core.ChatCompletion.base import (
    BaseChatCompletion,
    BaseChatCompletionSettings,
    BaseChatRequest,
    BaseChatResponse,
)
from marvin.utilities.strings import jinja_env


class ChatCompletionSettings(BaseChatCompletionSettings):
    """
    Provider-specific settings.
    """

    model: str = "claude-2"
    api_key: SecretStr = Field(
        None, env=["MARVIN_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"]
    )
    _function_call_prompt: str = f"{__name__}.FunctionCallPrompt"
    max_tokens_to_sample: int = 1000

    @property
    def function_call_prompt(self):
        return import_string(self._function_call_prompt)

    class Config(BaseChatCompletionSettings.Config):
        exclude_none = True
        exclude = {"api_key"}


class ChatRequest(BaseChatRequest):
    prompt: Optional[str] = Field(default=None)
    _config: ChatCompletionSettings = PrivateAttr(
        default_factory=ChatCompletionSettings
    )

    class Config(BaseChatRequest.Config):
        exclude = BaseChatRequest.Config.exclude.union(
            {"messages", "api_key", "functions", "function_call"}
        )


class ChatResponse(BaseChatResponse):
    @property
    def choices(self):
        # TODO: This is a hack, should use native classes
        class AttrDict(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        return [
            AttrDict(
                **{
                    "index": 0,
                    "message": AttrDict(
                        **{
                            "role": "assistant",
                            "content": self.raw.completion,
                        }
                    ),
                    "finish_reason": "stop",
                }
            )
        ]

    @property
    def message(self):
        """
        This property extracts the message from the raw response.
        If there is only one choice, it returns the message from that choice.
        Otherwise, it returns a list of messages from all choices.
        """
        return self.raw.completion

    def function_call(self, *args, **kwargs):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """

        class AnthropicFunctionCall(BaseModel):
            mode: str
            name: str
            arguments: str

            @classmethod
            def parse_raw(cls, raw: str):
                return super().parse_raw(re.sub("^[^{]*|[^}]*$", "", raw))

        return AnthropicFunctionCall.parse_raw(self.message)


class ChatCompletion(BaseChatCompletion):
    _module: str = "anthropic.Anthropic"
    _create: str = "create"
    _acreate: str = "acreate"

    _request_class: ChatRequest = ChatRequest
    _response_class: ChatResponse = ChatResponse

    def model(self, request):
        """
        This property returns the model name.
        """
        return self.module(
            api_key=request._config.api_key.get_secret_value()
        ).completions

    def prepare_request(self, **kwargs):
        """
        This method prepares the request for the API call.
        It sets the prompt to the messages in the request.
        """
        request = super().prepare_request(**kwargs)
        request.prompt = ""
        if next(iter(request.messages), {}).get("content", None) != "user":
            request.prompt += HUMAN_PROMPT
        request.prompt += " ".join(
            [
                "{prompt} {content}".format(
                    prompt={"user": HUMAN_PROMPT}.get(message.get("role"), AI_PROMPT),
                    content=message.get("content", ""),
                )
                for message in request.messages
            ]
        )
        if request.functions:
            request.prompt += (
                AI_PROMPT
                + " "
                + jinja_env.from_string(request._config.function_call_prompt).render(
                    functions=request.schema(exclude=set()).get("functions"),
                    function_call=request.function_call,
                )
            )
        request.prompt += AI_PROMPT
        return request
