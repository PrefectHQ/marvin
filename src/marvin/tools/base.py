# This module defines the `Tool` class and the `tool` function decorator.

# The `Tool` class is a base class for creating tools that can be used
# in the Marvin engine. Each tool has a name, a description, and a
# function (`fn`) that implements the tool's functionality.

# The `tool` function is a decorator that can be used to convert a
# function into a `Tool` instance.


import inspect
from functools import partial
from typing import Any, Callable, Optional, TypeVar, Union

from pydantic import BaseModel

from marvin.utilities.strings import jinja_env

from .._compat import field_validator
from ..engine.language_models import OpenAIFunction
from ..utilities.types import LoggerMixin, function_to_openapi_schema

T = TypeVar("T", bound=Callable[..., Any])


class Tool(LoggerMixin, BaseModel):
    """
    A tool in the Marvin engine.

    Attributes:
        name (str): The name of the tool.
        description (str): A description of what the tool does.
        fn (Callable): The function that implements the tool's functionality.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    fn: Optional[Callable[..., Any]] = None

    @classmethod
    def from_function(
        cls,
        fn: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "Tool":
        """
        Create a `Tool` instance from a function.

        Args:
            fn (Callable): The function that implements the tool's functionality.
            name (str, optional): The name of the tool. Defaults to the function's name.
            description (str, optional): A description of the tool. Defaults to the
            function's docstring.

        Returns:
            Tool: A `Tool` instance.
        """
        name = name or fn.__name__
        description = description or fn.__doc__
        return cls(name=name, description=description or "", fn=fn)

    @field_validator("name")
    def default_name_from_class_name(cls, v: Optional[str]) -> str:
        """
        A validator for the `name` attribute that defaults to the class name if `name`
        is not provided.

        Args:
            v (str, optional): The provided name.

        Returns:
            str: The validated name.
        """
        return v or str(getattr(cls, "__name__", "Tool"))

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Run the tool's function with the provided arguments.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Any: The return value of the function.

        Raises:
            NotImplementedError: If the tool's function is not set.
        """
        if not self.fn:
            raise NotImplementedError()
        return self.fn(*args, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Allow the tool to be called like a function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Any: The return value of the function.
        """
        return self.run(*args, **kwargs)

    def argument_schema(self) -> dict[str, Any]:
        """
        Get the argument schema for the tool's function.

        Returns:
            dict: The argument schema.
        """
        schema: dict[str, Any] = function_to_openapi_schema(self.fn or self.run)  # type: ignore # noqa: E501
        schema.pop("title", None)  # type: ignore
        return schema  # type: ignore

    def as_openai_function(self) -> OpenAIFunction:
        """
        Convert the tool to an `OpenAIFunction`.

        Returns:
            OpenAIFunction: The tool as an `OpenAIFunction`.
        """
        schema = self.argument_schema()
        description = jinja_env.from_string(inspect.cleandoc(self.description or ""))
        description = description.render(**self.dict(), TOOL=self)

        return OpenAIFunction(
            name=self.name,
            description=description,
            parameters=schema,
            fn=self.run,
        )


def tool(
    arg: Optional[Union[T, None]] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Union[Tool, partial[T]]:
    """
    A decorator that converts a function into a `Tool` instance.

    Args:
        arg (Callable, optional): The function to convert. If `arg` is `None`, this
                                    function returns a partial application.
        name (str, optional): The name of the tool. Defaults to the function's name.
        description (str, optional): A description of the tool. Defaults to the
                                    function's docstring.

    Returns:
        Tool or partial: A `Tool` instance or a partial application of this function.

    Raises:
        TypeError: If `arg` is not a function or `None`.
    """
    if callable(arg):  # Direct function decoration
        return Tool.from_function(arg, name=name, description=description)
    elif arg is None:  # Partial application
        return partial(tool, name=name, description=description)  # type: ignore
    else:
        raise TypeError("Invalid argument passed to decorator.")
