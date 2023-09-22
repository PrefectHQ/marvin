import asyncio
import inspect
from functools import partial
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin.core.ChatCompletion import ChatCompletion
from marvin.core.ChatCompletion.abstract import AbstractChatCompletion
from marvin.prompts import Prompt, prompt_fn
from marvin.utilities.async_utils import run_sync

T = TypeVar("T", bound=BaseModel)

A = TypeVar("A", bound=Any)

P = ParamSpec("P")


def ai_fn_prompt(
    func: Callable[P, Any],
    ctx: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> Callable[P, Prompt[P]]:
    return_annotation: Any = inspect.signature(func).return_annotation

    @prompt_fn(
        ctx={"ctx": ctx or {}, "func": func, "inspect": inspect},
        response_model=return_annotation,
        **kwargs,
    )
    def prompt_wrapper(*args: P.args, **kwargs: P.kwargs) -> None:  # type: ignore # noqa
        """
        System: {{ctx.get('instructions') if ctx.get('instructions')}}

        Your job is to generate likely outputs for a Python function with the
        following signature and docstring:

        {{'def' + ''.join(inspect.getsource(func).split('def')[1:])}}

        The user will provide function inputs (if any) and you must respond with
        the most likely result.

        User: The function was called with the following inputs:
        {% set sig = inspect.signature(func) %}
        {% set binds = sig.bind(*args, **kwargs) %}
        {% set defaults = binds.apply_defaults() %}
        {% set params = binds.arguments %}
        {%for (arg, value) in params.items()%}
        - {{ arg }}: {{ value }}
        {% endfor %}

        What is its output?
        """

    return prompt_wrapper  # type: ignore


class AIFunction(BaseModel, Generic[P, T]):
    fn: Callable[P, Any]
    ctx: Optional[dict[str, Any]] = None
    model: Any = Field(default_factory=ChatCompletion)
    response_model_name: Optional[str] = Field(default=None, exclude=True)
    response_model_description: Optional[str] = Field(default=None, exclude=True)
    response_model_field_name: Optional[str] = Field(default=None, exclude=True)

    def __call__(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Any:
        return self.call(*args, **kwargs)

    def get_prompt(
        self,
    ) -> Callable[P, Prompt[P]]:
        return ai_fn_prompt(
            self.fn,
            ctx=self.ctx,
            response_model_name=self.response_model_name,
            response_model_description=self.response_model_description,
            response_model_field_name=self.response_model_field_name,
        )

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> dict[str, Any]:
        return self.get_prompt()(*args, **kwargs).serialize(
            model=self.model,
        )

    def as_dict(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> dict[str, Any]:
        return self.get_prompt()(*args, **kwargs).to_dict()

    def as_chat_completion(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> AbstractChatCompletion[T]:
        return self.model(**self.as_dict(*args, **kwargs))

    def call(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Any:
        return getattr(
            self.as_chat_completion(*args, **kwargs).create().to_model(),
            self.response_model_field_name or "output",
        )

    async def acall(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Any:
        return getattr(
            (await self.as_chat_completion(*args, **kwargs).acreate()).to_model(),
            self.response_model_field_name or "output",
        )

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
            tasks.append(self.acall(*call_args, **call_kwargs))

        return await asyncio.gather(*tasks)

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, T]] = None,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Callable[P, T] | Callable[P, Awaitable[T]]:
        if not fn:
            return partial(
                cls.as_decorator,
                ctx=ctx,
                instructions=instructions,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
                model=model,
                **model_kwargs,
            )  # type: ignore

        if not inspect.iscoroutinefunction(fn):
            return cls(
                fn=fn,
                ctx={"instructions": instructions, **(ctx or {})},
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
                model=ChatCompletion(model=model, **model_kwargs),
            )
        else:
            return AsyncAIFunction[P, T](
                fn=fn,
                ctx={"instructions": instructions, **(ctx or {})},
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
                model=ChatCompletion(model=model, **model_kwargs),
            )


class AsyncAIFunction(AIFunction[P, T]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        return await super().acall(*args, **kwargs)


ai_fn = AIFunction.as_decorator
