from types import FunctionType, GenericAlias
from typing import Annotated, Any, Callable, Optional, Union, cast, get_origin, TypeVar

from pydantic import BaseModel, TypeAdapter, create_model
from pydantic.v1 import validate_arguments
from typing_extensions import Literal


def cast_callable_to_model(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> type[BaseModel]:
    response = validate_arguments(function).model
    for field in ["args", "kwargs", "v__duplicate_kwargs"]:
        fields = cast(dict[str, Any], response.__fields__)
        fields.pop(field, None)
    response.__title__ = name or function.__name__
    response.__name__ = name or function.__name__
    response.__doc__ = description or function.__doc__
    return response


def cast_type_or_alias_to_model(
    type_: Union[type, GenericAlias],
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    fields[field_name or "output"] = (type_, ...)
    response = create_model(
        name or "Output",
        __base__=BaseModel,
        **fields,
    )
    response.__doc__ = description or response.__doc__
    return response


def cast_to_model(
    function_or_type: Union[type, type[BaseModel], GenericAlias, Callable[..., Any]],
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> type[BaseModel]:
    """
    Casts a type or callable to a Pydantic model.
    """
    origin = get_origin(function_or_type) or function_or_type

    response = BaseModel
    if origin is Annotated:
        metadata: Any = next(iter(function_or_type.__metadata__), None)
        annotated_field_name: Optional[str] = field_name

        if hasattr(metadata, "extra") and isinstance(metadata.extra, dict):
            annotated_field_name: Optional[str] = metadata.extra.get("name", "")  # noqa
        elif hasattr(metadata, "json_schema_extra") and isinstance(
            metadata.json_schema_extra, dict
        ):  # noqa
            annotated_field_name: Optional[str] = metadata.json_schema_extra.get(
                "name", ""
            )  # noqa
        elif isinstance(metadata, dict):
            annotated_field_name: Optional[str] = metadata.get("name", "")  # noqa
        elif isinstance(metadata, str):
            annotated_field_name: Optional[str] = metadata
        else:
            pass
        annotated_field_description: Optional[str] = description or ""
        if hasattr(metadata, "description") and isinstance(metadata.description, str):
            annotated_field_description: Optional[str] = metadata.description  # noqa
        elif isinstance(metadata, dict):
            annotated_field_description: Optional[str] = metadata.get(
                "description", ""
            )  # noqa
        else:
            pass

        response = cast_to_model(
            function_or_type.__origin__,
            name=name,
            description=annotated_field_description,
            field_name=annotated_field_name,
        )
        response.__doc__ = annotated_field_description or ""
    elif origin in {dict, list, tuple, set, frozenset}:
        response = cast_type_or_alias_to_model(
            function_or_type, name, description, field_name
        )
    elif isinstance(origin, type):
        if issubclass(function_or_type, BaseModel):
            response = create_model(
                name or function_or_type.__name__,
                __base__=function_or_type,
            )
            response.__doc__ = description or function_or_type.__doc__

        else:
            response = cast_type_or_alias_to_model(
                function_or_type, name, description, field_name
            )
    elif isinstance(function_or_type, Callable):
        if isinstance(function_or_type, FunctionType):
            response = cast_callable_to_model(function_or_type, name, description)
    else:
        response = cast_type_or_alias_to_model(
            function_or_type, name, description, field_name
        )
    return response


def parse_as(
    type_: Any,
    data: Any,
    mode: Literal["python", "json", "strings"] = "python",
) -> BaseModel:
    """Parse a json string to a Pydantic model."""
    adapter = TypeAdapter(type_)

    if get_origin(type_) is list and isinstance(data, dict):
        data = next(iter(data.values()))

    parser = getattr(adapter, f"validate_{mode}")

    return parser(data)
