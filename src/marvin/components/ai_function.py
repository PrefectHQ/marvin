import asyncio
import inspect
import json
from functools import partial
from typing import Any, Callable, Generic, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin import settings
from marvin.utilities.asyncutils import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.openai import get_client
from marvin.utilities.pydantic import cast_to_model, parse_as
from marvin.utilities.strings import jinja_env

T = TypeVar("T", bound=BaseModel)

P = ParamSpec("P")

ai_fn_system_template = jinja_env.from_string("""
{{ctx.get('instructions') if ctx and ctx.get('instructions')}}

Your job is to generate likely outputs for the function `{{ func.__name__ }}`.

Here is the function's signature:
{{ 'def ' + func.__name__ + str(inspect.signature(func)) }}

And here is the function's docstring:
{{ func.__doc__ }}

When given inputs by the user, you must provide the most sensible
output for `{{ func.__name__ }}` to `FormatResponse`.

Remember, you must call `FormatResponse` with a valid object or array
that can be casted into the following model: {{ annotation }}.
""")

ai_fn_user_template = jinja_env.from_string("""
{% set sig = inspect.signature(func) %}
{% set binds = sig.bind(*args, **kwargs) %}
{% set defaults = binds.apply_defaults() %}
{% set params = binds.arguments %}
{% if params %}
These are my inputs:
{% for (arg, value) in params.items() %}
- {{ arg }}: {{ value }}
{% endfor %}
{% else %}
The function was called without inputs.
{% endif %}

Please -- I really need your help! What is the output of this function?
""")


class AIFunction(BaseModel, Generic[P, T]):
    fn: Callable[P, Any]
    context: Optional[dict[str, Any]] = None
    llm_settings: dict[str, Any] = Field(default_factory=dict)

    @property
    def return_annotation(self) -> Any:
        return inspect.signature(self.fn).return_annotation

    @property
    def return_model(self) -> Type[BaseModel]:
        return cast_to_model(
            self.return_annotation,
            name=f"{self.fn.__name__}_output",
            description=(
                f"Model representing the output of the `{self.fn.__name__}` function."
            ),
            field_name="output",
        )

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        return run_sync(self.call(*args, **kwargs))

    async def call(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        get_logger("marvin.AIFunction").debug_kv(
            f"Calling `ai_fn` {self.fn.__name__!r}",
            f"with args: {args} kwargs: {kwargs}",
        )
        chat_completion_payload = self.to_payload(*args, **kwargs)

        completion = await get_client().chat.completions.create(
            **chat_completion_payload
        )

        json_output = json.loads(
            completion.choices[0].message.tool_calls[0].function.arguments
        )

        if self.return_annotation in {
            inspect.Signature.empty,
            list,
            dict,
            dict[str, str],
            dict[str, Any],
            Any,
        }:
            return json_output

        get_logger("marvin.AIFunction").debug_kv(
            f"Received output from `ai_fn` {self.fn.__name__!r}",
            json.dumps(json_output, indent=2),
        )

        get_logger("marvin.AIFunction").debug_kv(
            f"Casting output from {self.fn.__name__!r}",
            f"to {self.return_annotation!r}",
        )

        print(json_output, self.return_model, self.return_annotation)

        return parse_as(self.return_model, json_output)

    def to_payload(self, *args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
        return {
            "model": settings.openai.chat.completions.model,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "FormatResponse",
                        "description": "Schema that likely outputs must conform to.",
                        "parameters": self.return_model.model_json_schema(),
                    },
                }
            ],
            "messages": [
                {
                    "role": "system",
                    "content": ai_fn_system_template.render(
                        func=self.fn,
                        args=args,
                        kwargs=kwargs,
                        ctx=self.context,
                        annotation=self.return_annotation,
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
            **{"temperature": 0.0} | self.llm_settings,
        }

    def map(self, *map_args: list[Any], **map_kwargs: list[Any]):
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        This method should be called synchronously.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2, x='b')].
        """
        return run_sync(self.amap(*map_args, **map_kwargs))

    async def amap(self, *map_args: list[Any], **map_kwargs: list[Any]) -> list[Any]:
        tasks: list[Any] = []
        if map_args:
            max_length = max(len(arg) for arg in map_args)
        else:
            max_length = max(len(v) for v in map_kwargs.values())

        for i in range(max_length):
            call_args = [arg[i] if i < len(arg) else None for arg in map_args]
            call_kwargs = (
                {k: v[i] if i < len(v) else None for k, v in map_kwargs.items()}
                if map_kwargs
                else {}
            )
            tasks.append(self.call(*call_args, **call_kwargs))

        return await asyncio.gather(*tasks)

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
            return AsyncAIFunction[P, T](fn=fn, context=context, **llm_settings)


class AsyncAIFunction(AIFunction[P, T]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        return await super().call(*args, **kwargs)


ai_fn = AIFunction.as_decorator
