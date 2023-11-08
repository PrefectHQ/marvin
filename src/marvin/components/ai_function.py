import inspect
import json
from functools import partial
from typing import Any, Callable, Generic, Optional, Self, TypeVar, Union

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec

from marvin import settings
from marvin.utilities.asyncutils import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import parse_as
from marvin.utilities.strings import jinja_env

T = TypeVar("T", bound=BaseModel)

P = ParamSpec("P")

ai_fn_system_template = jinja_env.from_string("""
{{ctx.get('instructions') if ctx and ctx.get('instructions')}}

Your job is to generate likely outputs for a Python function with the
following signature and docstring:

{{'def' + ''.join(inspect.getsource(func).split('def')[1:])}}

The user will provide function inputs (if any) and you must respond with
the most likely result, which must be valid, double-quoted JSON.
""")

ai_fn_user_template = jinja_env.from_string("""
The function was called with the following inputs:
{% set sig = inspect.signature(func) %}
{% set binds = sig.bind(*args, **kwargs) %}
{% set defaults = binds.apply_defaults() %}
{% set params = binds.arguments %}
{%for (arg, value) in params.items()%}
- {{ arg }}: {{ value }}
{% endfor %}

What is its output?
""")


class AIFunction(BaseModel, Generic[P, T]):
    fn: Callable[P, Any]
    context: Optional[dict[str, Any]] = None
    llm_settings: dict[str, Any] = Field(default_factory=dict)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        get_logger("marvin.AIFunction").debug_kv(
            f"Calling `ai_fn` {self.fn.__name__!r}",
            f"with args: {args} kwargs: {kwargs}",
        )

        return run_sync(self.call(*args, **kwargs))

    async def call(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        chat_completion_payload = self.to_payload(*args, **kwargs | self.llm_settings)

        openai_client = get_client()

        completion = await openai_client.chat.completions.create(
            **chat_completion_payload
        )

        return parse_as(
            inspect.signature(self.fn).return_annotation,
            json.loads(completion.choices[0].message.content),
        )

    def to_payload(self, *args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
        return {
            "model": settings.openai.llm_model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": ai_fn_system_template.render(
                        func=self.fn,
                        args=args,
                        kwargs=kwargs,
                        ctx=self.context,
                    ),
                },
                {
                    "role": "user",
                    "content": ai_fn_user_template.render(
                        func=self.fn,
                        args=args,
                        kwargs=kwargs,
                        ctx=self.context,
                    ),
                },
            ],
            **settings.openai.chat.completions.model_dump(exclude_none=True),
        }

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        context: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        **llm_settings: Any,
    ) -> Union[Self, Callable[[Callable[P, Any]], Self]]:
        if fn is None:
            return partial(
                cls.as_decorator,
                context=context,
                instructions=instructions,
                **llm_settings,
            )

        if not inspect.iscoroutinefunction(fn):
            return cls(fn=fn, context=context, **llm_settings)

        else:

            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                return await cls(fn=fn, context=context, **llm_settings)(
                    *args, **kwargs
                )

            return wrapper


ai_fn = AIFunction.as_decorator
