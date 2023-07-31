import warnings
from types import GenericAlias
from typing import Any, Union

import pydantic
from pydantic import BaseModel, Field, PrivateAttr

import marvin
import marvin.utilities.types
from marvin.tools import Tool
from marvin.utilities.types import (
    genericalias_contains,
    safe_issubclass,
)

SENTINEL = "__SENTINEL__"


class FormatResponse(Tool):
    _cached_type: Union[type, GenericAlias] = PrivateAttr(SENTINEL)
    type_schema: dict[str, Any] = Field(
        ..., description="The OpenAPI schema for the type"
    )
    description: str = (
        "You MUST always call this function before responding to the user to ensure"
        " that your final response is formatted correctly and complies with the output"
        " format requirements."
    )

    def __init__(self, type_: Union[type, GenericAlias] = SENTINEL, **kwargs):
        if type_ is not SENTINEL:
            if not isinstance(type_, (type, GenericAlias)):
                raise ValueError(f"Expected a type or GenericAlias, got {type_}")

            # warn if the type is a set or tuple with GPT 3.5
            if (
                "gpt-3.5" in marvin.settings.llm_model
                or "gpt-35" in marvin.settings.llm_model
            ):
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

            type_schema = marvin.utilities.types.type_to_schema(
                type_, set_root_type=False
            )
            type_schema.pop("title", None)
            kwargs["type_schema"] = type_schema

        super().__init__(**kwargs)
        if type_ is not SENTINEL:
            if type_schema.get("description"):
                self.description += f"\n\n {type_schema['description']}"

        if type_ is not SENTINEL:
            self._cached_type = type_

    def get_type(self) -> Union[type, GenericAlias]:
        if self._cached_type is not SENTINEL:
            return self._cached_type
        model = marvin.utilities.types.schema_to_type(self.type_schema)
        type_ = model.__fields__["__root__"].outer_type_
        self._cached_type = type_
        return type_

    def run(self, **kwargs) -> Any:
        type_ = self.get_type()
        if not safe_issubclass(type_, BaseModel):
            kwargs = kwargs["data"]
        return pydantic.parse_obj_as(type_, kwargs)

    def argument_schema(self) -> dict:
        return self.type_schema
