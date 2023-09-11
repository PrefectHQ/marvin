from types import GenericAlias
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union

from marvin._compat import BaseModel, cast_to_json, model_dump  # type: ignore

if TYPE_CHECKING:
    from .messages import Message


def cast_response_model_to_json(
    response_model: Optional[
        Union[
            type,  # e.g. str
            GenericAlias,  # e.g. list[str]
            type[BaseModel],  # e.g. Person
            Callable[..., Any],  # e.g. Callable[[str], str]
        ]
    ] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    if response_model is None:
        return {}
    json_schema = cast_to_json(response_model, name, description)
    response: dict[str, Any] = {}
    response["functions"] = [json_schema]
    response["function_call"] = {"name": json_schema.get("name")}
    return response


def cast_function_to_json(
    function: (
        Union[
            Callable[..., Any],  # e.g. str
            type[BaseModel],  # e.g. Person
            dict[str, Any],  # e.g. {'name': 'Person', 'description': 'A person.'}
        ]
    )
) -> dict[str, Any]:
    """
    Serializes a function to JSON.

    :param function: A function to serialize.

    :returns: A JSON-serializable dictionary.
    """
    if isinstance(function, dict):
        return function
    return cast_to_json(function)


def cast_functions_to_json(
    functions: (
        Optional[
            list[
                Union[
                    Callable[..., Any],  # e.g. str
                    type[BaseModel],  # e.g. Person
                    dict[
                        str, Any
                    ],  # e.g. {'name': 'Person', 'description': 'A person.'}
                ]
            ]
        ]
    ) = None,
) -> list[dict[str, Any]]:
    """
    Serializes a list of functions to JSON.

    :param functions: A list of functions to serialize.

    :returns: A JSON-serializable list of functions.
    """

    return [cast_function_to_json(function) for function in functions or []]


def model_serialize(
    *,
    messages: Optional[list["Message"]] = None,
    functions: Optional[
        list[Union[Callable[..., Any], type[BaseModel], dict[str, Any]]]
    ] = None,  # noqa
    function_call: Optional[
        Union[Literal["auto"], dict[Literal["name"], str]]
    ] = None,  # noqa
    response_model: Optional[
        Union[type, GenericAlias, type[BaseModel], Callable[..., Any]]
    ] = None,  # noqa
    response_model_name: Optional[str] = None,
    response_model_description: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Serializes a model to JSON.

    :param messages: A list of messages to serialize.
    :param functions: A list of functions to serialize.
    :param function_call: A function call to serialize.
    :param response_model: A response model to serialize.

    :returns: A JSON-serializable dictionary.

    NOTE: If a response model is provided, the function call will be set to
    the response model's name and the functions will be set to the response
    model's JSON schema. This is done to make the response model the
    default function call and function. This may change in the future
    to allow for multiple function calls and functions.

    """

    return {
        key: value
        for key, value in {
            "messages": [
                model_dump(message, exclude_none=True) for message in messages or []
            ],
            **({"functions": cast_functions_to_json(functions)} if functions else {}),
            **({"function_call": function_call} if function_call else {}),
            **cast_response_model_to_json(
                response_model,
                name=response_model_name,
                description=response_model_description,
            ),
            **kwargs,
        }.items()
        if value
    }
