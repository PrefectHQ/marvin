import asyncio
import functools
from typing import (
    Any,
    Callable,
    ClassVar,
    Optional,
    Type,
    TypeVar,
)

from marvin.core.ChatCompletion import BaseChatCompletion, ChatCompletion
from marvin.core.messages import Message, Prompt
from marvin.core.requests import Request
from marvin.core.serializers import AbstractRequestSerializer
from marvin.pydantic import BaseModel
from marvin.utilities.async_utils import run_sync

T = TypeVar("T", bound="AIModel")


def base_extract(response_model: type[BaseModel], text: str, **kwargs: Any) -> Prompt:
    """
    Creates most basic prompt that can be used to extract a response model from
    unstructured text.

    Args:
        response_model (type[BaseModel]): The response model to extract.
        text (str): The unstructured text to extract from.
        **kwargs (Any): Any additional keyword arguments to pass to the prompt.

    Returns:
        Prompt: A prompt object that can be used to generate a chat completion.
    """

    return Prompt(
        response_model=response_model,
        messages=[
            Message(
                role="system",
                content="""You correctly extract {{response_model.__name__}} objects from unstructured text.""",  # noqa
            ),
            Message(role="user", content="{{text}}"),
        ],
    ).render(text=text, **kwargs)


def extract(
    text: str,
    response_model: type[BaseModel],
    static_context: Optional[str] = None,
    context_function: Optional[Callable[..., str]] = None,
) -> Prompt:
    """
    Creates a prompt that can be used to extract a response model from
    unstructured text. This prompt is more flexible than `base_extract` in that
    it allows for the specification of context functions that can be used to
    extract, infer, or deduce missing data.

    Args:
        - text (str): The unstructured text to extract from.
        - response_model (type[BaseModel]): The response model to extract.
        - static_context (Optional[str], optional): Instructions from the user on how to complete the task. Defaults to None.
        - context_function (Optional[Callable[..., str]], optional): A function that takes in text and returns a string of context. Defaults to None.

    Returns:
        Prompt: A prompt object that can be used to generate a chat completion.
    """  # noqa
    return Prompt(
        response_model=response_model,
        messages=[
            Message(
                role="system",
                content=(
                    """You correctly extract, deduce, infer, and compute {{response_model.__name__}} objects from unstructured text. """  # noqa
                    """    - You deduce and both correct values and data types even if not directly provided."""  # noqa
                    """    - To validate your response, you must call the `{{response_model.__name__}}` function."""  # noqa
                    """    - You must format your response according to the `{{response_model.__name__}}` signature."""  # noqa
                    """{% if static_context %}{{'\n' + static_context}}{% endif %}"""  # noqa
                    """{% if context_function %}{% set context = context_function(text) %}{{'\n' + context if context}}{% endif %}"""  # noqa
                ),
            ),
            Message(role="user", content="{{text}}"),
        ],
    ).render(
        text=text,
        static_context=static_context,
        context_function=context_function,
    )


class BaseAIModel(BaseModel):
    _instructions: ClassVar[Optional[str]] = None
    _compute_prompt: ClassVar[Optional[Callable[..., Prompt]]] = None

    @classmethod
    def extract(
        cls,
        text: str,
        instructions: Optional[str] = None,
        context_function: Optional[Callable[[str], str]] = None,
        **kwargs: Any,
    ) -> Prompt:
        """
        Creates a prompt that can be used to extract a response model from
        unstructured text.

        Args:
            - text (str): The unstructured text to extract from.
            - instructions (Optional[str], optional): Instructions from the user on how to complete the task. Defaults to None.
            - context_function (Optional[Callable[..., str]], optional): A function that takes in text and returns a string of context. Defaults to None.

        Keyword Args:
            - **kwargs (Any): Any additional keyword arguments to render into the prompt.

        Returns:
            Request: A prompt object that can be used to generate a chat completion.

        """  # noqa

        instructions = "\n".join(
            list(filter(bool, [(cls._instructions or ""), (instructions or "")]))
        )
        return (cls._extract_prompt or base_extract)(
            response_model=cls,
            text=text,
            static_context=instructions,
            context_function=context_function,
        )


class AIModel(BaseAIModel):
    _extract_prompt: ClassVar[Optional[Callable[..., Prompt]]] = None
    _chat_completion: ClassVar[Optional[BaseChatCompletion]] = None

    def __init__(
        self,
        text: Optional[str] = None,
        *,
        _instructions: Optional[str] = None,
        **kwargs: Any,
    ) -> None:  # noqa
        # Takes a single positional argument `text` which, if present, is used to
        # extract parameters needed by the Pydantic model. The call method returns
        # a dictionary of keyword arguments that are passed to the Pydantic model.

        # Exposes an optional `_instructions` keyword argument that is passed to the
        # `Prompt` object. This is useful for providing instructions to the LLM.

        # NOTE: Pydantic models do not accept positional arguments, so we are free to
        # overload this method to accept a text argument without fear of breaking
        # the Pydantic model.

        if text:
            kwargs.update(
                self.__class__.call(
                    self.extract(
                        text,
                        static_context=getattr(self.__class__, "_instructions", None),
                        runtime_context=_instructions,
                        context_function=getattr(self, "_context_function", None),
                    )
                )
            )
        super().__init__(**kwargs)

    @classmethod
    def as_prompt(
        cls,
        text: str,
        instructions: Optional[str] = None,
        context_function: Optional[Callable[[str], str]] = None,
        prompt: Optional[Prompt] = None,
        serializer: Optional[Type[AbstractRequestSerializer]] = None,
        **kwargs: Any,
    ) -> Prompt:
        return cls.extract(
            text,
            instructions=instructions,
            context_function=context_function,
            serializer=serializer,
            prompt=prompt,
            **kwargs,
        ).serialize(
            serializer=serializer,
        )

    @classmethod
    def extract(
        cls,
        text: str,
        instructions: Optional[str] = None,
        context_function: Optional[Callable[[str], str]] = None,
        prompt: Optional[Prompt] = None,
        **kwargs: Any,
    ) -> Request:
        """
        Creates a prompt that can be used to extract a response model from
        unstructured text. This prompt is more flexible than `base_extract` in that
        it allows for the specification of context functions that can be used to
        extract, infer, or deduce missing data.

        Args:
            - text (str): The unstructured text to extract from.
            - response_model (type[BaseModel]): The response model to extract.
            - instructions (Optional[str], optional): Instructions from the user on how to complete the task. Defaults to None.
            - context_function (Optional[Callable[..., str]], optional): A function that takes in text and returns a string of context. Defaults to None.

        Keyword Args:
            - **kwargs (Any): Any additional keyword arguments to render into the prompt.

        Returns:
            Request: A prompt object that can be used to generate a chat completion.

        """  # noqa

        instructions = "\n".join(
            list(filter(bool, [(cls._instructions or ""), (instructions or "")]))
        )

        return Request.from_prompt(
            (prompt or cls._extract_prompt or extract)(
                response_model=cls,
                text=text,
                static_context=instructions,
                context_function=context_function,
            )
        )

    @classmethod
    def to_chat_completion(
        cls: type[T],
        text: str,
        instructions: Optional[str] = None,
        context_function: Optional[Callable[[str], str]] = None,
        **kwargs: list[Any],
    ) -> BaseChatCompletion:
        return (cls._chat_completion or ChatCompletion)(
            **cls.extract(
                text,
                instructions=instructions,
                context_function=context_function,
                **kwargs,
            ).serialize()
        )

    @classmethod
    def call(
        cls: type[T],
        Prompt: Prompt,
    ) -> dict[str, Any]:
        chat_completion: BaseChatCompletion = cls._chat_completion or ChatCompletion()
        response = chat_completion.create(**Prompt.dict())
        if response_model := response.to_model():
            return response_model.dict()
        return {}

    @classmethod
    async def acall(
        cls: type[T],
        Prompt: Prompt,
    ) -> dict[str, Any]:
        chat_completion: BaseChatCompletion = cls._chat_completion or ChatCompletion()
        response = await chat_completion.acreate(**Prompt.dict())
        if response_model := response.to_model():
            return response_model.dict()
        return {}

    @classmethod
    async def amap(
        cls: type[T], *map_args: list[str], **map_kwargs: list[Any]
    ) -> list[T]:
        """
        Map the AI Model over a sequence of arguments. Runs concurrently.

        Example:
            >>> await Location.amap(["windy city", "big apple"])
            # [Location(city="Chicago"), Location(city="New York City")]
        """

        if not map_kwargs:
            tasks = [cls.acall(cls.extract(*a)) for a in zip(*map_args)]
        else:
            tasks = [
                cls.acall(
                    cls.extract(*a, **{k: v for k, v in zip(map_kwargs.keys(), kw)})
                )  # noqa
                for a, kw in zip(zip(*map_args), zip(*map_kwargs.values()))
            ]
        return await asyncio.gather(*tasks)

    @classmethod
    def map(cls: type[T], *map_args: list[str], **map_kwargs: list[Any]) -> list[T]:
        """
        Map the AI Model over a sequence of arguments. Runs concurrently.
        """
        return run_sync(cls.amap(*map_args, **map_kwargs))

    @classmethod
    def as_decorator(
        cls: type[T],
        base_model: Optional[type[BaseModel]] = None,
        instructions: Optional[str] = None,
        context_function: Optional[Callable[..., str]] = None,
        extract_prompt: Optional[Callable[..., Prompt]] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> type[T] | functools.partial[Any]:
        if not base_model:
            return functools.partial(
                cls.as_decorator,
                instructions=instructions,
                context_function=context_function,
                extract_prompt=extract_prompt,
                **kwargs,
            )
        subclass: type[T] = type(
            base_model.__name__,
            (cls,),
            {
                **dict(base_model.__dict__),
                "_chat_completion": ChatCompletion(
                    model=model,
                    **kwargs,
                ),
                "_instructions": instructions,
                "_context_function": context_function,
                "_extract_prompt": extract_prompt,
            },
        )  # type: ignore

        return subclass


ai_model = AIModel.as_decorator
