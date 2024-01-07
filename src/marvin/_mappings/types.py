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
    type_: Union[type, GenericAlias],
) -> list[str]:
    if get_origin(type_) == Literal:
        return [str(token) for token in get_args(type_)]
    elif isinstance(type_, type) and issubclass(type_, Enum):
        members: list[str] = [
            option.value for option in getattr(type_, "__members__", {}).values()
        ]
        return members
    elif isinstance(type_, list):
        return [str(token) for token in type_]
    else:
        raise TypeError(f"Expected Literal, Enum, or list, got {type_}.")


def cast_options_to_grammar(
    options: list[str],
    encoder: Callable[[str], list[int]] = None,
    max_tokens: Optional[int] = None,
    enumerate_: bool = True,
    **kwargs: Any,
) -> Grammar:
    if encoder is None:
        encoder = settings.openai.llms.encoder
    return Grammar(
        max_tokens=max_tokens,
        logit_bias={
            str(encoding): 100
            for i, token in enumerate(options)
            for encoding in encoder(str(i) if enumerate_ else token)
        },
    )


def cast_type_to_grammar(
    type_: Union[type, GenericAlias],
    encoder: Callable[[str], list[int]] = settings.openai.llms.encoder,
    max_tokens: Optional[int] = None,
    enumerate_: bool = True,
    **kwargs: Any,
) -> Grammar:
    return cast_options_to_grammar(
        options=cast_type_to_options(type_),
        encoder=encoder,
        max_tokens=max_tokens,
        enumerate_=enumerate_,
        **kwargs,
    )
