"""'
    Hello there! Welcome to the messages module.

    This module contains the `Message` and `BasePrompt` classes, which are used to represent 
    messages and BasePrompts in Marvin. 
        - A message is a single message in a conversation, an atomic unit of communication. 
        - A BasePrompt is a collection of messages, functions or response_model. 

    There are two ways to create a message:
        - Using the `Message` class.
        - Using the `Message.from_transcript` class method.
            - This method parses a transcript and returns a list of messages. 

    There are two ways to create a BasePrompt:
        - Using the `BasePrompt` class.
        - Using the `BasePrompt.from_transcript` class method.
            - This method parses a transcript and returns a BasePrompt.

    The `BasePrompt` class can also be used as a function decorator. It will treat 
    the docstring of the function as a transcript and parse it to create a BasePrompt, 
    rendering the messages as Jinja templates with the function's parameters as
    context variables.
"""  # noqa

import inspect
import re
from datetime import datetime
from enum import Enum
from functools import partial, wraps
from typing import Any, Callable, List, Literal, Optional, TypeVar, Union, overload
from zoneinfo import ZoneInfo

from jinja2 import (
    Environment,
    StrictUndefined,
    select_autoescape,
)
from pydantic import Json

from marvin._compat import (  # type: ignore
    BaseModel,
    Field,
    cast_to_model,
    model_copy,
    model_dump,  # type: ignore
    model_fields,
    root_validator,
)
from marvin.types import ParamSpec

from .serializers import model_serialize

M = TypeVar("M", bound="Message")
P = TypeVar("P", bound="BasePrompt")


R = ParamSpec("R")
L = ParamSpec("L")

env = Environment(
    autoescape=select_autoescape(default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
    undefined=StrictUndefined,
)

env.globals.update(  # type: ignore
    zip=zip,  # type: ignore
    now=lambda: datetime.now(ZoneInfo("UTC")),  # type: ignore
)  #


class Role(Enum):
    """
    The role of the message.
    - `system`: The message is from the system.
    - `assistant`: The message is from the assistant.
    - `user`: The message is from the user.
    - `function`: The message is a function call.
    """

    System = "system"
    Assistant = "assistant"
    Human = "user"
    Function = "function"


class FunctionCall(BaseModel):
    name: Optional[str] = Field(
        default=None, description="""The name of the function to call."""
    )
    arguments: Json[dict[str, Any]] = Field(
        default_factory=dict, description="""The arguments to pass to the function."""
    )


class Message(BaseModel):
    """
    A Message represents a single message in a conversation.

    :param role: The role of the message.
    :param content: The content of the message.
    :param name: The name of the function to call.
    :param function_call: The function call to make.

    """

    role: Role = Field(
        default="system",
        description="""
            The role of the message, e.g. `system`, `assistant`, `user`, `function`.
        """,
    )

    content: str = Field(..., description="""The content of the message.""")

    name: Optional[str] = Field(
        default=None, repr=False, description="""The name of the function to call."""
    )

    function_call: Optional[FunctionCall] = Field(
        default=None, repr=False, description="""The function call to make."""
    )

    def __or__(self: M, other: Union[M, list[M]]) -> "MessageList":
        """
        Concatenate two messages.
        """
        if isinstance(other, list):
            response: list[M] = [self]
            response.extend(other)
            return MessageList(*response)
        else:
            return MessageList([self, other])

    def __ror__(self: M, other: Union[M, list[M]]) -> "MessageList":
        """
        Concatenate two messages.
        """
        if isinstance(other, list):
            response: list[M] = other
            response = [self] + response
            return MessageList(*response)
        else:
            return MessageList([other, self])

    def render(
        self, environment: Optional[Environment] = None, **kwargs: Any
    ) -> "Message":
        """
        Render the message.
        """
        environment = environment or env

        return Message(
            role=self.role,
            content=inspect.cleandoc(
                environment.from_string(self.content).render(**kwargs)
            ).strip(),
            name=self.name,
            function_call=self.function_call,
        )

    @classmethod
    def from_transcript(
        cls,
        template: str,
        role: Optional[Role] = None,
    ) -> list["Message"]:
        """
        Create a list of messages from a transcript.
        :param template: The transcript to parse.
        :param role: The role of the first message in the transcript if it is not specified.

        :returns: A list of messages.

        :Example:
        >>> from marvin import Message
        >>> transcript = (
        ...     'System: You are Marvin, the Paranoid Android.'
        ...     'User: Hello, Marvin.'
        ...     'Assistant: How are you?'
        ... )
        >>> messages = Message.from_transcript(transcript)
        >>> messages
        [
            Message(role='system', content='Hello, I am Marvin.'),
            Message(role='user', content='Hello, Marvin.'),
            Message(role='assistant', content='How are you?')
        ]
        """  # noqa
        # If Message is subclassed, get the roles from the subclass.
        roles: type[Enum] = getattr(model_fields(cls).get("role"), "type_", Role)
        # Get the names of the roles.
        names = "[\n\s]+" + "|".join([f"[\n\s]+{role.name}" for role in roles])  # type: ignore # noqa
        # Create a regex pattern to match the roles and their content.
        pattern = re.compile(f"({names}): (.*?)(?=(?:{names}:)|$)", re.DOTALL)
        # Find all the statements in the transcript.
        statements = re.findall(pattern, "\n\nSystem: " + template)
        if not statements:
            return [
                Message(role=Role(role or next(iter(roles))), content=template.strip())
            ]
        return [
            Message(role=Role[role.strip()], content=content.strip())
            for role, content in statements
            if content.strip()
        ]

    class Config:
        use_enum_values = True


class MessageList(list[Message]):
    """
    Internal helper class for list of messages.
    """

    def render(
        self, environment: Optional[Environment] = None, **kwargs: Any
    ) -> "MessageList":
        """
        Render the messages.
        """
        return MessageList(
            [message.render(environment=environment, **kwargs) for message in self]
        )


class BasePrompt(BaseModel):
    messages: list[Message] = Field(default_factory=list)

    functions: Optional[
        List[Union[Callable[..., Any], type[BaseModel], dict[str, Any]]]
    ] = Field(default_factory=list)

    function_call: Optional[Union[Literal["auto"], dict[Literal["name"], str]]] = Field(
        default=None
    )

    response_model: Optional[Any] = Field(default=None)

    response_model_name: Optional[str] = Field(default=None, repr=False)

    response_model_description: Optional[str] = Field(default=None, repr=False)

    def render(self: P, environment: Optional[Environment] = None, **kwargs: Any) -> P:
        """
        Render the messages.
        """

        extras: dict[str, Any] = model_dump(
            self,
            exclude={  # type: ignore
                "messages",
                "response_model",
                "function_call",
                "functions",
                "response_model_name",
                "response_model_description",
            },
        )

        response = self.__class__(
            messages=[
                message
                for message in MessageList(self.messages).render(
                    environment=environment, **(extras | kwargs)
                )
            ],
            functions=self.functions,
            function_call=self.function_call,
            response_model=self.response_model,
            response_model_name=self.response_model_name,
            response_model_description=self.response_model_description,
            **extras,
        )

        return response

    def serialize(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Serialize the BasePrompt.
        """

        return model_serialize(
            **{
                "messages": self.messages,
                "functions": self.functions,
                "function_call": self.function_call,
                "response_model": self.response_model,
                "response_model_name": self.response_model_name,
                "response_model_description": self.response_model_description,
                **kwargs,
            }  # type: ignore
        )

    def __or__(self: P, other: Union[M, P, list[Union[M, P]]]) -> "BasePrompt":
        """
        Concatenate two messages.
        """
        if isinstance(other, list):
            copy = model_copy(self)
            for item in other:
                if isinstance(item, Message):
                    copy.messages.append(item)
                else:
                    copy.messages.extend(item.messages)
        else:
            copy = model_copy(self)
            if isinstance(other, Message):
                copy.messages.append(other)
            else:
                copy.messages.extend(other.messages)
        return copy

    def __ror__(self: P, other: Union[M, P, list[Union[M, P]]]) -> "BasePrompt":
        """
        Concatenate two messages.
        """
        if isinstance(other, list):
            copy = model_copy(self)
            for item in reversed(other):
                if isinstance(item, Message):
                    copy.messages.insert(0, item)
                else:
                    copy.messages.extend(item.messages)
        else:
            copy = model_copy(self)
            if isinstance(other, Message):
                copy.messages.insert(0, other)
            else:
                copy.messages.extend(other.messages)
        return copy

    @classmethod
    def from_transcript(
        cls: type[P], template: str, role: Optional[Role] = None, **kwargs: Any
    ) -> P:
        """
        Create a list of messages from a transcript.
        :param template: The transcript to parse.
        :param role: The role of the first message in the transcript if it is not specified.

        :returns: A list of messages.

        :Example:
        >>> from marvin import Message
        >>> transcript = (
        ...     'SYSTEM: You are Marvin, the Paranoid Android.'
        ...     'USER: Hello, Marvin.'
        ...     'ASSISTANT: How are you?'
        ... )
        >>> BasePrompt = BasePrompt.from_transcript(transcript)
        >>> BasePrompt
        BasePrompt(
            messages = [
                Message(role='system', content='Hello, I am Marvin.'),
                Message(role='user', content='Hello, Marvin.'),
                Message(role='system', content='How are you?')
            ]
        )
        """  # noqa
        return cls(messages=Message.from_transcript(template, role=role), **kwargs)

    @overload
    @classmethod
    def as_decorator(
        cls,
        *,
        environment: Optional[Environment] = None,
        ctx: Optional[dict[str, Any]] = None,
        role: Optional[Role] = None,
        response_model: Optional[type[BaseModel]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
    ) -> Callable[[Callable[R, None]], Callable[R, "BasePrompt"]]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls,
        func: Callable[R, Any],
        *,
        environment: Optional[Environment] = None,
        ctx: Optional[dict[str, Any]] = None,
        role: Optional[Role] = None,
        response_model: Optional[type[BaseModel]] = None,
        response_model_name: Optional[str] = None,
        response_model_description: Optional[str] = None,
    ) -> Callable[R, "BasePrompt"]:
        pass

    @classmethod
    def as_decorator(
        cls,
        func: Optional[Callable[R, Any]] = None,
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
    ) -> Union[
        Callable[[Callable[R, None]], Callable[R, None]],
        Callable[[Callable[R, None]], Callable[R, "BasePrompt"]],
        Callable[R, "BasePrompt"],
    ]:
        def wrapper(
            func: Callable[R, Any], *args: R.args, **kwargs: R.kwargs
        ) -> BasePrompt:
            signature = inspect.signature(func)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()
            return BasePrompt.from_transcript(
                template=func.__doc__ or "",
                role=role,
                functions=functions or [],
                function_call=function_call,
                response_model=response_model or signature.return_annotation,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
            ).render(
                environment=environment or env,
                **(ctx or {}),
                __self__=func,
                __params__=params.arguments,
                **params.arguments,
                response_model=response_model or signature.return_annotation,
                response_model_name=response_model_name,
                response_model_description=response_model_description,
            )

        if func is not None:
            return wraps(func)(partial(wrapper, func))

        def decorator(func: Callable[R, None]) -> Callable[R, BasePrompt]:
            return wraps(func)(partial(wrapper, func))

        return decorator

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
        extra = "allow"


prompt = BasePrompt.as_decorator


class Prompt(BasePrompt):
    def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> "Prompt":
        return self

    @root_validator(pre=False)
    def render_docstring(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Render the docstring.
        """
        if response_model := values.get("response_model"):
            values["response_model"] = cast_to_model(
                response_model,
                name=values.get("response_model_name", None),
                description=values.get("response_model_description", None),
            )
        if not values.get("messages"):
            message = Message.from_transcript(cls.__doc__ or "")
            values["messages"] = [
                message.render(**values).render(**values) for message in message
            ]
        return values


# def validate_template(
#     func: Callable[P, Any],
#     template: Optional[str] = None,
#     ctx: Optional[dict[str, Any]] = None,
#     environment: Environment | None = None,
# ) -> bool:
#     # If environment is not provided, create a new one.
#     env = environment or Environment()

#     # Get the signature of the function
#     signature = inspect.signature(func)
#     signature_params = set(signature.parameters.keys()).union(
#         {"response_model", "__self__", "__params__"}
#     )
#     context_params = set((ctx or {}).keys())

#     # Get the undeclared variables in the docstring
#     string_template: str = template or func.__doc__ or ""
#     template_params = meta.find_undeclared_variables(env.parse(string_template))

#     # Check if the signature and context contain all the variables in the template
#     return signature_params.union(context_params).issuperset(template_params)
