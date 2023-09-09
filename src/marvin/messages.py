"""'
    Hello there! Welcome to the messages module.

    This module contains the `Message` and `Prompt` classes, which are used to represent 
    messages and prompts in Marvin. 
        - A message is a single message in a conversation, an atomic unit of communication. 
        - A prompt is a collection of messages, functions or response_model. 

    There are two ways to create a message:
        - Using the `Message` class.
        - Using the `Message.from_transcript` class method.
            - This method parses a transcript and returns a list of messages. 

    There are two ways to create a prompt:
        - Using the `Prompt` class.
        - Using the `Prompt.from_transcript` class method.
            - This method parses a transcript and returns a prompt.

    The `Prompt` class can also be used as a function decorator. It will treat 
    the docstring of the function as a transcript and parse it to create a prompt, 
    rendering the messages as Jinja templates with the function's parameters as
    context variables.
"""  # noqa

import inspect
import re
from enum import Enum
from functools import partial, wraps
from types import GenericAlias
from typing import Any, Callable, Literal, Optional, TypeVar, Union, overload

from jinja2 import Environment, meta
from pydantic import BaseModel, Field, Json

from marvin._compat import _model_dump, model_fields  # type: ignore
from marvin.types import ParamSpec

from .serializers import model_serialize

R = TypeVar("R", bound="Role")
P = ParamSpec("P")
L = ParamSpec("L")

env = Environment()


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

    function_call: Optional["FunctionCall"] = Field(
        default=None, repr=False, description="""The function call to make."""
    )

    def render(
        self, environment: Optional[Environment] = None, **kwargs: Any
    ) -> "Message":
        """
        Render the message.
        """
        environment = env or Environment()

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
        ...     'SYSTEM: You are Marvin, the Paranoid Android.'
        ...     'USER: Hello, Marvin.'
        ...     'ASSISTANT: How are you?'
        ... )
        >>> messages = Message.from_transcript(transcript)
        >>> messages
        [
            Message(role='system', content='Hello, I am Marvin.'),
            Message(role='user', content='Hello, Marvin.'),
            Message(role='system', content='How are you?')
        ]
        """  # noqa
        # If Message is subclassed, get the roles from the subclass.
        roles: type[Enum] = getattr(model_fields(cls).get("role"), "type_", Role)
        # Get the names of the roles.
        names = "[\n\s]+" + "|".join([f"[\n\s]+{role.name}" for role in roles])
        # Create a regex pattern to match the roles and their content.
        pattern = re.compile(f"({names}): (.*?)(?=(?:{names}:)|$)", re.DOTALL)
        # Find all the statements in the transcript.
        statements = re.findall(pattern, "\n\n" + template)
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


class FunctionCall(BaseModel):
    name: Optional[str] = Field(
        default=None, description="""The name of the function to call."""
    )
    arguments: Json[dict[str, Any]] = Field(
        default_factory=dict, description="""The arguments to pass to the function."""
    )


class Prompt(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    functions: list[Union[Callable[..., Any], type[BaseModel], dict[str, Any]]] = Field(
        default_factory=list
    )
    function_call: Optional[Union[Literal["auto"], dict[Literal["name"], str]]] = Field(
        default=None
    )
    response_model: Union[type, GenericAlias, type[BaseModel], Callable[..., Any]] = (
        Field(default=None, exclude=True)
    )

    def render(
        self, environment: Optional[Environment] = None, **kwargs: Any
    ) -> "Prompt":
        """
        Render the messages.
        """
        return Prompt(
            messages=[
                message
                for message in MessageList(self.messages).render(
                    environment=environment, **kwargs
                )
            ],
            functions=self.functions,
            function_call=self.function_call,
            response_model=self.response_model,
        )

    def serialize(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Serialize the prompt.
        """

        extras = _model_dump(
            self, exclude={"messages", "response_model", "function_call", "functions"}
        )

        return model_serialize(
            **{
                **extras,
                "messages": self.messages,
                "functions": self.functions,
                "function_call": self.function_call,
                "response_model": self.response_model,
                **kwargs,
            }  # type: ignore
        )

    @classmethod
    def from_transcript(
        cls, template: str, role: Optional[Role] = None, **kwargs: Any
    ) -> "Prompt":
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
        >>> prompt = Prompt.from_transcript(transcript)
        >>> prompt
        Prompt(
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
    ) -> Callable[[Callable[P, None]], Callable[P, "Prompt"]]:
        pass

    @overload
    @classmethod
    def as_decorator(
        cls,
        func: Callable[P, Any],
        *,
        environment: Optional[Environment] = None,
        ctx: Optional[dict[str, Any]] = None,
        role: Optional[Role] = None,
        response_model: Optional[type[BaseModel]] = None,
    ) -> Callable[P, "Prompt"]:
        pass

    @classmethod
    def as_decorator(
        cls,
        func: Optional[Callable[P, Any]] = None,
        *,
        environment: Optional[Environment] = None,
        ctx: Optional[dict[str, Any]] = None,
        role: Optional[Role] = None,
        response_model: Optional[type[BaseModel]] = None,
    ) -> Union[
        Callable[[Callable[P, None]], Callable[P, None]],
        Callable[[Callable[P, None]], Callable[P, "Prompt"]],
        Callable[P, "Prompt"],
    ]:
        def wrapper(
            func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs
        ) -> Prompt:
            signature = inspect.signature(func)
            params = signature.bind(*args, **kwargs)
            params.apply_defaults()
            return Prompt.from_transcript(
                template=func.__doc__ or "",
                role=role,
                response_model=response_model or signature.return_annotation,
            ).render(
                environment=environment or env,
                **(ctx or {}),
                __self__=func,
                __params__=params.arguments,
                **params.arguments,
                response_model=response_model or signature.return_annotation,
            )

        if func is not None:
            return wraps(func)(partial(wrapper, func))

        def decorator(func: Callable[P, None]) -> Callable[P, Prompt]:
            return wraps(func)(partial(wrapper, func))

        return decorator

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
        extra = "allow"


prompt_fn = Prompt.as_decorator


def validate_template(
    func: Callable[P, Any],
    template: Optional[str] = None,
    ctx: Optional[dict[str, Any]] = None,
    environment: Environment | None = None,
) -> bool:
    # If environment is not provided, create a new one.
    env = environment or Environment()

    # Get the signature of the function
    signature = inspect.signature(func)
    signature_params = set(signature.parameters.keys()).union(
        {"response_model", "__self__", "__params__"}
    )
    context_params = set((ctx or {}).keys())

    # Get the undeclared variables in the docstring
    string_template: str = template or func.__doc__ or ""
    template_params = meta.find_undeclared_variables(env.parse(string_template))

    # Check if the signature and context contain all the variables in the template
    return signature_params.union(context_params).issuperset(template_params)
