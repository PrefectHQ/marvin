import functools

import openai
from pydantic import BaseSettings, Field, validator

import marvin


class ChatCompletionConfig(BaseSettings):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0
    functions: list = Field(default_factory=list)
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
        return {k: v for k, v in self.__dict__.items() if v != []}


class ChatCompletion(openai.ChatCompletion):
    def __new__(cls, *args, **kwargs):
        subclass = type(
            "ChatCompletion",
            (ChatCompletion,),
            {"__config__": ChatCompletionConfig(**kwargs)},
        )
        return subclass

    @classmethod
    def create(cls, *args, **kwargs):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        payload = config.merge(**kwargs)
        return cls.observer(super(ChatCompletion, cls).create)(*args, **payload)

    @classmethod
    async def acreate(cls, *args, **kwargs):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        payload = config.merge(**kwargs)
        return await cls.observer(super(ChatCompletion, cls).acreate)(*args, **payload)

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
