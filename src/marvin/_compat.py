from types import FunctionType, GenericAlias
from typing import Any, Callable, Optional, TypeVar, Union, cast

from fastapi._compat import PYDANTIC_V2, lenient_issubclass
from pydantic import create_model

from .types import RESPONSE_MODEL

if PYDANTIC_V2:
    from pydantic import Field, ImportString, SecretStr
    from pydantic.v1 import (
        BaseModel,  # noqa
        root_validator,
        validate_arguments,
        validator,
    )
    from pydantic.v1 import Field as V1Field
    from pydantic_settings import BaseSettings

else:
    from pydantic import (
        BaseModel,
        BaseSettings,
        Field,
        SecretStr,
        root_validator,
        validate_arguments,  # type: ignore[no-redef]
        validator,
    )
    from pydantic import Field as V1Field
    from pydantic import PyObject as ImportString

_ModelT = TypeVar("_ModelT", bound="BaseModel")


def get_base_model() -> type[_ModelT]:
    if PYDANTIC_V2:
        from pydantic.v1 import BaseModel

        return BaseModel
    else:
        from pydantic import BaseModel
    return BaseModel  # type: ignore


def model_copy(model: _ModelT) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_copy()
    return model.copy()  # type: ignore


def model_dump(model: _ModelT, **kwargs: Any) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)  # type: ignore


def model_fields(model: type[_ModelT]) -> dict[str, Any]:
    if PYDANTIC_V2:
        return model.model_fields
    return model.__fields__  # type: ignore


def model_schema(model: type[_ModelT]) -> dict[str, Any]:
    if PYDANTIC_V2 and hasattr(model, "model_json_schema"):
        return model.model_json_schema()
    return model.schema()  # type: ignore


def model_json_schema(
    model: type[_ModelT],
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


def cast_callable_to_model(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> type[_ModelT]:
    response = validate_arguments(function).model  # type: ignore
    for field in ["args", "kwargs", "v__duplicate_kwargs"]:
        fields = cast(dict[str, Any], response.__fields__)  # type: ignore
        fields.pop(field, None)
    response.__title__ = name or function.__name__
    response.__doc__ = description or function.__doc__
    return response  # type: ignore


def cast_type_to_model(
    type_: type,
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> type[_ModelT]:
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
    model: Union[type, GenericAlias, type[_ModelT], Callable[..., Any]],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> type[_ModelT]:
    if isinstance(model, FunctionType):
        response = cast_callable_to_model(model, name, description)
    elif isinstance(model, type) and lenient_issubclass(model, BaseModel):
        response = model
    elif isinstance(model, type) or isinstance(model, GenericAlias):
        response = cast_type_to_model(model, name, description)
    else:
        response = cast_callable_to_model(model, name, description)
    if name:
        response.__name__ = name
    if description:
        response.__doc__ = description
    return response


def cast_to_json(
    model: RESPONSE_MODEL,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    return model_json_schema(cast_to_model(model, name, description))


__all__ = [
    "BaseSettings",
    "SecretStr",
    "Field",
    "BaseModel",
    "V1Field",
    "model_copy",
    "model_dump",
    "root_validator",
    "validator",
    "ImportString",
    "cast_to_model",
]
