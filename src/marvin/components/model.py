import inspect
from functools import partial
from typing import Callable, Optional, TypeVar, Union, overload

from typing_extensions import Unpack

from marvin.components.function import (
    FunctionKwargs,
    FunctionKwargsDefaults,
    fn,
)

T = TypeVar("T")

prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse into a structured"
    " form. To validate your response, you must call the"
    " `{{_response_model.function.name}}` function. Use the provided text to extract or"
    " infer any parameters needed by `{{_response_model.function.name}}`, including any"
    " missing data."
    " \n\nHUMAN: The text to parse: {{text}}"
)


class ModelKwargsDefaults(FunctionKwargsDefaults):
    prompt: Optional[str] = prompt


@overload
def model(
    **kwargs: Unpack[FunctionKwargs],
) -> Callable[[Callable[[str], T]], Callable[[str], T]]:
    pass


@overload
def model(
    _type: type[T],
    **kwargs: Unpack[FunctionKwargs],
) -> Callable[[str], T]:
    pass


def model(
    _type: Optional[type[T]] = None,
    **kwargs: Unpack[FunctionKwargs],
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
        return fn(
            fn=extract,
            **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True),
        )

    return partial(model, **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True))
