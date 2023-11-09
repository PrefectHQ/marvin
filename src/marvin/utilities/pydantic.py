from types import FunctionType, GenericAlias
from typing import (
    Annotated,
    Any,
    Callable,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_origin,
)

from pydantic import BaseModel, Field, TypeAdapter, create_model
from pydantic.v1 import validate_arguments
from typing_extensions import Literal

T = TypeVar("T")


def make_arbitrary_dict_model(name: str) -> Type[BaseModel]:
    class ArbitraryDictModel(BaseModel):
        output: dict = Field(
            description=(
                "This is a placeholder indicating that the model"
                " expects a dictionary with arbitrary keys and values"
                " based on the context of its use."
            ),
            example={"key1": "value1", "key2": "value2"},
        )

    ArbitraryDictModel.__name__ = name
    return ArbitraryDictModel


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

    elif origin is dict:
        response = make_arbitrary_dict_model(name or "Output")

    elif origin in {list, tuple, set, frozenset}:
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


ValidationMode = Literal["python", "json", "strings"]


def parse_as(
    model_: Any,
    data: dict[str, Any],
    mode: ValidationMode = "python",
    output_field_name: str = "output",
) -> T:
    """Parse data to a target type.

    Args:
        type_: The target type to parse to.
        data: The data to parse.
        mode: The mode to parse as. Defaults to "python".
        output_field_name: The name of the output field. Defaults to "output".
    """
    if mode not in (modes := ValidationMode.__args__):
        raise ValueError(f"Invalid mode: {mode!r}. Must be one of: {' | '.join(modes)}")

    adapter = TypeAdapter(model_)

    validated_model = getattr(adapter, f"validate_{mode}")(data, strict=False)

    return getattr(validated_model, output_field_name)
