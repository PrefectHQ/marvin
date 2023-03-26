import json
import re
from types import GenericAlias
from typing import Any, Literal

import pydantic
from pydantic import BaseModel, Field, PrivateAttr

import marvin
from marvin.utilities.types import (
    DiscriminatingTypeModel,
    safe_issubclass,
)

SENTINEL = "__SENTINEL__"


class ResponseFormatter(DiscriminatingTypeModel):
    format: str = Field(None, description="The format of the response")
    on_error: Literal["reformat", "raise", "ignore"] = "ignore"

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

            schema = marvin.utilities.types.type_to_schema(type_)
            kwargs.update(
                type_schema=schema,
                format=f"You must match the following type signature: `{type_}`",
            )
        super().__init__(**kwargs)
        if type_ is not SENTINEL:
            self._cached_type = type_

    def get_type(self) -> type | GenericAlias | pydantic.BaseModel:
        if self._cached_type is not SENTINEL:
            return self._cached_type

        model = marvin.utilities.types.schema_to_type(self.type_schema)
        type_ = model.__fields__["__root__"].outer_type_
        self._cached_type = type_
        return type_

    def parse_response(self, response):
        return pydantic.parse_raw_as(self.get_type(), response)


class PydanticFormatter(ResponseFormatter):
    # store the model as a private attribute so that we don't have to parse the
    # schema unless the formatter was deserialized
    _cached_model: type[pydantic.BaseModel] = PrivateAttr(SENTINEL)
    type_schema: dict[str, Any] = Field(
        ..., description="The OpenAPI schema for the model"
    )

    def __init__(self, model: BaseModel = None, **kwargs):
        if model is not None:
            for key in ["format", "type_schema"]:
                if key in kwargs:
                    raise ValueError(f"Cannot specify `{key}` for PydanticFormatter")
            if not safe_issubclass(model, pydantic.BaseModel):
                raise ValueError(f"Expected a BaseModel, got {model}")

            schema = marvin.utilities.types.type_to_schema(model)

            kwargs.update(
                type_schema=schema,
                format=(
                    "A JSON object that matches the following OpenAPI schema:"
                    f" ```{json.dumps(schema)}```"
                ),
            )
            self._cached_model = model
        super().__init__(**kwargs)

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
        case x if isinstance(x, str) and re.search("\bjson\b", x.lower()):
            return JSONFormatter(format=x)

        # x is a string
        case x if isinstance(x, str):
            return ResponseFormatter(format=x)

        # x is a pydantic model
        case x if safe_issubclass(x, pydantic.BaseModel):
            return PydanticFormatter(model=x)

        # x is a type or GenericAlias
        case x if isinstance(x, (type, GenericAlias)):
            return TypeFormatter(type_=x)

        # unsupported values
        case _:
            raise ValueError("Invalid output format")
