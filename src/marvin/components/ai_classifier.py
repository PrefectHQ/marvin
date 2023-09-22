import asyncio
import inspect
from enum import Enum, EnumMeta  # noqa
from functools import partial
from typing import Any, Callable, Literal, Optional, TypeVar

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin.core.ChatCompletion import ChatCompletion
from marvin.core.ChatCompletion.abstract import AbstractChatCompletion
from marvin.prompts import Prompt, prompt_fn
from marvin.utilities.async_utils import run_sync

T = TypeVar("T", bound=BaseModel)

A = TypeVar("A", bound=Any)

P = ParamSpec("P")


def ai_classifier_prompt(
    enum: Enum,
    ctx: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> Callable[P, Prompt[P]]:
    @prompt_fn(
        ctx={"ctx": ctx or {}, "enum": enum, "inspect": inspect},
        response_model=int,  # type: ignore
        response_model_name="Index",
        response_model_description="The index of the most likely class.",
        response_model_field_name="index",
        **kwargs,
    )

    #     You are an expert classifier that always chooses correctly.
    #     {% if enum_class_docstring %}
    #     Your classification task is: {{ enum_class_docstring }}
    #     {% endif %}
    #     {% if instructions %}
    #     Your instructions are: {{ instructions }}
    #     {% endif %}
    #     The user will provide context through text, you will use your expertise
    #     to choose the best option below based on it:
    #     {% for option in options %}
    #         {{ loop.index }}. {{ value_getter(option) }}
    #     {% endfor %}
    #     {% if context_fn %}
    #     You have been provided the following context to perform your task:\n
    #     {%for (arg, value) in context_fn(value).items()%}
    #         - {{ arg }}: {{ value }}\n
    #     {% endfor %}
    #     {% endif %}\
    def prompt_wrapper(text: str) -> None:  # type: ignore # noqa
        """
        System: You are an expert classifier that always chooses correctly
        {{ '(note, however: ' + ctx.get('instructions') + ')' if ctx.get('instructions') }}

        {{ 'Also note that: ' + enum.__doc__ if enum.__doc__ }}

        The user will provide text to classify, you will use your expertise
        to choose the best option below based on it:
        {% for option in enum %}
            {{ loop.index }}. {{option.name}} ({{option.value}})
        {% endfor %}
        {% set context = ctx.get('context_fn')(text).items() if ctx.get('context_fn') %}
        {% if context %}
        You have been provided the following context to perform your task:
        {%for (arg, value) in context%}
            - {{ arg }}: {{ value }}\n
        {% endfor %}
        {% endif %}
        User: the text to classify: {{text}}
        """  # noqa

    return prompt_wrapper  # type: ignore


class AIEnumMetaData(BaseModel):
    model: Any = Field(default_factory=ChatCompletion)
    ctx: Optional[dict[str, Any]] = None
    instructions: Optional[str] = None
    mode: Optional[Literal["function", "logit_bias"]] = "logit_bias"


class AIEnumMeta(EnumMeta):
    """

    A metaclass for the AIEnum class.

    Enables overloading of the __call__ method to permit extra keyword arguments.

    """

    __metadata__ = AIEnumMetaData()

    def __call__(
        cls: Self,
        value: Any,
        names: Optional[Any] = None,
        *args: Any,
        module: Optional[str] = None,
        qualname: Optional[str] = None,
        type: Optional[type] = None,
        start: int = 1,
        boundary: Optional[Any] = None,
        model: Optional[str] = None,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
        **model_kwargs: Any,
    ) -> type[Enum]:
        cls.__metadata__ = AIEnumMetaData(
            model=ChatCompletion(model=model, **model_kwargs),
            ctx=ctx,
            instructions=instructions,
            mode=mode,
        )
        return super().__call__(
            value,
            names,  # type: ignore
            *args,
            module=module,
            qualname=qualname,
            type=type,
            start=start,
        )


class AIEnum(Enum, metaclass=AIEnumMeta):
    """
    AIEnum is a class that extends Python's built-in Enum class.
    It uses the AIEnumMeta metaclass, which allows additional parameters to be passed
    when creating an enum. These parameters are used to customize the behavior
    of the AI classifier.
    """

    @classmethod
    def _missing_(cls: type[Self], value: object) -> Self:
        response: int = cls.call(value)
        return list(cls)[response - 1]

    @classmethod
    def get_prompt(
        cls,
        *,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        **kwargs: Any,
    ) -> Callable[..., Prompt[P]]:
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        return ai_classifier_prompt(cls, ctx=ctx, **kwargs)  # type: ignore

    @classmethod
    def as_prompt(
        cls,
        value: Any,
        *,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> dict[str, Any]:
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        mode = mode or cls.__metadata__.mode
        response = cls.get_prompt(instructions=instructions, ctx=ctx)(value).serialize(
            model=cls.__metadata__.model,
        )
        if mode == "logit_bias":
            import tiktoken

            response.pop("functions", None)
            response.pop("function_call", None)
            response.pop("response_model", None)
            encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
            response["logit_bias"] = {
                encoder.encode(str(j))[0]: 100 for j in range(1, len(cls) + 1)
            }
            response["max_tokens"] = 1
        return response

    @classmethod
    def as_dict(
        cls,
        value: Any,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        mode = mode or cls.__metadata__.mode

        response = cls.get_prompt(ctx=ctx, instructions=instructions)(value).to_dict()
        if mode == "logit_bias":
            import tiktoken

            response.pop("functions", None)
            response.pop("function_call", None)
            response.pop("response_model", None)
            encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
            response["logit_bias"] = {
                encoder.encode(str(j))[0]: 100 for j in range(1, len(cls) + 1)
            }
            response["max_tokens"] = 1

        return response

    @classmethod
    def as_chat_completion(
        cls,
        value: Any,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
    ) -> AbstractChatCompletion[T]:  # type: ignore # noqa
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        mode = mode or cls.__metadata__.mode
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        return cls.__metadata__.model(
            **cls.as_dict(value, ctx=ctx, instructions=instructions, mode=mode)
        )

    @classmethod
    def call(
        cls,
        value: Any,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
    ) -> Any:
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        mode = mode or cls.__metadata__.mode
        chat_completion = cls.as_chat_completion(  # type: ignore # noqa
            value, ctx=ctx, instructions=instructions, mode=mode
        )
        if cls.__metadata__.mode == "logit_bias":
            return int(chat_completion.create().response.choices[0].message.content)  # type: ignore # noqa
        return getattr(chat_completion.create().to_model(), "index")  # type: ignore

    @classmethod
    async def acall(
        cls,
        value: Any,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = None,
    ) -> Any:
        ctx = ctx or cls.__metadata__.ctx or {}
        instructions = instructions or cls.__metadata__.instructions
        ctx["instructions"] = instructions or ctx.get("instructions", None)
        mode = mode or cls.__metadata__.mode
        chat_completion = cls.as_chat_completion(  # type: ignore # noqa
            value, ctx=ctx, instructions=instructions, mode=mode
        )
        if cls.__metadata__.mode == "logit_bias":
            return int((await chat_completion.acreate()).response.choices[0].message.content)  # type: ignore # noqa
        return getattr((await chat_completion.acreate()).to_model(), "index")  # type: ignore # noqa

    @classmethod
    def map(cls, items: list[str], **kwargs: Any) -> list[Any]:
        """
        Map the classifier over a list of items.
        """
        coros = [cls.acall(item, **kwargs) for item in items]

        # gather returns a future, but run_sync requires a coroutine
        async def gather_coros() -> list[Any]:
            return await asyncio.gather(*coros)

        results = run_sync(gather_coros())
        return [list(cls)[result - 1] for result in results]

    @classmethod
    def as_decorator(
        cls: type[Self],
        enum: Optional[Enum] = None,
        ctx: Optional[dict[str, Any]] = None,
        instructions: Optional[str] = None,
        mode: Optional[Literal["function", "logit_bias"]] = "logit_bias",
        model: Optional[str] = None,
        **model_kwargs: Any,
    ) -> Self:
        if not enum:
            return partial(
                cls.as_decorator,
                ctx=ctx,
                instructions=instructions,
                mode=mode,
                model=model,
                **model_kwargs,
            )  # type: ignore
        response = cls(
            enum.__name__,  # type: ignore
            {member.name: member.value for member in enum},  # type: ignore
        )
        setattr(
            response,
            "__metadata__",
            AIEnumMetaData(
                model=ChatCompletion(model=model, **model_kwargs),
                ctx=ctx,
                instructions=instructions,
                mode=mode,
            ),
        )

        response.__doc__ = enum.__doc__  # type: ignore
        return response


ai_classifier = AIEnum.as_decorator
