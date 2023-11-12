from enum import Enum
from types import GenericAlias
from typing import Any, Callable, Literal, Union, get_args, get_origin

from pydantic import create_model
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode

from marvin import settings
from marvin.requests import Function, LogitBias, Tool


class FunctionSchema(GenerateJsonSchema):
    def generate(self, schema: Any, mode: JsonSchemaMode = "validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop("title", None)
        return json_schema


def create_tool(
    _type: Union[type, GenericAlias],
    name: str = "A",
    description: str = "B",
    field_name: str = "C",
    **kwargs: Any,
) -> Tool:
    return Tool(
        type="function",
        function=Function(
            name=name,
            description=description,
            parameters=create_model(
                name, **{field_name: (_type, ...)}  # type: ignore
            ).model_json_schema(schema_generator=FunctionSchema),
        ),
    )


def to_logit_bias(
    _type: Union[GenericAlias, type, list[str]],
    encoder: Callable[..., list[int]] = settings.openai.chat.completions.encoder,
    _enumerate: bool = True,
    **kwargs: Any,
) -> LogitBias:
    if get_origin(_type) == Literal:
        return {
            encoding: 100
            for i, token in enumerate(get_args(_type))
            for encoding in encoder(str(i) if _enumerate else token)
        }
    elif isinstance(_type, type) and issubclass(_type, Enum):
        return {
            encoding: 100
            for i, token in enumerate(list(_type.__members__.keys()))
            for encoding in encoder(str(i) if _enumerate else token)
        }
    elif isinstance(_type, list) and next(iter(get_args(list[str])), None) == str:
        return {
            encoding: 100
            for i, token in enumerate(_type)
            for encoding in encoder(str(i) if _enumerate else token)
        }
    else:
        raise TypeError(
            f"Expected Literal or Enum or list[str], got {type(_type)} with value"
            f" {_type}"
        )
