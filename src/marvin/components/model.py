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
    **kwargs: Unpack[FunctionKwargs],
) -> Union[
    Callable[[Callable[[str], T]], Callable[[str], T]],
    partial[Callable[[Callable[[str], T]], Callable[[str], T]]],
    Callable[[str], T],
]:
    """Decorator for creating a Pydantic model type that can be used to cast or extract data.

    Args:
        _type: The type of the model to create.
        **kwargs: Keyword arguments to pass to the model.

    Returns:
        A Pydantic model type that can be used to cast or extract data.

    Example:
        ```python
        import marvin
        from pydantic import BaseModel

        class MenuItem(BaseModel):
            name: str
            price: float

        class Order(BaseModel):
            items: list[MenuItem]
            total: float

        marvin.model(Order)("can i get 2 $5 footlongs? and 2 cookies from the dollar menu?")
        '''
        Order(
            items=[
                MenuItem(name='footlong', price=5.0),
                MenuItem(name='footlong', price=5.0),
                MenuItem(name='cookie', price=1.0),
                MenuItem(name='cookie', price=1.0)
            ],
            total=12.0
        )
        '''
        ```
    """
    if _type is not None:

        def extract(text: str, instructions: str = None) -> _type:
            pass

        return fn(
            fn=extract,
            **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True),
        )

    return partial(model, **ModelKwargsDefaults(**kwargs).model_dump(exclude_none=True))
