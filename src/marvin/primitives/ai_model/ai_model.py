import asyncio
import functools
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from marvin.engines.language_models import ChatLLM
from marvin.functions.prompts import render_prompts
from marvin.prompts import System, User
from marvin.tools.format_response import FormatResponse

T = TypeVar("T")

ai_model_prompts = [
    System(content="""
            The user will provide context through text that you need to parse
            into a structured form that is compatible with `FormatResponse`.
            Based on the text, extract or infer any parameters needed by
            `FormatResponse`, including any missing data.
            """),
    User(content="""The text to parse: {{ input_text }}"""),
]


class AIModel(BaseModel):
    def __init__(self, text: str = None, model: ChatLLM = None, **kwargs):
        if text:
            if model is None:
                model = ChatLLM()
            messages = render_prompts(
                ai_model_prompts, render_kwargs=dict(input_text=text)
            )
            print(messages)
            llm_call = model.run(
                messages=messages,
                functions=[FormatResponse(type_=type(self)).as_openai_function()],
                function_call={"name": "FormatResponse"},
            )

            response = asyncio.run(llm_call)
            arguments = response.data["arguments"]
            # overwrite with any values provided by the user
            arguments.update(kwargs)
            kwargs = arguments
        super().__init__(**kwargs)


def ai_model(cls: Optional[Type[T]] = None) -> Type[T]:
    """
    This function allows the AIModel decorator to be used with or without
    calling it. It's a wrapper around the AIModel decorator that adds some
    extra flexibility.
    """
    if cls is None:
        return functools.partial(ai_model)

    # create a new class that subclasses AIModel and the original class
    ai_model_class = type(cls.__name__, (AIModel, cls), {})

    # Use setattr() to add the original class's methods and class variables to
    # the new class do not attempt to copy dunder methods
    for name, attr in cls.__dict__.items():
        if not name.startswith("__"):
            setattr(ai_model_class, name, attr)

    return ai_model_class
