import asyncio
import inspect
from functools import partial, wraps
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import pydantic
from prefect import flow, task
from prefect.utilities.asyncutils import sync_compatible

from marvin import ai_fn
from marvin.bot import Bot
from marvin.bot.response_formatters import PydanticFormatter
from marvin.models.threads import Message
from marvin.utilities.llms import call_llm_messages, get_model

M = TypeVar("M", bound=pydantic.BaseModel)

Context = Union[str, Tuple[str, Optional[Dict[str, Any]]]]


def unstructured_context_handler(func):
    """
    This decorator allows the model to accept a single positional string
    argument as the context during initialization.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        context = {}
        # If the first argument is a string, we assume it is the context.
        if next(iter(args), None) and isinstance(next(iter(args), None), str):
            context = {"__marvin_context__": args[0]}
        func(self, **{**context, **kwargs})

    return wrapper


AI_MODEL_INSTRUCTIONS = inspect.cleandoc("""
    Given unstructured `context` infer, impute, and deduce when possible the
    missing data.
    """)


def AIModel(
    cls: Optional[Type[M]],
    *,
    bot: Bot = None,
    **bot_kwargs,
) -> Type[M]:
    """
    This decorator modifies a Pydantic model class to be able to impute missing
    values from an unstructured context using an AI model. The AI model can be
    either a built-in or an external one, provided via the 'bot' parameter.
    """

    def as_function(cls, description=None):
        """
        This method returns the metadata for the model that can be used to call it
        as a function.
        """
        return {
            "name": "deduce_infer_and_extract",
            "description": description or AI_MODEL_INSTRUCTIONS,
            "parameters": cls.schema(),
        }

    cls.as_function = classmethod(as_function)

    def _ai_imputer_base(context: str) -> cls:
        f"""{AI_MODEL_INSTRUCTIONS}"""

    def _ai_imputer_plugin(cls, context: str) -> cls:
        model = get_model()
        output = asyncio.run(
            call_llm_messages(
                model,
                messages=[
                    Message(
                        role="system",
                        content=(
                            "Your goal is to infer, extrapolate, and "
                            "interpolate structured data from user provided context. "
                            "- If you choose a tool it must validate against the "
                            "schema provided."
                        ),
                    ),
                    Message(role="user", content=f"Context: {context}"),
                ],
                functions=[cls.as_function()],
                function_call={"name": cls.as_function()["name"]},
            )
        )
        print(output.dict())
        parsed_output = cls.parse_raw(
            output.additional_kwargs.get("function_call", {}).get("arguments", "")
        )
        return parsed_output

    def ai_validator(cls, values):
        # Check if a __marvin_context__ has been passed in the init method.
        __context__ = values.pop("__marvin_context__", None)
        # If __marvin_context__ has been passed, use an ai_fn to impute the values.
        if __context__:
            model = get_model()
            if model.__class__.__name__ == "ChatOpenAI":
                ai_imputer = cls._ai_imputer_plugin

            else:
                ai_imputer = ai_fn(
                    _ai_imputer_base,
                    bot=bot,
                    bot_kwargs={
                        **bot_kwargs,
                        "response_format": PydanticFormatter(model=cls),
                    },
                )
            try:
                return {**ai_imputer(context=__context__).dict(), **values}
            except Exception:
                return values
        return values

    # Wrap the __init__ method with the unstructured_context_handler decorator
    cls.__init__ = unstructured_context_handler(cls.__init__)

    # Add the ai_validator as a preroot validator to run before other root validators
    cls.__pre_root_validators__ = [ai_validator, *cls.__pre_root_validators__]

    @sync_compatible
    async def map(
        cls,
        contexts: List[Context],
        task_kwargs: Dict[str, Any] = None,
        flow_kwargs: Dict[str, Any] = None,
    ) -> List[M]:
        """
        This method maps the AIModel over a list of contexts and returns the
        processed results. The contexts can be either strings or tuples
        consisting of a string and an optional dictionary.
        """

        @task(**{"name": cls.__name__, **(task_kwargs or {})})
        async def process_item(context: Context):
            if isinstance(context, str):
                return cls(context)
            elif isinstance(context, tuple):
                unstructured, structured = context
                return cls(unstructured, **(structured or {}))
            else:
                raise TypeError(
                    "`Context` must be a `str` or a `Tuple[str, Optional[Dict[str,"
                    " Any]]]`, not {type(context)}"
                )

        @flow(**{"name": cls.__name__, **(flow_kwargs or {})})
        async def mapped_ai_fn(contexts: List[Context]):
            return await process_item.map(contexts)

        return [await state.result().get() for state in await mapped_ai_fn(contexts)]

    cls._ai_imputer_plugin = classmethod(_ai_imputer_plugin)
    cls.map = classmethod(map)
    return cls


def ai_model(
    cls: Optional[Type[M]] = None,
    *,
    bot: Bot = None,
    **bot_kwargs,
) -> Type[M]:
    """
    This function allows the AIModel decorator to be used with or without
    calling it. It's a wrapper around the AIModel decorator that adds some
    extra flexibility.
    """
    if cls is None:
        return partial(ai_model, bot=bot, **bot_kwargs)
    return AIModel(cls=cls, bot=bot, bot_kwargs=bot_kwargs)
