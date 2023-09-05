import warnings
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    Literal,
    Optional,
)

from pydantic import BaseModel, validate_arguments
from pydantic.decorator import (
    ALT_V_ARGS,
    ALT_V_KWARGS,
    V_DUPLICATE_KWARGS,
    V_POSITIONAL_ONLY_NAME,
)

from .messages import Message


def cast_to_model(
    model: type[BaseModel] | Callable[..., Any],
) -> type[BaseModel]:
    if isinstance(model, type):
        return model
    else:
        return validate_arguments(model).model  # type: ignore


def json_schema(
    model: type[BaseModel] | Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    openapi_schema = cast_to_model(model).schema()

    json_schema: dict[str, Any] = {}
    json_schema["name"] = name or model.__name__
    json_schema["description"] = description or model.__doc__
    json_schema["parameters"] = {
        key: value
        for (key, value) in openapi_schema.items()
        if key not in {"title", "description"}
    }
    json_schema["properties"] = {
        key: value
        for (key, value) in openapi_schema["properties"].items()
        if key
        not in [
            "args",
            "kwargs",
            ALT_V_ARGS,
            ALT_V_KWARGS,
            V_POSITIONAL_ONLY_NAME,
            V_DUPLICATE_KWARGS,
        ]
    }
    return json_schema


class AbstractResponseParser(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, **kwargs: Any) -> dict[str, Any]:
        pass


class AbstractRequestSerializer(ABC):
    """
    Abstract class for serializing payloads to send to an LLM.

    The serialize method takes in a ∏list of messages, a list of functions,
    a response model, and a function call.
    """

    @staticmethod
    def serialize_messages(messages: list[Message]) -> list[dict[str, Any]]:
        return [
            {"content": None, **message.dict(exclude_none=True)} for message in messages
        ]  # noqa

    @staticmethod
    def serialize_functions(
        functions: list[Callable[..., Any] | Dict[str, Any] | type[BaseModel]]
    ) -> list[Dict[str, Any]]:
        response: list[Dict[str, Any]] = []
        for function in functions:
            if isinstance(function, dict):
                response.append(function)
            else:
                response.append(json_schema(function))

        return response

    @staticmethod
    def serialize_response_model(response_model: type[BaseModel]) -> Dict[str, Any]:
        """Abstract method for serializing function_call."""
        schema = {**response_model.schema()}
        json_schema: Dict[str, Any] = {}
        json_schema["name"] = schema.pop("title")
        json_schema["description"] = schema.pop(
            "description", f"""Base {json_schema['name']} model"""
        )  # noqa
        json_schema["parameters"] = schema
        return json_schema

    @staticmethod
    def serialize_function_call(
        function_call: Optional[Literal["auto"] | Dict[Literal["name"], str]]
    ) -> Optional[Literal["auto"] | Dict[Literal["name"], str]]:
        return function_call

    def to_dict(
        self,
        /,
        *,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        ] = None,  # noqa
        function_call: Optional[
            Literal["auto"] | Dict[Literal["name"], str]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        serialized_request: dict[str, Any] = {}
        if messages:
            serialized_request["messages"] = self.serialize_messages(messages)

        if response_model:
            if functions:
                warnings.warn(
                    "Providing both a response_model and functions is partially supported: "  # noqa
                    "we will use the response_model to generate the function_call, "  # noqa
                )
                serialized_request["functions"] = self.serialize_functions(functions)
            else:
                serialized_request["functions"] = []
            serialized_request["functions"] += [
                self.serialize_response_model(response_model)
            ]
            serialized_request["function_call"] = {
                "name": serialized_request["functions"][0]["name"]
            }

        elif functions:
            serialized_request["functions"] = self.serialize_functions(functions)

            if function_call:
                serialized_request["function_call"] = self.serialize_function_call(
                    function_call
                )

        return {**kwargs, **serialized_request}
