from types import FunctionType, GenericAlias
from typing import Any, Callable, Optional, TypeVar, Union, cast

from pydantic import BaseModel, create_model
from pydantic.version import VERSION as PYDANTIC_VERSION

_ModelT = TypeVar("_ModelT", bound="BaseModel")

PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2.")

if PYDANTIC_V2:
    from pydantic.v1 import validate_arguments  # noqa # type: ignore
    from pydantic_settings import BaseSettings  # noqa # type: ignore
    from pydantic_settings import SettingsConfigDict  # noqa # type: ignore
    from pydantic import field_validator  # noqa # type: ignore

else:
    from pydantic import BaseSettings, validate_arguments  # noqa # type: ignore
    from pydantic import validator as field_validator  # noqa # type: ignore

    SettingsConfigDict = BaseSettings.Config


def model_dump(model: BaseModel, **kwargs: Any) -> dict[str, Any]:
    if PYDANTIC_V2 and hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)  # type: ignore
    return model.dict(**kwargs)  # type: ignore


def model_dump_json(model: type[BaseModel], **kwargs: Any) -> dict[str, Any]:
    if PYDANTIC_V2 and hasattr(model, "model_dump_json"):
        return model.model_dump_json(**kwargs)  # type: ignore
    return model.json(**kwargs)  # type: ignore


def model_json_schema(
    model: type[BaseModel],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    # Get the schema from the model.
    schema = {"parameters": {**model_schema(model)}}

    # Mutate the schema to match the OpenAPI spec.
    schema["parameters"]["title"] = name or schema["parameters"].pop("title")
    schema["parameters"]["description"] = description or schema["parameters"].pop(
        "description", ""
    )  # noqa

    # Move the properties to the root of the schema.
    schema["name"] = schema["parameters"].pop("title")
    schema["description"] = schema["parameters"].pop("description")
    return schema


def model_schema(model: type[BaseModel], **kwargs: Any) -> dict[str, Any]:
    if PYDANTIC_V2 and hasattr(model, "model_json_schema"):
        return model.model_json_schema(**kwargs)  # type: ignore
    return model.schema(**kwargs)  # type: ignore


def cast_callable_to_model(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> type[BaseModel]:
    response = validate_arguments(function).model  # type: ignore
    for field in ["args", "kwargs", "v__duplicate_kwargs"]:
        fields = cast(dict[str, Any], response.__fields__)  # type: ignore
        fields.pop(field, None)
    response.__title__ = name or function.__name__
    response.__doc__ = description or function.__doc__
    return response  # type: ignore


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
    response = BaseModel
    if isinstance(function_or_type, GenericAlias):
        response = cast_type_or_alias_to_model(
            function_or_type, name, description, field_name
        )
    elif isinstance(function_or_type, type):
        if issubclass(function_or_type, BaseModel):
            response = function_or_type
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


def cast_to_json(
    function_or_type: Union[type, type[BaseModel], GenericAlias, Callable[..., Any]],
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> dict[str, Any]:
    return model_json_schema(
        cast_to_model(function_or_type, name, description, field_name)
    )
