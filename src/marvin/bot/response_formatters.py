import json
import re
import warnings
from types import GenericAlias
from typing import Any, Literal, Union

import pydantic
from dateutil.rrule import rrulestr
from pydantic import BaseModel, Field, PrivateAttr

import marvin
from marvin.utilities.strings import condense_newlines
from marvin.utilities.types import (
    DiscriminatedUnionType,
    LoggerMixin,
    format_type_str,
    genericalias_contains,
    safe_issubclass,
)

SENTINEL = "__SENTINEL__"
MAX_VALIDATION_ATTEMPTS = 3


class ResponseFormatter(DiscriminatedUnionType, LoggerMixin):
    format: str = Field(None, description="The format of the response")
    on_error: Literal["reformat", "raise", "ignore"] = "reformat"

    def validate_response(self, response: str):
        # by default, try to parse the response to validate it
        self.parse_response(response)

    def parse_response(self, response: str) -> str:
        return response

    async def run(self, llm_response: str):
        """
        Parses the response from the LLM into the required format, applying
        error correction if neccessary. Leverages `validate_response` and
        `parse_response`.
        """

        parsed_response = llm_response
        validated = False

        for _ in range(MAX_VALIDATION_ATTEMPTS):
            try:
                self.validate_response(llm_response)
                validated = True
                break
            except Exception as exc:
                if self.on_error == "ignore":
                    break
                elif self.on_error == "raise":
                    raise exc
                elif self.on_error == "reformat":
                    self.logger.debug_kv(
                        "Response did not pass validation. Attempted to reformat",
                        f" {llm_response}",
                        key_style="red",
                    )
                    llm_response = reformat_response_fn(
                        llm_response=llm_response,
                        error_message=repr(exc),
                        target_return_type=self.format,
                    )
                else:
                    raise ValueError(f"Unknown on_error value: {self.on_error}")
        else:
            llm_response = (
                "Error: could not validate response after"
                f" {MAX_VALIDATION_ATTEMPTS} attempts."
            )
            parsed_response = llm_response

        if validated:
            parsed_response = self.parse_response(llm_response)

        return parsed_response


class StringFormatter(ResponseFormatter):
    format: str = (
        "The response will be parsed as a string. Do not add unecessary surrounding"
        " quotes."
    )


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
    _cached_type: Union[type, GenericAlias] = PrivateAttr(SENTINEL)
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
            if marvin.settings.llm_model.startswith("gpt-3.5"):
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

            # for all but the simplest containers, include an OpenAPI schema
            # this can confuse the LLM (esp 3.5) if included for very simple signatures
            schema_placeholder = ""
            if isinstance(type_, GenericAlias):
                if any(a not in (str, int, float, bool) for a in type_.__args__):
                    schema_placeholder = (
                        "It must also comply with this OpenAPI schema:"
                        f" ```{json.dumps(schema)}```. "
                    )

            kwargs.update(
                type_schema=schema,
                format=(
                    "A valid JSON object that is compatible with the following type"
                    f" signature: ```{format_type_str(type_)}```."
                    f" {schema_placeholder}\n\nYour response MUST be valid JSON or a"
                    " JSON-compatible scalar (such as str, int, float, bool, or null)."
                    " Use lists instead of literal tuples or sets; literal `true` and"
                    " `false` instead of `True` and `False`; literal `null` instead of"
                    " `None`; and double quotes instead of single quotes."
                ),
            )
        super().__init__(**kwargs)

        if type_ is not SENTINEL:
            self._cached_type = type_

    def get_type(self) -> Union[type, GenericAlias]:
        if self._cached_type is not SENTINEL:
            return self._cached_type

        model = marvin.utilities.types.schema_to_type(self.type_schema)
        type_ = model.__fields__["__root__"].outer_type_
        self._cached_type = type_
        return type_

    def parse_response(self, response):
        type_ = self.get_type()
        try:
            if type_ is str:
                return str(json.loads(response))
            return pydantic.parse_raw_as(type_, response)
        except Exception as exc:
            # if an error should be raised, make it highly informative
            if self.on_error == "raise":
                raise ValueError(
                    f"Could not parse response as type. Response: '{response}'. Type:"
                    f" '{type_}'. Format: '{self.format}'. Error from parsing:"
                    f" '{repr(exc)}'"
                )
            else:
                raise


class PydanticFormatter(ResponseFormatter):
    # store the model as a private attribute so that we don't have to parse the
    # schema unless the formatter was deserialized
    _cached_model: type[pydantic.BaseModel] = PrivateAttr(SENTINEL)
    type_schema: dict[str, Any] = Field(
        ..., description="The OpenAPI schema for the model"
    )

    def __init__(self, model: Union[BaseModel, GenericAlias] = None, **kwargs):
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


class RRuleFormatter(ResponseFormatter):
    format: str = condense_newlines("""    
        A valid RRULE (RFC 5545) string that can be parsed by
        dateutil.rrule.rrulestr(). Each property (RRULE, DTSTART, EXDATE, etc.)
        should be on a new line, and parameters (FREQ, BYHOUR, INTERVAL, etc.)
        should be separated by semicolons. Round off hours/minutes/seconds to 0
        if not specified.
        
        The result must be a string delimited by optional newlines, not a JSON object.
        """)

    def validate_response(self, response: str):
        rrulestr(response)


def load_formatter_from_shorthand(shorthand_response_format) -> ResponseFormatter:
    if shorthand_response_format is None:
        return ResponseFormatter()
    elif isinstance(shorthand_response_format, ResponseFormatter):
        return shorthand_response_format
    elif shorthand_response_format is str:
        return StringFormatter()
    elif shorthand_response_format is bool:
        return BooleanFormatter()
    elif isinstance(shorthand_response_format, str):
        if re.search(r"\bjson\b", shorthand_response_format.lower()):
            return JSONFormatter(format=shorthand_response_format)
        else:
            return ResponseFormatter(
                format=(
                    "A response that complies with the instruction"
                    f" '{shorthand_response_format}', and nothing else."
                )
            )
    elif genericalias_contains(shorthand_response_format, pydantic.BaseModel):
        return PydanticFormatter(model=shorthand_response_format)
    elif isinstance(shorthand_response_format, (type, GenericAlias)):
        return TypeFormatter(type_=shorthand_response_format)
    else:
        raise ValueError("Invalid output format")


def reformat_response_fn(
    llm_response: str,
    target_return_type: Any,
    error_message: str,
) -> str:
    @marvin.ai_fn(
        plugins=[],
        response_format=JSONFormatter(on_error="ignore"),
        llm_model=marvin.settings.llm_model_for_response_format,
        llm_temperature=0,
    )
    def reformat_response(
        llm_response: str,
        target_return_type: str,
        error_message: str,
    ) -> str:
        """
        An error (`error_message`) was raised when attempting to parse
        `llm_response` into `target_return_type`.

        Convert `llm_response` into a valid JSON string compatible with
        `target_return_type`.
        """

    reformatted_response = reformat_response(
        llm_response=llm_response,
        target_return_type=target_return_type,
        error_message=error_message,
    )
    if not isinstance(reformatted_response, str):
        reformatted_response = json.dumps(reformatted_response)
    return reformatted_response
