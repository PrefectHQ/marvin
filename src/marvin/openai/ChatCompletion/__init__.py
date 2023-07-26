import functools

import openai
from pydantic import BaseSettings, Field, BaseModel

import marvin
import warnings

from typing import Type, Optional, Union, Literal, Callable, List
from pydantic import Extra, validator
from marvin.types import Function
from functools import partial
from marvin import settings


class ChatCompletionConfig(BaseSettings, extra=Extra.allow):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.8
    api_key: str = Field(default_factory=settings.openai.api_key.get_secret_value)
    messages: Optional[List[dict[str, str]]] = None
    functions: List[Union[dict, Callable]] = None
    function_call: Optional[Union[dict[Literal["name"], str], Literal["auto"]]] = None

    def dict(self, *args, exclude_none=True, **kwargs):
        response = super().dict(*args, exclude_none=exclude_none, **kwargs)
        # Cast functions to list of dicts
        if response.get("functions"):
            response["functions"] = [
                x.model.schema() if isinstance(x, Callable) else x
                for x in response["functions"]
            ]
        return response

    @validator("functions", each_item=True)
    def validate_function(cls, fn):
        if isinstance(fn, Callable):
            fn = Function(fn)
        return fn

    def __call__(self, **kwargs):
        """
        Takes in new config kwargs and
        - Overwrites attrs with new passed kwargs, with exception:
        - Concatenates attrs that are lists
        """
        # We'll validate the passed kwargs.
        passed = self.__class__(**kwargs)

        if self.functions or passed.functions:
            passed.functions = (self.functions or []) + (passed.functions or [])
        if self.messages or passed.messages:
            passed.messages = (self.messages or []) + (passed.messages or [])

        return self.__class__(
            **{
                **self.dict(),
                **passed.dict(exclude_unset=True),
                "functions": passed.functions,
                "messages": passed.messages,
            }
        )


def get_function_call(response):
    try:
        return list(map(lambda x: x.message.function_call, response.choices))
    except AttributeError:
        return None


def get_preval(function_call, functions):
    return [
        {fn.__name__: fn for fn in functions if isinstance(fn, Callable)}.get(
            function_call.name
        ),
        function_call.arguments,
    ]


def process_list(lst):
    if len(lst) == 1:
        return lst[0]
    else:
        return lst


class ChatCompletion(openai.ChatCompletion):
    def __new__(cls, *args, **kwargs):
        subclass = type(
            "ChatCompletion",
            (ChatCompletion,),
            {"__config__": ChatCompletionConfig(**kwargs)},
        )
        return subclass

    @classmethod
    def create(cls, *args, response_model: Optional[Type[BaseModel]] = None, **kwargs):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        passed_config = ChatCompletionConfig(**kwargs)

        functions = [*config.functions, *passed_config.functions]

        if response_model is not None:
            if kwargs.get("functions"):
                warnings.warn("Use of response_model with functions is not supported")
            else:
                kwargs["functions"] = [
                    {
                        "name": "format_response",
                        "description": "Format the response",
                        "parameters": response_model.schema(),
                    }
                ]
                kwargs["function_call"] = {
                    "name": "format_response",
                }
        payload = config.merge(**kwargs)
        response = cls.observer(super(ChatCompletion, cls).create)(*args, **payload)

        response = type(
            response.__class__.__name__,
            (response.__class__,),
            {
                "evaluate": partial(
                    cls.evaluate, response=response, functions=functions
                ),
                "to_model": partial(
                    cls.to_model, response=response, response_model=response_model
                ),
            },
        )(response.to_dict_recursive())

        return response

    @classmethod
    def evaluate(cls, response, functions):
        function_call = get_function_call(response) or []
        return process_list(
            [
                fn.evaluate_raw(args, fn=fn) if isinstance(fn, Callable) else fn
                for fn, args in [get_preval(call, functions) for call in function_call]
            ]
        )

    @classmethod
    def to_model(cls, response, response_model):
        return process_list(
            list(
                map(
                    response_model.parse_raw,
                    [
                        function_call.arguments
                        for function_call in get_function_call(response)
                    ],
                )
            )
        )

    @classmethod
    async def acreate(
        cls, *args, response_model: Optional[Type[BaseModel]] = None, **kwargs
    ):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        passed_config = ChatCompletionConfig(**kwargs)

        functions = [*config.functions, *passed_config.functions]

        if response_model is not None:
            if kwargs.get("functions"):
                warnings.warn("Use of response_model with functions is not supported")
            else:
                kwargs["functions"] = [
                    {
                        "name": "format_response",
                        "description": "Format the response",
                        "parameters": response_model.schema(),
                    }
                ]
                kwargs["function_call"] = {
                    "name": "format_response",
                }
        payload = config.merge(**kwargs)
        response = await cls.observer(super(ChatCompletion, cls).acreate)(
            *args, **payload
        )

        response = type(
            response.__class__.__name__,
            (response.__class__,),
            {
                "evaluate": partial(
                    cls.evaluate, response=response, functions=functions
                ),
                "to_model": partial(
                    cls.to_model, response=response, response_model=response_model
                ),
            },
        )(response.to_dict_recursive())

        return response

    @staticmethod
    def observer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ChatCompletion.on_send(*args, **kwargs)
            response = func(*args, **kwargs)
            response = ChatCompletion.on_receive(response, *args, **kwargs)
            return response

        return wrapper

    @classmethod
    def on_send(cls, *args, **kwargs):
        pass

    @classmethod
    def on_receive(cls, result, *args, **kwargs):
        return result
