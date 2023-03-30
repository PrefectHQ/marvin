import json
import re
import warnings
from types import GenericAlias
from typing import Any, Literal

import pydantic
from pydantic import BaseModel, Field, PrivateAttr

import marvin
from marvin.utilities.types import (
    DiscriminatedUnionType,
    LoggerMixin,
    format_type_str,
    genericalias_contains,
    safe_issubclass,
)

SENTINEL = "__SENTINEL__"


class ResponseFormatter(DiscriminatedUnionType, LoggerMixin):
    format: str = Field(None, description="The format of the response")
    on_error: Literal["reformat", "raise", "ignore"] = "reformat"

    def validate_response(self, response):
        # by default, try to parse the response to validate it
        self.parse_response(response)

    def parse_response(self, response):
        return response


class JSONFormatter(ResponseFormatter):
    format: str = "A valid JSON string."

    def parse_response(self, response):
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError(f'Expected a valid JSON string, got "{response}"')


class BooleanFormatter(ResponseFormatter):
    format: str = (
        'Respond only with "true" or "false". Never say anything else or add'
        " any punctuation."
    )

    def validate_response(self, response):
        if response.lower() not in ["true", "false"]:
            raise ValueError(f"Expected either `true` or `false`, got `{response}`")

    def parse_response(self, response):
        return response.lower() == "true"


class TypeFormatter(ResponseFormatter):
    _cached_type: type | GenericAlias = PrivateAttr(SENTINEL)
    type_schema: dict[str, Any] = Field(
        ..., description="The OpenAPI schema for the type"
    )

    def __init__(self, type_: type = SENTINEL, **kwargs):
        if type_ is not SENTINEL:
            for key in ["format", "type_schema"]:
                if key in kwargs:
                    raise ValueError(f"Cannot specify `{key}` for TypeFormatter")
            if not isinstance(type_, (type, GenericAlias)):
                raise ValueError(f"Expected a type or GenericAlias, got {type_}")

            # warn if the type is a set or tuple with GPT 3.5
            if marvin.settings.openai_model_name.startswith("gpt-3.5"):
                if safe_issubclass(type_, (set, tuple)) or genericalias_contains(
                    type_, (set, tuple)
                ):
                    warnings.warn(
                        (
                            "GPT-3.5 often fails with `set` or `tuple` types. Consider"
                            " using `list` instead."
                        ),
                        UserWarning,
                    )

            schema = marvin.utilities.types.type_to_schema(type_)

            kwargs.update(
                type_schema=schema,
                format=(
                    "A valid JSON object that satisfies this OpenAPI schema:"
                    f" ```{json.dumps(schema)}```. The JSON object will be coerced to"
                    f" the following type signature: ```{format_type_str(type_)}```."
                    " Make sure your response is valid JSON, which means you must use"
                    " lists instead of tuples or sets; literal `true` and `false`"
                    " instead of `True` and `False`; literal `null` instead of `None`;"
                    " and double quotes instead of single quotes."
                ),
            )
        super().__init__(**kwargs)

        if type_ is not SENTINEL:
            self._cached_type = type_

    def get_type(self) -> type | GenericAlias:
        if self._cached_type is not SENTINEL:
            return self._cached_type

        model = marvin.utilities.types.schema_to_type(self.type_schema)
        type_ = model.__fields__["__root__"].outer_type_
        self._cached_type = type_
        return type_

    def parse_response(self, response):
        type_ = self.get_type()

        # handle GenericAlias and containers like dicts
        if isinstance(type_, GenericAlias) or safe_issubclass(
            type_, (list, dict, set, tuple)
        ):
            return pydantic.parse_raw_as(type_, response)

        # handle basic types
        else:
            return type_(response)


class PydanticFormatter(ResponseFormatter):
    # store the model as a private attribute so that we don't have to parse the
    # schema unless the formatter was deserialized
    _cached_model: type[pydantic.BaseModel] = PrivateAttr(SENTINEL)
    type_schema: dict[str, Any] = Field(
        ..., description="The OpenAPI schema for the model"
    )

    def __init__(self, model: BaseModel | GenericAlias = None, **kwargs):
        if model is not None:
            for key in ["format", "type_schema"]:
                if key in kwargs:
                    raise ValueError(f"Cannot specify `{key}` for PydanticFormatter")
            if not (
                safe_issubclass(model, pydantic.BaseModel)
                or genericalias_contains(model, pydantic.BaseModel)
            ):
                raise ValueError(
                    f"Expected a BaseModel or nested BaseModel, got {model}"
                )

            schema = marvin.utilities.types.type_to_schema(model)

            kwargs.update(
                type_schema=schema,
                format=(
                    "A JSON object that satisfies the following OpenAPI schema:"
                    f" ```{json.dumps(schema)}```"
                ),
            )

        super().__init__(**kwargs)

        if model is not None:
            self._cached_model = model

    def get_model(self) -> pydantic.BaseModel:
        if self._cached_model != SENTINEL:
            return self._cached_model
        model = marvin.utilities.types.schema_to_type(self.type_schema)
        self._cached_model = model
        return model

    def parse_response(self, response):
        return pydantic.parse_raw_as(self.get_model(), response)


def load_formatter_from_shorthand(shorthand_response_format) -> ResponseFormatter:
    match shorthand_response_format:
        # shorthand for None
        case None:
            return ResponseFormatter()

        # x is a ResponseFormatter - no shorthand
        case x if isinstance(x, ResponseFormatter):
            return x

        # x is a boolean
        case x if x is bool:
            return BooleanFormatter()

        # x is a string that contains the word "json"
        case x if isinstance(x, str) and re.search(r"\bjson\b", x.lower()):
            return JSONFormatter(format=x)

        # x is a string
        case x if isinstance(x, str):
            return ResponseFormatter(format=x)

        # x is a pydantic model
        case x if genericalias_contains(x, pydantic.BaseModel):
            return PydanticFormatter(model=x)

        # x is a type or GenericAlias
        case x if isinstance(x, (type, GenericAlias)):
            return TypeFormatter(type_=x)

        # unsupported values
        case _:
            raise ValueError("Invalid output format")
