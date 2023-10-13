import abc
import inspect
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

from jinja2 import Environment
from pydantic import BaseModel, Field
from typing_extensions import ParamSpec, Self

import marvin
from marvin._compat import cast_to_json, cast_to_model, model_dump, model_json_schema
from marvin.core.ChatCompletion import ChatCompletion
from marvin.core.ChatCompletion.abstract import AbstractChatCompletion
from marvin.utilities.messages import Message, Role
from marvin.utilities.strings import count_tokens, jinja_env

T = TypeVar("T")
P = ParamSpec("P")


class MessageList(list[Message]):
    def render(
        self: Self,
        **kwargs: Any,
    ) -> Self:
        return render_prompts(self, render_kwargs=kwargs)

    def serialize(
        self: Self,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return [model_dump(message) for message in self.render(**kwargs)]


class PromptList(list[Union["Prompt", Message]]):
    def __init__(self, prompts: list[Union["Prompt", Message]]):
        super().__init__(prompts)

    def render(
        self: Self,
        content: Optional[str] = None,
        render_kwargs: Optional[dict[str, Any]] = None,
    ) -> list[Message]:
        return render_prompts(self, render_kwargs=render_kwargs)

    def dict(self, **kwargs: Any):
        return [model_dump(message) for message in self.render(**kwargs)]

    def __call__(self, **kwargs: Any):
        return self.render(**kwargs)


class BasePrompt(BaseModel, abc.ABC):
    """
    Base class for prompt templates.
    """

    functions: Optional[
        Union[
            List[Union[Dict[str, Any], Callable[..., Any], type[BaseModel]]],
            Callable[
                ..., List[Union[Dict[str, Any], Callable[..., Any], type[BaseModel]]]
            ],
        ]
    ] = Field(default=None)

    function_call: Optional[
        Union[
            Literal["auto"],
            Dict[Literal["name"], str],
        ]
    ] = Field(default=None)

    response_model: Optional[
        Union[
            type,
            type[BaseModel],
            Any,
            Callable[..., Union[type, type[BaseModel], Any]],
        ]
    ] = Field(default=None)

    response_model_name: Optional[str] = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    response_model_description: Optional[str] = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    response_model_field_name: Optional[str] = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    position: Optional[int] = Field(
        default=None,
        repr=False,
        exclude=True,
        description=(
            "Position indicates the desired index for this prompt's messages. 0"
            " indicates they should be first; 1 indicates they should be second; -1"
            " indicates they should be last; None indicates they should be between any"
            " prompts that do request a position."
        ),
    )
    priority: float = Field(
        default=10,
        repr=False,
        exclude=True,
        description=(
            "Priority indicates the weight given when trimming messages to satisfy"
            " context limitations. Lower numbers indicate higher priority e.g. the"
            " highest priority is 0. The default is 10. Ties will be broken by message"
            " timestamp and role."
        ),
    )

    @abc.abstractmethod
    def generate(self, **kwargs: Any) -> list["Message"]:
        """
        Abstract method that generates a list of messages from the prompt template
        """
        pass

    def render(
        self: Self, content: str, render_kwargs: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Helper function for rendering any jinja2 template with runtime render kwargs
        """
        return jinja_env.from_string(inspect.cleandoc(content)).render(
            **(render_kwargs or {})
        )

    def __or__(self: Self, other: Union[Self, list[Self]]) -> PromptList:
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
        # when the right operand is a Prompt object
        if isinstance(other, Prompt):
            return PromptList([self, other])
        # when the right operand is a list
        elif isinstance(other, list[Prompt]):
            return PromptList([self, *other])
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(self).__name__}' and"
                f" '{type(other).__name__}'"
            )

    def __ror__(self, other):
        """
        Supports pipe syntax:
        prompt = (
            Prompt()
            | Prompt()
            | Prompt()
        )
        """
        # when the left operand is a Prompt object
        if isinstance(other, Prompt):
            return PromptList([other, self])
        # when the left operand is a list
        elif isinstance(other, list):
            return PromptList(other + [self])
        else:
            raise TypeError(
                f"unsupported operand type(s) for |: '{type(other).__name__}' and"
                f" '{type(self).__name__}'"
            )


class Prompt(BasePrompt, Generic[P], extra="allow", arbitrary_types_allowed=True):
    def generate(self, **kwargs: Any) -> list[Message]:
        response = Message.from_transcript(
            self.render(content=self.__doc__ or "", render_kwargs=kwargs)
        )
        return response

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        extras = model_dump(
            self,
            exclude=set(self.__fields__.keys()),
            exclude_none=True,
        )
        return {
            "messages": [
                model_dump(message, include={"content", "role"})
                for message in render_prompts(
                    self.generate(
                        **extras | kwargs | {"response_model": self.response_model}
                    )
                )
            ],
            "functions": self.functions,
            "function_call": self.function_call,
            "response_model": self.response_model,
        }

    def to_chat_completion(
        self, model: Optional[str] = None, **model_kwargs: Any
    ) -> AbstractChatCompletion[T]:
        return ChatCompletion(model=model, **model_kwargs)(**self.to_dict())

    def serialize(self, model: Any = None, **kwargs: Any) -> dict[str, Any]:
        if model:
            return model(**self.to_dict(**kwargs))._serialize_request()  # type: ignore

        _dict = self.to_dict(**kwargs)

        response: dict[str, Any] = {}
        response["messages"] = _dict["messages"]

        if _dict.get("response_model", None):
            response["functions"] = [
                model_json_schema(cast_to_model(_dict["response_model"]))
            ]
            response["function_call"] = {"name": response["functions"][0]["name"]}
        elif _dict.get("functions", None):
            response["functions"] = [
                cast_to_json(function) if callable(function) else function
                for function in _dict["functions"]
            ]
            if _dict["function_call"]:
                response["function_call"] = _dict["function_call"]

        return response

    @classmethod
    def as_decorator(
        cls: type[Self],
        func: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[Environment] = None,
        ctx: Optional[dict[str, Any]] = None,
        role: Optional[Role] = None,
        functions: Optional[
            list[Union[Callable[..., Any], type[BaseModel], dict[str, Any]]]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
        response_model_field_name: Optional[str] = None,
        serialize_on_call: bool = True,
    ) -> Union[
        Callable[[Callable[P, None]], Callable[P, None]],
        Callable[[Callable[P, None]], Callable[P, Self]],
        Callable[P, Self],
    ]:
        def wrapper(func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> Self:
            signature = inspect.signature(func)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()
            response = type(getattr(cls, "__name__", ""), (cls,), {})(
                __params__=params.arguments,
                **params.arguments,
                **ctx or {},
                functions=functions,
                function_call=function_call,
                response_model=cast_to_model(
                    response_model or signature.return_annotation,
                    name=response_model_name,
                    description=response_model_description,
                    field_name=response_model_field_name,
                ),
                response_model_name=response_model_name,
                response_model_description=response_model_description,
                response_model_field_name=response_model_field_name,
            )
            response.__doc__ = func.__doc__
            if serialize_on_call:
                return response.serialize()
            return response

        if func is not None:
            return wraps(func)(partial(wrapper, func))

        def decorator(func: Callable[P, None]) -> Callable[P, Self]:
            return wraps(func)(partial(wrapper, func))

        return decorator


prompt_fn = Prompt.as_decorator


class MessageWrapper(BasePrompt):
    """
    A Prompt class that stores and returns a specific Message
    """

    message: Message

    def generate(self, **kwargs: Any) -> list[Message]:
        return [self.message]


def render_prompts(
    prompts: Union[list[Message], list[Union[Prompt, Message]]],
    render_kwargs: Optional[dict[str, Any]] = None,
    max_tokens: Optional[int] = None,
) -> MessageList:
    max_tokens = max_tokens or marvin.settings.llm_max_context_tokens

    all_messages = []

    # if the user supplied any messages, wrap them in a MessageWrapper so we can
    # treat them as prompts for sorting and filtering
    prompts = [
        MessageWrapper(message=p) if isinstance(p, Message) else p for p in prompts
    ]

    # Separate prompts by positive, none and negative position
    pos_prompts = [p for p in prompts if p.position is not None and p.position >= 0]
    none_prompts = [p for p in prompts if p.position is None]
    neg_prompts = [p for p in prompts if p.position is not None and p.position < 0]

    # Sort the positive prompts in ascending order and negative prompts in
    # descending order, but both with timestamp ascending
    pos_prompts = sorted(pos_prompts, key=lambda c: c.position)
    neg_prompts = sorted(neg_prompts, key=lambda c: c.position, reverse=True)

    # generate messages from all prompts
    for i, prompt in enumerate(pos_prompts + none_prompts + neg_prompts):
        prompt_messages = prompt.generate(**(render_kwargs or {})) or []
        all_messages.extend((prompt.priority, i, m) for m in prompt_messages)

    # sort all messages by (priority asc, position desc)  and stop when the
    # token limit is reached. This will prefer high-priority messages that are
    # later in the message chain.
    current_tokens = 0
    allowed_messages = []
    for _, position, msg in sorted(all_messages, key=lambda m: (m[0], -1 * m[1])):
        if current_tokens >= max_tokens:
            break
        allowed_messages.append((position, msg))
        current_tokens += count_tokens(msg.content)

    # sort allowed messages by position to restore original order
    messages = [msg for _, msg in sorted(allowed_messages, key=lambda m: m[0])]

    # Combine all system messages into one and insert at the index of the first
    # system message
    system_messages = [m for m in messages if m.role == Role.SYSTEM.value]
    if len(system_messages) > 1:
        system_message = Message(
            role=Role.SYSTEM,
            content="\n\n".join([m.content for m in system_messages]),
        )
        system_message_index = messages.index(system_messages[0])
        messages = [m for m in messages if m.role != Role.SYSTEM.value]
        messages.insert(system_message_index, system_message)

    # return all messages
    return messages
