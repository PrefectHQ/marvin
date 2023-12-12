from functools import partial, wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

from marvin.components.prompt.fn import PromptFunction
from marvin.utilities.jinja import (
    BaseEnvironment,
)

if TYPE_CHECKING:
    from openai.types.images_response import ImagesResponse

T = TypeVar("T")

P = ParamSpec("P")


class AIImage(BaseModel, Generic[P]):
    fn: Optional[Callable[P, Any]] = None
    environment: Optional[BaseEnvironment] = None
    prompt: Optional[str] = Field(default=None)
    render_kwargs: dict[str, Any] = Field(default_factory=dict)

    generate: Optional[Callable[..., "ImagesResponse"]] = Field(default=None)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> "ImagesResponse":
        generate = self.generate
        if self.fn is None:
            raise NotImplementedError
        if generate is None:
            from marvin.settings import settings

            generate = settings.openai.images.generate

        _response = generate(prompt=self.as_prompt(*args, **kwargs))

        return _response

    def as_prompt(
        self,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> str:
        return (
            PromptFunction[BaseModel]
            .as_tool_call(
                fn=self.fn,
                environment=self.environment,
                prompt=self.prompt,
                **self.render_kwargs,
            )(*args, **kwargs)
            .messages[0]
            .content
        )

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        **render_kwargs: Any,
    ) -> Callable[P, Self]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Callable[P, Any],
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        **render_kwargs: Any,
    ) -> Self:
        pass

    @classmethod
    def as_decorator(
        cls: type[Self],
        fn: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[BaseEnvironment] = None,
        prompt: Optional[str] = None,
        **render_kwargs: Any,
    ) -> Union[Self, Callable[[Callable[P, Any]], Self]]:
        if fn is None:
            return partial(
                cls,
                environment=environment,
                **({"prompt": prompt} if prompt else {}),
                **render_kwargs,
            )

        return cls(
            fn=fn,
            environment=environment,
            **({"prompt": prompt} if prompt else {}),
            **render_kwargs,
        )


def ai_image(
    fn: Optional[Callable[P, Any]] = None,
    *,
    environment: Optional[BaseEnvironment] = None,
    prompt: Optional[str] = None,
    **render_kwargs: Any,
) -> Union[
    Callable[[Callable[P, Any]], Callable[P, "ImagesResponse"]],
    Callable[P, "ImagesResponse"],
]:
    def wrapper(
        func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
    ) -> "ImagesResponse":
        return AIImage[P].as_decorator(
            func,
            environment=environment,
            prompt=prompt,
            **render_kwargs,
        )(*args, **kwargs)

    if fn is not None:
        return wraps(fn)(partial(wrapper, fn))

    def decorator(fn: Callable[P, Any]) -> Callable[P, "ImagesResponse"]:
        return wraps(fn)(partial(wrapper, fn))

    return decorator


def create_image(
    prompt: str,
    environment: Optional[BaseEnvironment] = None,
    generate: Optional[Callable[..., "ImagesResponse"]] = None,
    **model_kwargs: Any,
) -> "ImagesResponse":
    if generate is None:
        from marvin.settings import settings

        generate = settings.openai.images.generate
    return generate(prompt=prompt, **model_kwargs)
