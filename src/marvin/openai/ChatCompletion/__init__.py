from pydantic import BaseModel, Field, validator, Extra, BaseSettings, root_validator
from pydantic.main import ModelMetaclass

from typing import Any, Callable, List, Optional, Type, Union, Literal
from marvin import settings
from marvin.types import Function
from operator import itemgetter
from marvin.utilities.module_loading import import_string
import warnings
import copy


class Request(BaseSettings):
    """
    This is a class for creating Request objects to interact with the GPT-3 API.
    The class contains several configurations and validation functions to ensure
    the correct data is sent to the API.

    """

    model: str = "gpt-3.5-turbo"  # the model used by the GPT-3 API
    temperature: float = 0.8  # the temperature parameter used by the GPT-3 API
    api_key: str = Field(default_factory=settings.openai.api_key.get_secret_value)
    messages: Optional[List[dict[str, str]]] = None  # messages to send to the API
    functions: List[Union[dict, Callable]] = None  # functions to be used in the request
    function_call: Optional[Union[dict[Literal["name"], str], Literal["auto"]]] = None

    # Internal Marvin Attributes to be excluded from the data sent to the API
    response_model: Optional[Type[BaseModel]] = Field(default=None)
    evaluate_function_call: bool = Field(default=False)

    class Config:
        exclude = {"response_model"}
        exclude_none = True
        extra = Extra.allow

    @root_validator(pre=True)
    def handle_response_model(cls, values):
        """
        This function validates and handles the response_model attribute.
        If a response_model is provided, it creates a function from the model
        and sets it as the function to call.
        """
        response_model = values.get("response_model")
        if response_model:
            fn = Function.from_model(response_model)
            values["functions"] = [fn]
            values["function_call"] = {"name": fn.__name__}
        return values

    @validator("functions", each_item=True)
    def validate_function(cls, fn):
        """
        This function validates the functions attribute.
        If a Callable is provided, it wraps it with the Function class.
        """
        if isinstance(fn, Callable):
            fn = Function(fn)
        return fn

    def __or__(self, config):
        """
        This method is used to merge two Request objects.
        If the attribute is a list, the lists are concatenated.
        Otherwise, the attribute from the provided config is used.
        """
        for field in self.__fields__:
            if isinstance(getattr(self, field), list):
                merged = (getattr(self, field, []) or []) + (
                    getattr(config, field, []) or []
                )
                setattr(self, field, merged)
            else:
                touched = config.dict(exclude_unset=True, serialize_functions=False)
                setattr(self, field, touched.get(field, getattr(self, field)))
        return self

    def merge(self, **kwargs):
        warnings.warn(
            "This is deprecated. Use the | operator instead.", DeprecationWarning
        )
        return self | self.__class__(**kwargs)

    def functions_schema(self, *args, **kwargs):
        """
        This method generates a list of schemas for all functions in the request.
        If a function is callable, its model's schema is returned.
        Otherwise, the function itself is returned.
        """
        return [
            fn.model.schema() if isinstance(fn, Callable) else fn
            for fn in self.functions or []
        ]

    def dict(self, *args, serialize_functions=True, exclude=None, **kwargs):
        """
        This method returns a dictionary representation of the Request.
        If the functions attribute is present and serialize_functions is True,
        the functions' schemas are also included.
        """
        exclude = exclude or {}
        if serialize_functions:
            exclude["evaluate_function_call"] = True
            exclude["response_model"] = True
        response = super().dict(*args, **kwargs, exclude=exclude)
        if response.get("functions") and serialize_functions:
            response.update({"functions": self.functions_schema()})
        return response


class Response(BaseModel):
    """
    This class is used to handle the response from the API.
    It includes several utility functions and properties to extract useful information
    from the raw response.
    """

    raw: dict  # the raw response from the API
    request: Any  # the request that generated the response

    def __init__(self, response, *args, request, **kwargs):
        super().__init__(raw=response, request=request)

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
        if len(self.raw.choices) == 1:
            return next(iter(self.raw.choices)).message
        return [x.message for x in self.raw.choices]

    @property
    def function_call(self):
        """
        This property extracts the function call from the message.
        If the message is a list, it returns a list of function calls from all messages.
        Otherwise, it returns the function call from the message.
        """
        if isinstance(self.message, list):
            return [x.function_call for x in self.message]
        return self.message.function_call

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


class ChatCompletionBase(BaseModel):
    """
    This class is used to create and handle chat completions from the API.
    It provides several utility functions to create the request, send it to the API,
    and handle the response.
    """

    _module: str = "openai.ChatCompletion"  # the module used to interact with the API
    _config: str = "marvin.openai.ChatCompletion.Request"
    defaults: Optional[dict] = Field(None, repr=False)  # default configuration values

    def __init__(self, module_path: str = None, config_path: str = None, **kwargs):
        super().__init__(_module=module_path, _config=config_path, defaults=kwargs)

    @property
    def model(self):
        """
        This property imports and returns the API model.
        """
        return import_string(self._module)

    def config(self, *args, **kwargs) -> Request:
        """
        This method imports and returns a configuration object.
        """
        return import_string(self._config)(*args, **(kwargs or self.defaults or {}))

    def create(self=None, *args, **kwargs):
        """
        This method creates a request and sends it to the API.
        It returns a Response object with the raw response and the request.
        """
        request = self.config() | self.config(**kwargs)
        payload = request.dict(exclude_none=True, exclude_unset=True)
        response = Response(self.model.create(**payload), request=request)
        if request.evaluate_function_call and response.function_call:
            return response.call_function(as_message=True)
        return response

    async def acreate(self, *args, **kwargs):
        """
        This method is an asynchronous version of the create method.
        It creates a request and sends it to the API asynchronously.
        It returns a Response object with the raw response and the request.
        """
        request = self.config() | self.config(**kwargs)
        payload = request.dict(exclude_none=True, exclude_unset=True)
        response = Response(await self.model.acreate(**payload), request=request)
        if request.evaluate_function_call and response.function_call:
            return response.call_function(as_message=True)
        return response

    def __call__(self, *args, **kwargs):
        self = copy.deepcopy(self)
        config = self.config()
        passed = self.__class__(**kwargs).config()
        self.defaults = (config | passed).dict(serialize_functions=False)
        return self


ChatCompletion = ChatCompletionBase()

# This is a legacy class that is used to create a ChatCompletion object.
# It is deprecated and will be removed in a future release.
ChatCompletionConfig = Request
