import asyncio
import functools
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from marvin.engines.language_models import ChatLLM
from marvin.prompts import library as prompt_library
from marvin.prompts import render_prompts
from marvin.tools.format_response import FormatResponse
from marvin.utilities.logging import get_logger
from marvin.utilities.types import LoggerMixin

T = TypeVar("T")


class AIModel(LoggerMixin, BaseModel):
    def __init__(
        self,
        text_: str = None,
        *,
        instructions_: str = None,
        model_: ChatLLM = None,
        **kwargs,
    ):
        """
        Args:
            text_ (str): The text to parse into a structured form. instructions_
            (str): Additional instructions to assist the model. model_
            (ChatLLM): The language model to use.
        """
        # the loggingmixin hasn't been instantiated yet
        logger = get_logger(type(self).__name__)

        if text_:
            if model_ is None:
                model_ = ChatLLM()

            prompts = [
                prompt_library.System(content="""
                        The user will provide context as text that you need to
                        parse into a structured form. To validate your response,
                        you must call the `FormatResponse` function. Use the
                        provided text to extract or infer any parameters needed
                        by `FormatResponse`, including any missing data.
                        """),
                # prompt_library.Now(),
                prompt_library.User(content="""The text to parse: {{ input_text }}"""),
            ]

            if instructions_:
                prompts.append(prompt_library.System(content=instructions_))

            messages = render_prompts(prompts, render_kwargs=dict(input_text=text_))

            retries = 0
            while retries <= 2:
                llm_call = model_.run(
                    messages=messages,
                    functions=[FormatResponse(type_=type(self)).as_openai_function()],
                    function_call={"name": "FormatResponse"},
                )

                response = asyncio.run(llm_call)

                # if the FormatResponse function errored, repeat the call to fix
                # it up to 2 times
                if response.data.get("is_error"):
                    retries += 1
                    if retries > 2:
                        raise TypeError(
                            "Could not build AI Model; most recent error was:"
                            f" {response.content}"
                        )
                    logger.debug(
                        f"Error building AI Model, starting retry attempt {retries}."
                        f" {response.content}"
                    )
                    messages.append(response)
                else:
                    break

            arguments = response.data["arguments"]
            # overwrite with any values provided by the user
            arguments.update(kwargs)
            kwargs = arguments
        super().__init__(**kwargs)


def ai_model(
    cls: Optional[Type[T]] = None,
    *,
    instructions: str = None,
    model: ChatLLM = None,
) -> Type[T]:
    """
    This function allows the AIModel decorator to be used with or without
    calling it. It's a wrapper around the AIModel decorator that adds some extra
    flexibility.
    """
    if cls is None:
        return functools.partial(ai_model, instructions=instructions, model=model)

    # create a new class that subclasses AIModel and the original class
    ai_model_class = type(cls.__name__, (AIModel, cls), {})

    # Use setattr() to add the original class's methods and class variables to
    # the new class do not attempt to copy dunder methods
    for name, attr in cls.__dict__.items():
        if not name.startswith("__"):
            setattr(ai_model_class, name, attr)

    ai_model_class.__init__ = functools.partialmethod(
        ai_model_class.__init__, instructions_=instructions, model_=model
    )

    return ai_model_class
