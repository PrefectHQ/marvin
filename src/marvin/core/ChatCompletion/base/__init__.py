from marvin.pydantic import BaseModel, BaseSettings, Extra, Field, SecretStr
from marvin.settings import ENV_PATH
from typing import Callable, Literal, Optional, Union, Type, Any
import os
from pathlib import Path
from marvin.types import Function
from functools import cached_property
from marvin.utilities.module_loading import import_string
from operator import itemgetter

import json

from .abstract import (
    AbstractChatCompletion,
    AbstractChatCompletionSettings,
    AbstractChatRequest,
    AbstractChatResponse,
    AbstractChatCompletionFunctionCall,
)


class BaseChatCompletionSettings(BaseSettings, AbstractChatCompletionSettings):
    class Config:
        env_file = (".env", ENV_PATH)
        env_prefix = "MARVIN_"
        validate_assignment = True

    def dict(self, exclude_none=True, evaluate_secrets=True, exclude=None, **kwargs):
        exclude = (exclude or set()).union(getattr(self.Config, "exclude", set()))
        response = super().dict(exclude_none=exclude_none, exclude=exclude, **kwargs)
        if evaluate_secrets:
            for k, v in response.items():
                if isinstance(v, SecretStr):
                    response[k] = v.get_secret_value()
        return response


class BaseChatRequest(BaseModel, AbstractChatRequest):
    _config: Type[BaseChatCompletionSettings]
    messages: list[dict[str, str]] = []
    functions: Optional[list[Callable, dict[str, str]]] = None
    function_call: Optional[Union[Literal["auto"], dict[Literal["name"], str]]] = None

    _response_model: Optional[Type[BaseModel]] = Field(None, alias="response_model")
    _evaluate_function_call: bool = Field(False, alias="evaluate_function_call")

    class Config:
        extra = Extra.allow
        exclude = {"_response_model", "_evaluate_function_call"}
        merge = {"functions", "messages"}

    def __init__(self, *args, **kwargs):
        if "response_model" in kwargs:
            fn = Function.from_model(kwargs.get("response_model"))
            kwargs |= {"functions": [fn], "function_call": {"name": fn.__name__}}
            kwargs["_response_model"] = kwargs.pop("response_model")

        if "functions" in kwargs:
            kwargs["functions"] = [
                Function(f) if isinstance(f, Callable) else f
                for f in kwargs.pop("functions", []) or []
            ] or None
        super().__init__(*args, **kwargs)

    def schema(self, exclude_none: bool = True, exclude: set = None, **kwargs):
        response = super().dict(
            exclude_none=exclude_none,
            **kwargs,
            exclude=(
                exclude if exclude is not None else (set().union(self.Config.exclude))
            ),
        )
        if response.get("functions", None):
            response["functions"] = [
                Function(f).model.schema() if isinstance(f, Callable) else f
                for f in response.get("functions", [])
            ] or None

        return response

    def dict(self, *args, **kwargs):
        return {**self._config.dict(), **super().dict(*args, **kwargs)}

    def json(self, *args, **kwargs):
        return json.dumps(self.to_request(), *args, **kwargs)

    def merge(self, *args, **kwargs):
        for kwarg in kwargs:
            if kwarg in self.Config.merge:
                setattr(self, kwarg, (getattr(self, kwarg, []) or []) + kwargs[kwarg])
            else:
                setattr(self, kwarg, kwargs[kwarg])
        return self.__class__(**self.dict())


class BaseChatResponse(BaseModel, AbstractChatResponse):
    raw: Any
    request: BaseChatRequest

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
        return self.request._response_model.parse_raw(self.function_call.arguments)


class BaseChatCompletion(BaseModel, AbstractChatCompletion):
    _module: str
    _request_class: str
    _response_class: str
    _create: str
    _acreate: str
    _defaults: dict = None

    @property
    def module(self):
        return import_string(self._module)

    def model(self, *args, **kwargs):
        return self.module

    @property
    def request(self):
        return import_string(self._request_class)

    @property
    def response(self):
        return import_string(self._response_class)

    def prepare_request(self, **kwargs):
        return self.request(**self._defaults, **self.dict(exclude={"_defaults"})).merge(
            **kwargs
        )

    def create(self, *args, **kwargs):
        request = self.prepare_request(**kwargs)
        request_dict = request.schema()
        return self.response(
            raw=self.model(request).create(*args, **request_dict), request=request
        )

    async def acreate(self, *args, **kwargs):
        request = self.prepare_request(**kwargs)
        request_dict = request.schema()
        return self.response(
            raw=await self.model(request).acreate(*args, **request_dict),
            request=request,
        )

    class Config:
        keep_untouched = (cached_property,)
        exclude = {"_defaults"}
        extra = Extra.allow
