import inspect
from functools import partial
from typing import Callable, Optional, TypeVar, Union, overload

from typing_extensions import Unpack

from marvin.components.ai_function import (
    AIFunctionKwargs,
    AIFunctionKwargsDefaults,
    ai_fn,
)

T = TypeVar("T")

prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse into a structured"
    " form. To validate your response, you must call the"
    " `{{_response_model.function.name}}` function. Use the provided text to extract or"
    " infer any parameters needed by `{{_response_model.function.name}}`, including any"
    " missing data."
    " user: The text to parse: {{text}}"
)


class AIModelKwargsDefaults(AIFunctionKwargsDefaults):
    prompt: Optional[str] = prompt


@overload
def ai_model(
    **kwargs: Unpack[AIFunctionKwargs],
) -> Callable[[Callable[[str], T]], Callable[[str], T]]:
    pass


@overload
def ai_model(
    _type: type[T],
    **kwargs: Unpack[AIFunctionKwargs],
) -> Callable[[str], T]:
    pass


def ai_model(
    _type: Optional[type[T]] = None,
    **kwargs: Unpack[AIFunctionKwargs],
) -> Union[
    Callable[
        [Callable[[str], T]],
        Callable[[str], T],
    ],
    partial[
        Callable[
            [Callable[[str], T]],
            Callable[[str], T],
        ]
    ],
    Callable[[str], T],
]:
    if _type is not None:

        def extract(text: str) -> T:
            return _type

        extract.__annotations__["return"] = _type
        return ai_fn(
            fn=extract,
            **AIModelKwargsDefaults(**kwargs).model_dump(exclude_none=True),
        )

    return partial(
        ai_model, **AIModelKwargsDefaults(**kwargs).model_dump(exclude_none=True)
    )
