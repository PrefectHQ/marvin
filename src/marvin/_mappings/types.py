from enum import Enum
from types import GenericAlias
from typing import Any, Callable, Literal, Optional, Union, get_args, get_origin

from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from marvin.requests import Grammar, Tool, ToolSet
from marvin.settings import settings

from .base_model import cast_model_to_tool, cast_model_to_toolset


def cast_type_to_model(
    _type: Union[type, GenericAlias],
    model_name: str,
    model_description: str,
    field_name: str,
    field_description: str,
) -> type[BaseModel]:
    annotated_metadata = getattr(_type, "__metadata__", [])
    if isinstance(next(iter(annotated_metadata), None), FieldInfo):
        metadata = next(iter(annotated_metadata))
    else:
        metadata = FieldInfo(description=field_description)

    if _type is None:
        raise ValueError("No type provided; unable to create model for casting.")

    return create_model(
        model_name,
        __doc__=model_description,
        __config__=None,
        __base__=None,
        __module__=__name__,
        __validators__=None,
        __cls_kwargs__=None,
        **{field_name: (_type, metadata)},
    )


def cast_type_to_tool(
    _type: Union[type, GenericAlias],
    model_name: str,
    model_description: str,
    field_name: str,
    field_description: str,
    python_function: Optional[Callable[..., Any]] = None,
) -> Tool[BaseModel]:
    return cast_model_to_tool(
        model=cast_type_to_model(
            _type,
            model_name,
            model_description,
            field_name,
            field_description,
        )
    )


def cast_type_to_toolset(
    _type: Union[type, GenericAlias],
    model_name: str,
    model_description: str,
    field_name: str,
    field_description: str,
    python_function: Optional[Callable[..., Any]] = None,
    **kwargs: Any,
) -> ToolSet[BaseModel]:
    return cast_model_to_toolset(
        model=cast_type_to_model(
            _type,
            model_name,
            model_description,
            field_name,
            field_description,
        ),
        **kwargs,
    )


def cast_type_to_options(
    _type: Union[type, GenericAlias],
) -> list[str]:
    if get_origin(_type) == Literal:
        return [str(token) for token in get_args(_type)]
    elif isinstance(_type, type) and issubclass(_type, Enum):
        members: list[str] = [
            option.value for option in getattr(_type, "__members__", {}).values()
        ]
        return members
    else:
        raise TypeError(f"Expected Literal or Enum, got {_type}.")


def cast_options_to_grammar(
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


def cast_type_to_grammar(
    _type: Union[type, GenericAlias],
    encoder: Callable[[str], list[int]] = settings.openai.chat.completions.encoder,
    max_tokens: Optional[int] = None,
    _enumerate: bool = True,
    **kwargs: Any,
) -> Grammar:
    return cast_options_to_grammar(
        vocabulary=cast_type_to_options(_type),
        encoder=encoder,
        max_tokens=max_tokens,
        _enumerate=_enumerate,
        **kwargs,
    )
