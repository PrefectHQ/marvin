from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Literal, Optional

from .pydantic import BaseModel, Field, validate_arguments


class AbstractRequestSerializer(ABC):
    """
    Abstract class for serializing payloads to send to an LLM.

    The serialize method takes in a list of messages, a list of functions,
    a response model, and a function call.
    """

    @staticmethod
    @abstractmethod
    def serialize_messages(messages: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Abstract method for serializing messages."""
        pass

    @staticmethod
    @abstractmethod
    def serialize_functions(
        functions: list[Callable[..., Any] | Dict[str, Any] | BaseModel]
    ) -> list[Dict[str, Any]]:
        """Abstract method for serializing functions."""
        pass

    @staticmethod
    def serialize_response_model(response_model: BaseModel) -> Dict[str, Any]:
        """Abstract method for serializing function_call."""
        schema = {**response_model.schema()}
        json_schema: Dict[str, Any] = {}
        json_schema["name"] = schema.pop("title")
        json_schema["description"] = schema.pop("description", None)
        json_schema["parameters"] = schema
        return json_schema

    @staticmethod
    @abstractmethod
    def serialize_function_call(
        function_call: Optional[Literal["auto"] | Dict[Literal["name"], str]]
    ) -> Optional[Literal["auto"] | Dict[Literal["name"], str]]:
        """Abstract method for serializing function_call."""
        pass

    def to_dict(
        self,
        /,
        *,
        messages: Optional[list[Dict[str, Any]]] = None,
        functions: Optional[
            list[Callable[..., Any] | Dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Literal["auto"] | Dict[Literal["name"], str]
        ] = None,  # noqa
        response_model: Optional[BaseModel] = None,
    ) -> dict[str, Any]:
        serialized_request: dict[str, Any] = {}
        if messages:
            serialized_request["messages"] = self.serialize_messages(messages)

        if response_model:
            serialized_request["functions"] = [
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

        return serialized_request


class OpenAISerializer(AbstractRequestSerializer):
    @staticmethod
    def serialize_messages(messages: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Abstract method for serializing messages."""
        return messages

    @staticmethod
    def serialize_functions(
        functions: list[Callable[..., Any] | Dict[str, Any] | BaseModel]
    ) -> list[Dict[str, Any]]:
        """Abstract method for serializing functions."""
        response: list[Dict[str, Any]] = []
        for function in functions:
            if isinstance(function, dict):
                response.append(function)
            elif isinstance(function, BaseModel):
                response.append(function.schema())
            else:
                model: BaseModel = validate_arguments(function).model  # type: ignore
                response.append(model.schema())
        return response

    @staticmethod
    def serialize_function_call(
        function_call: Optional[Literal["auto"] | Dict[Literal["name"], str]]
    ) -> Optional[Literal["auto"] | Dict[Literal["name"], str]]:
        """Abstract method for serializing function_call."""
        return function_call


class Request(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)
    functions: list[Callable[..., Any]] = Field(default_factory=list)
    function_call: Optional[Literal["auto"] | dict[str, str]] = None
    response_model: Optional[type[BaseModel]] = None
    retries: int = Field(default=0, ge=0)

    def __enter__(self) -> "Request":
        """Returns self."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Returns None."""
        return None

    def serialize(
        self,
        serializer: AbstractRequestSerializer = OpenAISerializer(),
        exclude_none: bool = True,
        exclude_unset: bool = True,
        exclude: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        # First, we serialize the request as a dictionary.
        response = self.dict(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            exclude=exclude or {"retries"},
        )

        # Then, we serialize the messages, functions, and function_call.
        return serializer.to_dict(**response)

    class Config:
        allow_extra_fields = True
