import asyncio
import functools
from typing import Optional, Type, TypeVar

import pydantic

from marvin.models.threads import Message
from marvin.openai.tools.format_response import FormatResponse
from marvin.utilities.llms import call_llm_with_tools, get_model

T = TypeVar("T")


class AIModel(pydantic.BaseModel):
    def __init__(self, text: str = None, **kwargs):
        if text:
            llm = get_model()
            llm_call = call_llm_with_tools(
                llm,
                messages=[
                    Message(
                        role="system",
                        content=(
                            "The user will provide text that you need to parse into a"
                            " structured form that is compatible with the"
                            " FinalizeResponse function. Extract or infer any"
                            " parameters from the user's text, including any missing"
                            " data. You must call FinalizeResponse to validate your"
                            " answer before responding to the user."
                        ),
                    ),
                    Message(role="user", content=f"Text to parse: {text}"),
                ],
                tools=[FormatResponse(type_=type(self))],
                function_call={"name": "FormatResponse"},
            )

            model = asyncio.run(llm_call)
            llm_kwargs = model.dict()
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
