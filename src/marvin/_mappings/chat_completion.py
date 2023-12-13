import json
from enum import Enum
from types import GenericAlias
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
    Union,
)

from pydantic import BaseModel, TypeAdapter, ValidationError

from .types import cast_type_to_options

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletion,
        ChatCompletionMessage,
        ChatCompletionMessageToolCall,
    )

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=Union[Enum, GenericAlias])


def chat_completion_to_model(
    response_model: type[T], completion: "ChatCompletion", field_name: str = "data"
) -> T:
    message: ChatCompletionMessage = completion.choices[0].message
    if message.tool_calls is None:
        raise ValueError("tool_calls is None")
    tool_calls: list[ChatCompletionMessageToolCall] = message.tool_calls
    tool_arguments: list[str] = [tool.function.arguments for tool in tool_calls]
    try:
        return [
            response_model.model_validate_json(argument) for argument in tool_arguments
        ][0]
    except ValidationError:
        """If the model is not a pydantic model, then we can't validate it, so we just return the raw json"""  # noqa
        data: dict[str, Any] = {}
        data[field_name] = json.loads(tool_arguments[0])
        return response_model.model_validate_json(json.dumps(data))


def chat_completion_to_type(response_type: U, completion: "ChatCompletion") -> "U":
    options = cast_type_to_options(response_type)
    message: ChatCompletionMessage = completion.choices[0].message
    if message.content is None:
        raise ValueError("content is None")
    content: str = message.content
    validator: Callable[[str], U] = TypeAdapter(response_type).validate_strings
    return validator(options[int(content)])
