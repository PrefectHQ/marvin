import asyncio
import inspect
from functools import partial
from typing import Any, Callable, Optional, Self, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

from marvin.core.ChatCompletion import ChatCompletion
from marvin.core.ChatCompletion.abstract import AbstractChatCompletion
from marvin.prompts import Prompt, prompt_fn
from marvin.utilities.async_utils import run_sync

T = TypeVar("T", bound=BaseModel)

A = TypeVar("A", bound=Any)

P = ParamSpec("P")


def ai_model_prompt(
    cls: type[BaseModel],
    ctx: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> Callable[[str], Prompt[P]]:
    @prompt_fn(
        ctx={"ctx": ctx or {}, "inspect": inspect},
        response_model=cls,
    )
    def prompt_wrapper(text: str) -> None:  # type: ignore # noqa
        """
        System: The user will provide context as text that you need to parse into a
        structured form. To validate your response, you must call the
        `{{response_model.__name__}}` function.
        {% if ctx.get('instructions') %}
            - Your instructions: {{ctx.get('instructions')}}
        {% endif %}
        {% if response_model.__doc__ %}
            - {{response_model.__doc__}}}
        {% endif %}
        Use the provided text and context to extract or infer
        any parameters needed by `{{response_model.__name__}}`, including any missing
        data.

        You have been provided the following context to perform your task:
            - The current time is {{now()}}.
        {% set context = ctx.get('context_fn')(text).items() if ctx.get('context_fn') %}
        {% if context %}
        {%for (arg, value) in context%}
            - {{ arg }}: {{ value }}\n
        {% endfor %}
        {% endif %}

        User: The text to parse: {{text}}
        """  # noqa

    return prompt_wrapper  # type: ignore


class AIModel(BaseModel):
    def __init__(
        self,
        text: Optional[str] = None,
        /,
        instructions_: Optional[str] = None,
        **kwargs: Any,
    ):
        if text:
            kwargs.update(self.__class__.call(text, instructions=instructions_))

        super().__init__(**kwargs)

    @classmethod
    def get_prompt(
        cls,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
    ) -> Callable[[str], Prompt[P]]:
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})
        instructions = (  # type: ignore
            "\n".join(
                list(
                    filter(
                        bool,
                        [
                            instructions,
                            getattr(cls, "__metadata__", {}).get("instructions"),
                        ],
                    )
                )  # type: ignore
            )
            or None
        )
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")

        return ai_model_prompt(
            cls,
            ctx=((ctx or {}) | {"instructions": instructions}),
            response_model_name=response_model_name,
            response_model_description=response_model_description,
            response_model_field_name=response_model_field_name,
        )

    @classmethod
    def as_prompt(
        cls,
        text: str,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> dict[str, Any]:
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})
        instructions = instructions or getattr(cls, "__metadata__", {}).get(
            "instructions"
        )  # noqa
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")
        return cls.get_prompt(
            ctx=ctx,
            instructions=instructions,
            response_model_name=response_model_name,
            response_model_description=response_model_description,
            response_model_field_name=response_model_field_name,
        )(text).serialize(model=ChatCompletion(model=model, **model_kwargs))

    @classmethod
    def as_dict(
        cls,
        text: str,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> dict[str, Any]:
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})
        instructions = instructions or getattr(cls, "__metadata__", {}).get(
            "instructions"
        )  # noqa
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")
        return cls.get_prompt(
            ctx=ctx,
            instructions=instructions,
            response_model_name=response_model_name,
            response_model_description=response_model_description,
            response_model_field_name=response_model_field_name,
        )(text).to_dict()

    @classmethod
    def as_chat_completion(
        cls,
        text: str,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> AbstractChatCompletion[T]:  # type: ignore
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})
        instructions = instructions or getattr(cls, "__metadata__", {}).get(
            "instructions"
        )  # noqa
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")
        return ChatCompletion(model=model, **model_kwargs)(
            **cls.as_dict(
                text,
                ctx=ctx,
                instructions=instructions,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
            )
        )  # type: ignore

    @classmethod
    def call(
        cls: type[Self],
        text: str,
        *,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Self:
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})

        instructions = instructions or getattr(cls, "__metadata__", {}).get(
            "instructions"
        )  # noqa
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")
        _model: Self = (  # type: ignore
            cls.as_chat_completion(
                text,
                ctx=ctx,
                instructions=instructions,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
                model=model,
                **model_kwargs,
            )
            .create()
            .to_model()
        )
        return _model  # type: ignore

    @classmethod
    async def acall(
        cls: type[Self],
        text: str,
        *,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Self:
        ctx = ctx or getattr(cls, "__metadata__", {}).get("ctx", {})
        instructions = instructions or getattr(cls, "__metadata__", {}).get(
            "instructions"
        )  # noqa
        response_model_name = response_model_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_name")
        response_model_description = response_model_description or getattr(
            cls, "__metadata__", {}
        ).get("response_model_description")
        response_model_field_name = response_model_field_name or getattr(
            cls, "__metadata__", {}
        ).get("response_model_field_name")
        _model: Self = (  # type: ignore
            await cls.as_chat_completion(
                text,
                ctx=ctx,
                instructions=instructions,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
                model=model,
                **model_kwargs,
            ).acreate()  # type: ignore
        ).to_model()
        return _model  # type: ignore

    @classmethod
    def map(cls, *map_args: list[str], **map_kwargs: list[Any]):
        """
        Map the AI function over a sequence of arguments. Runs concurrently.

        Arguments should be provided as if calling the function normally, but
        each argument must be a list. The function is called once for each item
        in the list, and the results are returned in a list.

        This method should be called synchronously.

        For example, fn.map([1, 2]) is equivalent to [fn(1), fn(2)].

        fn.map([1, 2], x=['a', 'b']) is equivalent to [fn(1, x='a'), fn(2, x='b')].
        """
        return run_sync(cls.amap(*map_args, **map_kwargs))

    @classmethod
    async def amap(cls, *map_args: list[str], **map_kwargs: list[Any]) -> list[Any]:
        tasks: list[Any] = []
        if map_args:
            max_length = max(len(arg) for arg in map_args)
        else:
            max_length = max(len(v) for v in map_kwargs.values())

        for i in range(max_length):
            call_args: list[str] = [
                arg[i] if i < len(arg) else None for arg in map_args
            ]  # type: ignore
            call_kwargs = (
                {k: v[i] if i < len(v) else None for k, v in map_kwargs.items()}
                if map_kwargs
                else {}
            )
            tasks.append(cls.acall(*call_args, **call_kwargs))

        return await asyncio.gather(*tasks)

    @classmethod
    def as_decorator(
        cls: type[Self],
        base_model: Optional[type[BaseModel]] = None,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> type[BaseModel]:
        if not base_model:
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

        response = type(base_model.__name__, (cls, base_model), {})
        response.__doc__ = base_model.__doc__
        setattr(
            response,
            "__metadata__",
            {
                "ctx": ctx or {},
                "instructions": instructions,
                "response_model_name": response_model_name,
                "response_model_description": response_model_description,
                "response_model_field_name": response_model_field_name,
                "model": model,
                "model_kwargs": model_kwargs,
            },
        )
        return response  # type: ignore


ai_model = AIModel.as_decorator
