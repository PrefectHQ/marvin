import inspect
from typing import Any, Callable, Optional, TypeVar, Union, overload

from marvin.components.ai_function import ai_fn
from marvin.utilities.jinja import BaseEnvironment

T = TypeVar("T")

prompt = inspect.cleandoc(
    "The user will provide context as text that you need to parse into a structured"
    " form. To validate your response, you must call the"
    " `{{_response_model.function.name}}` function. Use the provided text to extract or"
    " infer any parameters needed by `{{_response_model.function.name}}`, including any"
    " missing data."
    " user: The text to parse: {{text}}"
)


@overload
def ai_model(
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = prompt,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Callable[[T], Callable[[str], T]]:
    pass


@overload
def ai_model(
    _type: Optional[type[T]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = prompt,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Callable[[str], T]:
    pass


def ai_model(
    _type: Optional[type[T]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = prompt,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Union[Callable[[T], Callable[[str], T]], Callable[[str], T],]:
    if _type is not None:

        def extract(text: str) -> T:
            return _type

        extract.__annotations__["return"] = _type
        return ai_fn(
            extract,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **render_kwargs,
        )

    def decorator(__type__: T) -> Callable[[str], T]:
        def extract(text: str) -> T:
            return __type__

        extract.__annotations__["return"] = _type
        return ai_fn(
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **render_kwargs,
        )

    return decorator
