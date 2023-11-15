from enum import Enum
from types import GenericAlias
from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode

from marvin import settings
from marvin.requests import Function, LogitBias, Tool, Grammar

U = TypeVar("U", bound=BaseModel)


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
    annotated_metadata = getattr(_type, "__metadata__", [])
    if isinstance(next(iter(annotated_metadata), None), FieldInfo):
        metadata = next(iter(annotated_metadata))
    else:
        metadata = FieldInfo(description=field_description)

    model: type[BaseModel] = create_model(
        model_name,
        __config__=None,
        __base__=None,
        __module__=__name__,
        __validators__=None,
        __cls_kwargs__=None,
        **{field_name: (_type, metadata)},
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


def create_vocabulary_from_type(
    vocabulary: Union[GenericAlias, type, list[str]],
) -> list[str]:
    if get_origin(vocabulary) == Literal:
        return [str(token) for token in get_args(vocabulary)]
    elif isinstance(vocabulary, type) and issubclass(vocabulary, Enum):
        return [str(token) for token in list(vocabulary.__members__.keys())]
    elif isinstance(vocabulary, list) and next(iter(get_args(list[str])), None) == str:
        return [str(token) for token in vocabulary]
    else:
        raise TypeError(
            f"Expected Literal or Enum or list[str], got {type(vocabulary)} with value"
            f" {vocabulary}"
        )


def create_grammar_from_vocabulary(
    vocabulary: list[str],
    encoder: Callable[[str], list[int]] = settings.openai.chat.completions.encoder,
    max_tokens: Optional[int] = None,
    _enumerate: bool = True,
    **kwargs: Any,
) -> Grammar:
    return Grammar(
        max_tokens=max_tokens,
        logit_bias={
            str(encoding): 100
            for i, token in enumerate(vocabulary)
            for encoding in encoder(str(i) if _enumerate else token)
        },
    )
