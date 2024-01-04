from functools import partial
from typing import Callable, Optional, TypeVar, Union, overload

from typing_extensions import Unpack

from marvin.components.function import (
    FunctionKwargs,
    FunctionKwargsDefaults,
    fn,
)
from marvin.prompts.models import MODEL_PROMPT

T = TypeVar("T")


class ModelKwargsDefaults(FunctionKwargsDefaults):
    prompt: Optional[str] = MODEL_PROMPT


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
    instructions: str = None,
    **kwargs: Unpack[FunctionKwargs],
) -> Union[
    Callable[[Callable[[str], T]], Callable[[str], T]],
    partial[Callable[[Callable[[str], T]], Callable[[str], T]]],
    Callable[[str], T],
]:
    if _type is not None:

        def extract(text: str, instructions: str = None) -> _type:
            pass

        return partial(
            fn(
                fn=extract,
                **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True),
            ),
            instructions=instructions,
        )

    return partial(model, **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True))
