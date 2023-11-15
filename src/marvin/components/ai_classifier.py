import inspect
from functools import partial, wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin.components.prompt_function import PromptFn
from marvin.settings import settings
from marvin.utilities.jinja import (
    BaseEnvironment,
)

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

T = TypeVar("T")

P = ParamSpec("P")


class AIClassifier(BaseModel, Generic[P, T]):
    fn: Optional[Callable[P, T]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=inspect.cleandoc("""
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
    """))
    enumerate: bool = True
    encoder: Callable[[str], list[int]] = Field(default=None)
    max_tokens: Optional[int] = 1
    render_kwargs: dict[str, Any] = Field(default_factory=dict)

    create: Optional[Callable[..., "ChatCompletion"]] = Field(default=None)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        create = self.create
        if self.fn is None:
            raise NotImplementedError
        if create is None:
            from marvin.settings import settings

            create = settings.openai.chat.completions.create
        return self.parse(create(**self.as_prompt(*args, **kwargs).serialize()))

    def parse(self, response: "ChatCompletion") -> T:
        pass

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> PromptFn[BaseModel]:
        return PromptFn[BaseModel].as_grammar(
            fn=self.fn,
            environment=self.environment,
            prompt=self.prompt,
            enumerate=self.enumerate,
            encoder=self.encoder,
            max_tokens=self.max_tokens,
            **self.render_kwargs,
        )(*args, **kwargs)

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        enumerate: bool = True,
        encoder: Callable[[str], list[int]] = settings.openai.chat.completions.encoder,
        max_tokens: Optional[int] = 1,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, T],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        enumerate: bool = True,
        encoder: Callable[[str], list[int]] = settings.openai.chat.completions.encoder,
        max_tokens: Optional[int] = 1,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, T]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        enumerate: bool = True,
        encoder: Callable[[str], list[int]] = settings.openai.chat.completions.encoder,
        max_tokens: Optional[int] = 1,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
        **render_kwargs: Any,
    ) -> Union[Self, Callable[[Callable[P, T]], Self]]:
        if fn is None:
            return partial(
                cls,
                environment=environment,
                prompt=prompt,
                enumerate=enumerate,
                encoder=encoder,
                max_tokens=max_tokens,
                acreate=acreate,
                **({"prompt": prompt} if prompt else {}),
                **render_kwargs,
            )

        return cls(
            fn=fn,
            environment=environment,
            enumerate=enumerate,
            encoder=encoder,
            max_tokens=max_tokens,
            **({"prompt": prompt} if prompt else {}),
            **render_kwargs,
        )


@overload
def ai_classifier(
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    pass


@overload
def ai_classifier(
    fn: Callable[P, T],
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Callable[P, T]:
    pass


def ai_classifier(
    fn: Optional[Callable[P, T]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    model_name: str = "FormatResponse",
    model_description: str = "Formats the response.",
    field_name: str = "data",
    field_description: str = "The data to format.",
    **render_kwargs: Any,
) -> Union[Callable[[Callable[P, T]], Callable[P, T]], Callable[P, T],]:
    def wrapper(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        return AIClassifier[P, T].as_decorator(
            func,
            environment=environment,
            prompt=prompt,
            model_name=model_name,
            model_description=model_description,
            field_name=field_name,
            field_description=field_description,
            **render_kwargs,
        )(*args, **kwargs)

    if fn is not None:
        return wraps(fn)(partial(wrapper, fn))

    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        return wraps(fn)(partial(wrapper, fn))

    return decorator
