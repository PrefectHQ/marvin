from enum import Enum
from types import GenericAlias
from typing import Any, Callable, Literal, Union, get_args, get_origin

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode

from marvin import settings
from marvin.requests import Function, LogitBias, Tool


class FunctionSchema(GenerateJsonSchema):
    def generate(self, schema: Any, mode: JsonSchemaMode = "validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop("title", None)
        return json_schema


def create_tool_from_type(
    _type: Union[type, GenericAlias],
    model_name: str,
    model_description: str,
    field_name: str,
    field_description: str,
    **kwargs: Any,
) -> Tool[BaseModel]:
    model: type[BaseModel] = create_model(
        model_name,
        __config__=None,
        __base__=None,
        __module__=__name__,
        __validators__=None,
        __cls_kwargs__=None,
        **{field_name: (_type, FieldInfo(description=field_description))},
    )
    return Tool[BaseModel](
        type="function",
        function=Function[BaseModel](
            name=model_name,
            description=model_description,
            parameters=model.model_json_schema(schema_generator=FunctionSchema),
            model=model,
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
