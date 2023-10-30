from types import FunctionType, GenericAlias
from typing import (
    Annotated,
    Any,
    Callable,
    Optional,
    TypeVar,
    Union,
    cast,
    get_origin,
)

from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2.")

if PYDANTIC_V2:
    from pydantic.v1 import (
        BaseSettings,
        PrivateAttr,
        SecretStr,
        validate_arguments,
    )

    SettingsConfigDict = BaseSettings.Config

    from pydantic import (
        BaseModel,
        Field,
        create_model,
        field_validator,
    )

else:
    from pydantic import (  # noqa # type: ignore
        BaseSettings,
        BaseModel,
        create_model,
        Field,
        SecretStr,
        validate_arguments,
        validator as field_validator,
        PrivateAttr,
    )

    SettingsConfigDict = BaseSettings.Config

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def model_dump(model: _ModelT, **kwargs: Any) -> dict[str, Any]:
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
    schema["parameters"]["title"] = name or schema["parameters"].pop("title", None)
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


def model_copy(model: _ModelT, **kwargs: Any) -> _ModelT:
    if PYDANTIC_V2 and hasattr(model, "model_copy"):
        return model.model_copy(**kwargs)  # type: ignore
    return model.copy(**kwargs)  # type: ignore


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
    response.__name__ = name or function.__name__
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
    origin = get_origin(function_or_type) or function_or_type

    response = BaseModel
    if origin is Annotated:
        metadata: Any = next(iter(function_or_type.__metadata__), None)  # type: ignore
        annotated_field_name: Optional[str] = field_name

        if hasattr(metadata, "extra") and isinstance(metadata.extra, dict):
            annotated_field_name: Optional[str] = metadata.extra.get("name", "")  # type: ignore # noqa
        elif hasattr(metadata, "json_schema_extra") and isinstance(
            metadata.json_schema_extra, dict
        ):  # noqa
            annotated_field_name: Optional[str] = metadata.json_schema_extra.get("name", "")  # type: ignore # noqa
        elif isinstance(metadata, dict):
            annotated_field_name: Optional[str] = metadata.get("name", "")  # type: ignore # noqa
        elif isinstance(metadata, str):
            annotated_field_name: Optional[str] = metadata
        else:
            pass
        annotated_field_description: Optional[str] = description or ""
        if hasattr(metadata, "description") and isinstance(metadata.description, str):
            annotated_field_description: Optional[str] = metadata.description  # type: ignore # noqa
        elif isinstance(metadata, dict):
            annotated_field_description: Optional[str] = metadata.get("description", "")  # type: ignore # noqa
        else:
            pass

        response = cast_to_model(
            function_or_type.__origin__,  # type: ignore
            name=name,
            description=annotated_field_description,
            field_name=annotated_field_name,  # type: ignore
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


def cast_to_json(
    function_or_type: Union[type, type[BaseModel], GenericAlias, Callable[..., Any]],
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> dict[str, Any]:
    return model_json_schema(
        cast_to_model(function_or_type, name, description, field_name)
    )
