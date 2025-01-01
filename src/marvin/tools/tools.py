"""
Tools for AI agents.
"""

import functools
import inspect
import typing
from dataclasses import dataclass, field
from typing import Callable, Optional

from pydantic import Field, TypeAdapter
from pydantic.errors import PydanticSchemaGenerationError
from typing_extensions import Annotated


def run_coro_as_sync(coro):
    """Run a coroutine synchronously."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@dataclass
class Tool:
    """A tool that can be used by an AI agent."""

    name: str
    description: str
    fn: Callable
    parameters: dict

    # Optional instructions to display to the agent as part of the system prompt
    # when this tool is available. Tool descriptions have a 1024
    # character limit, so this is a way to provide extra detail about behavior.
    instructions: Optional[str] = None

    metadata: dict = field(default_factory=dict)

    def run(self, input: dict):
        """Run the tool synchronously."""
        result = self.fn(**input)
        if inspect.isawaitable(result):
            result = run_coro_as_sync(result)
        return result

    async def run_async(self, input: dict):
        """Run the tool asynchronously."""
        result = self.fn(**input)
        if inspect.isawaitable(result):
            result = await result
        return result

    @classmethod
    def from_function(
        cls,
        fn: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        include_param_descriptions: bool = True,
        include_return_description: bool = True,
        metadata: Optional[dict] = None,
        **kwargs,
    ):
        """Create a Tool from a function."""
        name = name or fn.__name__
        description = description or fn.__doc__ or ""

        signature = inspect.signature(fn)
        try:
            parameters = TypeAdapter(fn).json_schema()
        except PydanticSchemaGenerationError:
            raise ValueError(
                f'Could not generate a schema for tool "{name}". '
                "Tool functions must have type hints that are compatible with Pydantic."
            )

        # load parameter descriptions
        if include_param_descriptions:
            for param in signature.parameters.values():
                # handle Annotated type hints
                if typing.get_origin(param.annotation) is Annotated:
                    param_description = " ".join(
                        str(a) for a in typing.get_args(param.annotation)[1:]
                    )
                # handle pydantic Field descriptions
                elif param.default is not inspect.Parameter.empty and isinstance(
                    param.default, Field
                ):
                    param_description = param.default.description
                else:
                    param_description = None

                if param_description:
                    parameters["properties"][param.name][
                        "description"
                    ] = param_description

        # Handle return type description
        if (
            include_return_description
            and signature.return_annotation is not inspect._empty
        ):
            return_schema = {}
            try:
                return_schema.update(
                    TypeAdapter(signature.return_annotation).json_schema()
                )
            except PydanticSchemaGenerationError:
                pass
            finally:
                if typing.get_origin(signature.return_annotation) is Annotated:
                    return_schema["annotation"] = " ".join(
                        str(a) for a in typing.get_args(signature.return_annotation)[1:]
                    )

            if return_schema:
                description += f"\n\nReturn value schema: {return_schema}"

        if not description:
            description = "(No description provided)"

        if len(description) > 1024:
            raise ValueError(
                f"{name}: The tool's description exceeds 1024 characters. "
                "Please provide a shorter description, fewer annotations, or pass "
                "`include_param_descriptions=False` or `include_return_description=False` "
                "to `from_function`."
            )

        return cls(
            name=name,
            description=description,
            parameters=parameters,
            fn=fn,
            instructions=instructions,
            metadata=metadata or {},
            **kwargs,
        )

    def serialize_for_prompt(self) -> dict:
        """Serialize the tool for inclusion in a prompt."""
        return self.model_dump(include={"name", "description", "metadata"})


def tool(
    fn: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    instructions: Optional[str] = None,
    include_param_descriptions: bool = True,
    include_return_description: bool = True,
    metadata: Optional[dict] = None,
    **kwargs,
) -> Tool:
    """
    Decorator for turning a function into a Tool
    """
    kwargs.update(
        instructions=instructions,
        include_param_descriptions=include_param_descriptions,
        include_return_description=include_return_description,
        metadata=metadata or {},
    )
    if fn is None:
        return functools.partial(tool, name=name, description=description, **kwargs)
    return Tool.from_function(fn, name=name, description=description, **kwargs)
