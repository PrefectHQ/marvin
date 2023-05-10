from functools import partial, wraps
from typing import Optional, Type, TypeVar

import pydantic

from marvin import ai_fn
from marvin.bot import Bot
from marvin.bot.response_formatters import PydanticFormatter

M = TypeVar("M", bound=pydantic.BaseModel)


def AIModel(
    cls: Optional[Type[M]],
    *,
    bot: Bot = None,
    **bot_kwargs,
) -> Type[M]:
    def __unstructured_context_handler__(func):
        # wrapper to handle a single positional `str` in the __init__ method.
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            context = {}
            # If the first argument is a string, we assume it is the context.
            if next(iter(args), None) and isinstance(next(iter(args), None), str):
                context = {"__marvin_context__": args[0]}
            func(self, **{**context, **kwargs})

        return wrapper

    def _ai_imputer_base(context: str) -> cls:
        """
        Given unstructured text infer when possible the missing data.
        """

    def _ai_validator(cls, values):
        # Check if a __marvin_context__ has been passed in the init method.
        __context__ = values.pop("__marvin_context__", None)
        # If __marvin_context__ has been passed, use an ai_fn to impute the values.
        if __context__:
            # use ai_fn  to create a function that will be used to impute the values.
            ai_imputer = ai_fn(
                _ai_imputer_base,
                bot=bot,
                bot_kwargs={
                    **bot_kwargs,
                    "response_format": PydanticFormatter(model=cls),
                },
            )
            # We'll attempt to impute the values using the ai_imputer function.
            try:
                return {**ai_imputer(context=__context__).dict(), **values}
            # If the ai_imputer function fails, we'll simply return the values.
            except Exception:  # TODO: Add a custom exception here.
                return values
        return values

    # wrap the __init__ method in __unstructured_context_handler__
    cls.__init__ = __unstructured_context_handler__(cls.__init__)

    # add _ai_validator as a pre root validator to run before any other root validators.
    cls.__pre_root_validators__ = [_ai_validator, *cls.__pre_root_validators__]
    return cls


def ai_model(
    cls: Optional[Type[M]] = None,
    *,
    bot: Bot = None,
    **bot_kwargs,
) -> Type[M]:
    # this allows the decorator to be used with or without calling it
    if cls is None:
        return partial(ai_model, bot=bot, **bot_kwargs)
    return AIModel(cls=cls, bot=bot, bot_kwargs=bot_kwargs)
