import functools

import openai
from pydantic import BaseSettings, Field, BaseModel

import marvin
import warnings

from typing import Type, Optional, Union, Literal
from pydantic import Extra


class ChatCompletionConfig(BaseSettings, extra=Extra.allow):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0
    functions: list = Field(default_factory=list)
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

    def merge(self, *args, **kwargs):
        for key, value in kwargs.items():
            if type(value) == list:
                setattr(self, key, getattr(self, key, []) + value)
            else:
                setattr(self, key, value)
        return {k: v for k, v in self.__dict__.items() if v}


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
        if response_model is not None:
            response.to_model = lambda: (
                process_list(
                    list(
                        map(
                            lambda x: response_model.parse_raw(
                                x.message.function_call.arguments
                            ),
                            response.choices,
                        )
                    )
                )
            )
        return response

    @classmethod
    async def acreate(
        cls, *args, response_model: Optional[Type[BaseModel]] = None, **kwargs
    ):
        config = getattr(cls, "__config__", ChatCompletionConfig())
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
        if response_model is not None:
            response.to_model = lambda: (
                process_list(
                    list(
                        map(
                            lambda x: response_model.parse_raw(
                                x.message.function_call.arguments
                            ),
                            response.choices,
                        )
                    )
                )
            )
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
