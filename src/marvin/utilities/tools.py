"""Module for LLM tool utilities."""

import inspect
import json
from functools import update_wrapper
from typing import (
    Any,
    Callable,
    GenericAlias,
    Optional,
    TypeVar,
    Union,
)

import pydantic
from pydantic import BaseModel, TypeAdapter, create_model
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode

from marvin.types import Function, Tool
from marvin.utilities.asyncio import run_sync
from marvin.utilities.logging import get_logger

logger = get_logger("Tools")

T = TypeVar("T")
U = TypeVar("U", bound=Union[type, GenericAlias])
M = TypeVar("M", bound=pydantic.BaseModel)


def custom_partial(func: Callable, **fixed_kwargs: Any) -> Callable:
    """
    Returns a new function with partial application of the given keyword arguments.
    The new function has the same __name__ and docstring as the original, and its
    signature excludes the provided kwargs.
    """

    # Define the new function with a dynamic signature
    def wrapper(**kwargs):
        # Merge the provided kwargs with the fixed ones, prioritizing the former
        all_kwargs = {**fixed_kwargs, **kwargs}
        return func(**all_kwargs)

    # Update the wrapper function's metadata to match the original function
    update_wrapper(wrapper, func)

    # Modify the signature to exclude the fixed kwargs
    original_sig = inspect.signature(func)
    new_params = [
        param
        for param in original_sig.parameters.values()
        if param.name not in fixed_kwargs
    ]
    wrapper.__signature__ = original_sig.replace(parameters=new_params)

    return wrapper


class ModelSchemaGenerator(GenerateJsonSchema):
    def generate(self, schema: Any, mode: JsonSchemaMode = "validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop("title", None)
        return json_schema


def tool_from_type(type_: U, tool_name: str = None) -> Tool[U]:
    annotated_metadata = getattr(type_, "__metadata__", [])
    if isinstance(next(iter(annotated_metadata), None), FieldInfo):
        metadata = next(iter(annotated_metadata))
    else:
        metadata = FieldInfo(description="The formatted response")

    model = create_model(
        tool_name or "FormatResponse",
        __doc__="Format the response with valid JSON.",
        __module__=__name__,
        **{"value": (type_, metadata)},
    )

    def tool_fn(**data) -> U:
        return TypeAdapter(model).validate_python(data).value

    return tool_from_model(model, python_fn=tool_fn)


def tool_from_model(model: type[M], python_fn: Callable[[str], M] = None):
    """
    Creates an OpenAI-compatible tool from a Pydantic model class.
    """

    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(
            f"Expected a Pydantic model class, but got {type(model).__name__}."
        )

    def tool_fn(**data) -> M:
        return TypeAdapter(model).validate_python(data)

    return Tool[M](
        type="function",
        function=Function[M].create(
            name=model.__name__,
            description=model.__doc__,
            parameters=model.model_json_schema(schema_generator=ModelSchemaGenerator),
            model=model,
            _python_fn=python_fn or tool_fn,
        ),
    )


def tool_from_function(
    fn: Callable[..., T],
    name: Optional[str] = None,
    description: Optional[str] = None,
    kwargs: Optional[dict[str, Any]] = None,
):
    """
    Creates an OpenAI-compatible tool from a Python function.

    If any kwargs are provided, they will be stored and provided at runtime.
    Provided kwargs will be removed from the tool's parameter schema.
    """
    if kwargs:
        fn = custom_partial(fn, **kwargs)

    schema = pydantic.TypeAdapter(
        fn, config=pydantic.ConfigDict(arbitrary_types_allowed=True)
    ).json_schema()

    return Tool[T](
        type="function",
        function=Function[T].create(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=schema,
            _python_fn=fn,
        ),
    )


def call_function_tool(
    tools: list[Tool],
    function_name: str,
    function_arguments_json: str,
    return_string: bool = False,
):
    tool = next(
        (
            tool
            for tool in tools
            if getattr(tool, "function", None) and tool.function.name == function_name
        ),
        None,
    )
    if (
        not tool
        or not tool.function
        or not tool.function._python_fn
        or not tool.function.name
    ):
        raise ValueError(f"Could not find function '{function_name}'")

    arguments = json.loads(function_arguments_json)
    logger.debug_kv(
        f"{tool.function.name}", f"called with arguments: {arguments}", "green"
    )
    output = tool.function._python_fn(**arguments)
    if inspect.isawaitable(output):
        output = run_sync(output)
    truncated_output = str(output)[:100]
    if len(truncated_output) < len(str(output)):
        truncated_output += "..."
    logger.debug_kv(f"{tool.function.name}", f"returned: {truncated_output}", "green")
    if return_string and not isinstance(output, str):
        output = json.dumps(output)
    return output
