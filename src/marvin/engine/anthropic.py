from operator import itemgetter
from typing import Any, Callable, Optional

from anthropic import AI_PROMPT, HUMAN_PROMPT
from jinja2 import Template
from pydantic import BaseModel, Extra, Field, root_validator

from marvin import settings
from marvin.engine import ChatCompletionBase
from marvin.engine.language_models.anthropic import AnthropicFunctionCall
from marvin.types.request import Request as BaseRequest
from marvin.utilities.module_loading import import_string


class Request(BaseRequest):
    """
    This is a class for creating Request objects to interact with the GPT-3 API.
    The class contains several configurations and validation functions to ensure
    the correct data is sent to the API.

    """

    model: str = "claude-2"  # the model used by the GPT-3 API
    # temperature: float = 0.8  # the temperature parameter used by the GPT-3 API
    api_key: str = Field(default_factory=settings.anthropic.api_key.get_secret_value)
    max_tokens_to_sample: int = Field(default=1000)
    prompt: str = Field(default="")

    class Config:
        exclude = {"response_model", "messages"}
        exclude_none = True
        extra = Extra.allow
        functions_prompt = (
            "marvin.engine.language_models.anthropic.FUNCTIONS_INSTRUCTIONS"
        )

    @root_validator(pre=True)
    def to_anthropic(cls, values):
        values["prompt"] = ""
        for message in values.get("messages", []):
            if message.get("role") == "user":
                values["prompt"] += f'{HUMAN_PROMPT} {message.get("content")}'
            else:
                values["prompt"] += f'{AI_PROMPT} {message.get("content")}'
        values["prompt"] += f"{AI_PROMPT} "
        return values

    def dict(self, *args, serialize_functions=True, **kwargs):
        """
        This method returns a dictionary representation of the Request.
        If the functions attribute is present and serialize_functions is True,
        the functions' schemas are also included.
        """

        # This identity function is here for no reason except to show
        # readers that custom adapters need only override the dict method.
        return super().dict(*args, serialize_functions=serialize_functions, **kwargs)


class Response(BaseModel):
    """
    This class is used to handle the response from the API.
    It includes several utility functions and properties to extract useful information
    from the raw response.
    """

    raw: Any  # the raw response from the API
    request: Any  # the request that generated the response

    def __init__(self, response, *args, request, **kwargs):
        super().__init__(raw=response, request=request)

    def __iter__(self):
        return self.raw.__iter__()

    def __next__(self):
        return self.raw.__next__()

    def __getattr__(self, name):
        """
        This method attempts to get the attribute from the raw response.
        If it doesn't exist, it falls back to the standard attribute access.
        """
        try:
            return self.raw.__getattr__(name)
        except AttributeError:
            return self.__getattribute__(name)

    @property
    def message(self):
        """
        This property extracts the message from the raw response.
        If there is only one choice, it returns the message from that choice.
        Otherwise, it returns a list of messages from all choices.
        """
        return self.raw.completion

    @property
    def function_call(self):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """

        return AnthropicFunctionCall.parse_raw(self.message).dict(
            exclude={"function_call"}
        )

    @property
    def callables(self):
        """
        This property returns a list of all callable functions from the request.
        """
        return [x for x in self.request.functions if isinstance(x, Callable)]

    @property
    def callable_registry(self):
        """
        This property returns a dictionary mapping function names to functions for all
        callable functions from the request.
        """
        return {fn.__name__: fn for fn in self.callables}

    def call_function(self, as_message=True):
        """
        This method evaluates the function call in the response and returns the result.
        If as_message is True, it returns the result as a function message.
        Otherwise, it returns the result directly.
        """
        name, raw_arguments = itemgetter("name", "arguments")(self.function_call)
        function = self.callable_registry.get(name)
        arguments = function.model.parse_raw(raw_arguments)
        value = function(**arguments.dict(exclude_none=True))
        if as_message:
            return {"role": "function", "name": name, "content": value}
        else:
            return value

    def to_model(self):
        """
        This method parses the function call arguments into the response model and
        returns the result.
        """
        return self.request.response_model.parse_raw(self.function_call.arguments)

    def __repr__(self, *args, **kwargs):
        """
        This method returns a string representation of the raw response.
        """
        return self.raw.__repr__(*args, **kwargs)


class AnthropicChatCompletion(ChatCompletionBase):
    """
    This class is used to create and handle chat completions from the API.
    It provides several utility functions to create the request, send it to the API,
    and handle the response.
    """

    _module: str = "anthropic.Anthropic"  # the module used to interact with the API
    _request: str = "marvin.engine.anthropic.Request"
    _response: str = "marvin.engine.anthropic.Response"
    defaults: Optional[dict] = Field(None, repr=False)  # default configuration values

    @property
    def model(self):
        """
        This property imports and returns the API model.
        """
        return self.module(
            api_key=self.request().api_key,
        ).completions

    def prepare_request(self, *args, **kwargs):
        request, payload = super().prepare_request(*args, **kwargs)
        payload.pop("messages", None)
        payload.pop("api_key", None)
        if payload.get("functions", None):
            functions_prompt = Template(
                import_string(request.Config.functions_prompt)
            ).render(
                functions=payload.get("functions"),
                function_call=payload.get("function_call"),
            )
            payload["prompt"] = f"{HUMAN_PROMPT} {functions_prompt}" + payload["prompt"]
            payload.pop("functions", None)
        return request, payload


ChatCompletion = AnthropicChatCompletion()

# This is a legacy class that is used to create a ChatCompletion object.
# It is deprecated and will be removed in a future release.
ChatCompletionConfig = Request
