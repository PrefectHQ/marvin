import functools

import openai
from pydantic import BaseSettings, Field, BaseModel

import marvin
import warnings

from typing import Type, Optional, Union, Literal, Callable
from pydantic import Extra, validator
from marvin.types import Function
from functools import partial


class ChatCompletionConfig(BaseSettings, extra=Extra.allow):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0
    functions: Optional[list[Union[dict, Callable]]] = Field(default_factory=list)
    function_call: Optional[Union[dict[Literal["name"], str], Literal["auto"]]] = None
    messages: list = Field(default_factory=list)

    api_key: str = Field(
        default_factory=lambda: (
            marvin.settings.openai.api_key.get_secret_value()
            if marvin.settings.openai.api_key is not None
            else None
        ),
        env="OPENAI_API_KEY",
    )

    @validator("functions")
    def validate_function(cls, functions):
        functions = [
            Function(fn) if isinstance(fn, Callable) else fn for fn in functions or []
        ]
        return functions

    def merge(self, *args, **kwargs):
        # We take the dict of default params.
        default = self.dict(exclude_none=True)

        # We take the dict of given params.

        _passed = self.__class__(**kwargs).dict(exclude_unset=True)

        # We let _passed overwrite default params for all types,
        # except lists, where we concatenate them.
        for key, value in _passed.items():
            # if the value is a list, we merge
            if isinstance(value, list):
                _passed[key] = default.get(key, []) + value

        response = {**default, **_passed}

        # If there are functions, we convert callables to their schemas.

        if response.get("functions"):
            response["functions"] = [
                fn.schema() if isinstance(fn, Callable) else fn
                for fn in response.get("functions")
            ]

        return {k: v for k, v in response.items() if v}


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
