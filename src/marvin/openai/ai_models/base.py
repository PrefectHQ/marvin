import asyncio
import functools
from typing import Optional, Type, TypeVar

import pydantic

from marvin.models.threads import Message
from marvin.openai.tools.format_response import FormatResponse
from marvin.utilities.openai import call_llm_chat

T = TypeVar("T")


class AIModel(pydantic.BaseModel):
    def __init__(self, text: str = None, **kwargs):
        if text:
            llm_call = call_llm_chat(
                messages=[
                    Message(
                        role="system",
                        content=(
                            "The user will provide context through text that you need"
                            " to parse into a structured form that is compatible with"
                            " the FormatResponse function. Based on the text, extract"
                            " or infer any parameters needed by FormatResponse,"
                            " including any missing data. You must call"
                            " FormatResponse to validate your answer before"
                            " responding to the user."
                        ),
                    ),
                    Message(role="user", content=f"Text to parse: {text}"),
                ],
                functions=[FormatResponse(type_=type(self)).as_openai_function()],
                function_call={"name": "FormatResponse"},
            )

            response = asyncio.run(llm_call)
            llm_kwargs = response.data["result"]
            # overwrite with any values provided by the user
            llm_kwargs.update(kwargs)
            kwargs = llm_kwargs
        super().__init__(**kwargs)


def ai_model(
    cls: Optional[Type[T]] = None,
) -> Type[T]:
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
