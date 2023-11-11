import inspect
import json
from functools import partial
from typing import Any, Callable, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from yaml import serialize
from functools import partial, wraps

from marvin import settings
from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import Environment as JinjaEnvironment
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as
from marvin.components.prompt_function import PromptFn
import json

T = TypeVar("T", bound=BaseModel)

P = ParamSpec("P")


prompt = """
Your job is to generate likely outputs for a Python function with the
following signature and docstring:

{{_source_code}}

The user will provide function inputs (if any) and you must respond with
the most likely result, which must be valid, double-quoted JSON.

user: The function was called with the following inputs:
{%for (arg, value) in _arguments.items()%}
- {{ arg }}: {{ value }}
{% endfor %}

What is its output?
"""


class AIFunction(BaseModel, Generic[P, T]):
    fn: Callable[P, T]
    prompt_fn: PromptFn

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        get_logger("marvin.AIFunction").debug_kv(  # type: ignore
            f"Calling `ai_fn` {self.fn.__name__!r}",
            f"with args: {args} kwargs: {kwargs}",
        )

        return

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        *,
        prompt: str = prompt,
        response_model_name: str = "FormatResponse",
        response_model_description: str = "Formats the response.",
        response_model_field_name: str = "data",
    ) -> Union[
        Callable[[Callable[P, None]], Callable[P, None]],
        Callable[[Callable[P, None]], Callable[P, Self]],
        Callable[P, Self],
    ]:
        def wrapper(fn: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> T:
            return json.loads(
                PromptFn.as_decorator(
                    fn=fn,
                    prompt=prompt,
                    serialize=False,
                    response_model_name=response_model_name,
                    response_model_description=response_model_description,
                    response_model_field_name=response_model_field_name,
                )(*args, **kwargs)
                .call()  # type: ignore
                .choices[0]
                .message.tool_calls[0]
                .function.arguments
            ).get(response_model_field_name)

        def decorator(fn: Callable[P, None]) -> Callable[P, Self]:
            return wraps(fn)(partial(wrapper, fn))

        return decorator

        test = PromptFn.as_decorator(
            fn=fn,
            prompt=prompt,
            serialize=False,
            response_model_name=response_model_name,
            response_model_description=response_model_description,
            response_model_field_name=response_model_field_name,
        )

        return test


ai_fn = AIFunction.as_decorator
