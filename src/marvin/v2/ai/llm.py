import inspect
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    GenericAlias,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin._mappings.types import (
    cast_labels_to_grammar,
    cast_type_to_labels,
)
from marvin.requests import ChatRequest, ChatResponse
from marvin.utilities.jinja import Transcript
from marvin.utilities.python import PythonFunction
from marvin.v2.ai.prompt_templates import (
    CAST_PROMPT,
    CLASSIFY_PROMPT,
    EXTRACT_PROMPT,
    FUNCTION_PROMPT,
)
from marvin.v2.client import ChatCompletion, MarvinClient

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


def generate_llm_response(
    prompt_template: str,
    prompt_kwargs: dict = None,
    llm_kwargs: dict = None,
) -> ChatResponse:
    llm_kwargs = llm_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)
    request = ChatRequest(messages=messages, **llm_kwargs)
    response = MarvinClient().generate_chat(**request.model_dump())
    tool_outputs = get_tool_outputs(request, response)
    return ChatResponse(request=request, response=response, tool_outputs=tool_outputs)


def get_tool_outputs(request: ChatRequest, response: ChatCompletion) -> list[Any]:
    outputs = []
    tool_calls = response.choices[0].message.tool_calls or []
    for tool_call in tool_calls:
        tool_output = marvin.utilities.tools.call_function_tool(
            tools=request.tools,
            function_name=tool_call.function.name,
            function_arguments_json=tool_call.function.arguments,
        )
        outputs.append(tool_output)
    return outputs


def _generate_typed_llm_response_with_tool(
    prompt_template: str,
    type_: Union[GenericAlias, type[T]],
    tool_name: str = None,
    prompt_kwargs: dict = None,
    llm_kwargs: dict = None,
) -> T:
    llm_kwargs = llm_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    tool = marvin.utilities.tools.tool_from_type(type_, tool_name=tool_name)
    tool_choice = tool_choice = {
        "type": "function",
        "function": {"name": tool.function.name},
    }
    llm_kwargs.update(tools=[tool], tool_choice=tool_choice)

    # adding the tool parameters to the context helps GPT-4 pay attention to field
    # descriptions. If they are only in the tool signature it often ignores them.
    prompt_kwargs["response_format"] = tool.function.parameters

    response = generate_llm_response(
        prompt_template=prompt_template,
        prompt_kwargs=prompt_kwargs,
        llm_kwargs=llm_kwargs | dict(temperature=0),
    )

    return response.tool_outputs[0]


def _generate_typed_llm_response_with_logit_bias(
    prompt_template: str,
    prompt_kwargs: dict,
    encoder: Callable[[str], list[int]] = None,
    max_tokens: int = 1,
    llm_kwargs: dict = None,
) -> T:
    """
    Generates a response to a prompt that is constrained to a set of labels.

    The LLM will be constrained to output a single number representing the
    0-indexed position of the chosen option. Therefore the labels must be
    present (and ideally enumerated) in the prompt template, and will be
    provided as the kwarg `labels`
    """
    llm_kwargs = llm_kwargs or {}

    if "labels" not in prompt_kwargs:
        raise ValueError("Labels must be provided as a kwarg to the prompt template.")
    labels = prompt_kwargs["labels"]
    string_labels = cast_type_to_labels(labels)
    grammar = cast_labels_to_grammar(
        labels=string_labels, encoder=encoder, max_tokens=max_tokens
    )
    llm_kwargs.update(grammar.model_dump())
    response = generate_llm_response(
        prompt_template=prompt_template,
        prompt_kwargs=(prompt_kwargs or {}) | dict(labels=string_labels),
        llm_kwargs=llm_kwargs | dict(temperature=0),
    )
    # the response contains a single number representing the index of the chosen
    result = string_labels[int(response.response.choices[0].message.content)]
    # if the original labels were a type (like enum or bool), we cast the result
    # back to that type
    if isinstance(labels, type):
        if labels is bool:
            result = result == "True"
        else:
            result = labels(result)
    return result


def cast(
    data: str,
    type_: type[T],
    instructions: str = None,
    llm_kwargs: dict = None,
) -> T:
    """
    Convert data into the provided type.
    """
    return _generate_typed_llm_response_with_tool(
        prompt_template=CAST_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=type_,
        llm_kwargs=llm_kwargs,
    )


def extract(
    data: str,
    type_: type[T],
    instructions: str = None,
    llm_kwargs: dict = None,
) -> list[T]:
    """
    Extract entities from the provided data.
    """
    return _generate_typed_llm_response_with_tool(
        prompt_template=EXTRACT_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=list[type_],
        llm_kwargs=llm_kwargs,
    )


def classify(
    data: str,
    labels: Union[Enum, list[T], type],
    instructions: str = None,
    llm_kwargs: dict = None,
) -> T:
    """
    Classify the provided information as of the provided labels.

    This uses a logit bias to constrain the LLM response to a single token. It
    is highly efficient for classification tasks and will always return one of
    the provided responses.
    """
    return _generate_typed_llm_response_with_logit_bias(
        prompt_template=CLASSIFY_PROMPT,
        prompt_kwargs=dict(data=data, labels=labels, instructions=instructions),
        llm_kwargs=llm_kwargs,
    )


def fn(func: Callable):
    """
    A decorator that converts a Python function into an AI function.

    @fn
    def list_fruit(n:int) -> list[str]:
        '''generates a list of n fruit'''

    list_fruit(3) # ['apple', 'banana', 'orange']
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(func, *args, **kwargs)

        if (
            isinstance(model.return_annotation, str)
            or model.return_annotation is None
            or model.return_annotation is inspect.Signature.empty
        ):
            type_ = str
        else:
            type_ = model.return_annotation

        return _generate_typed_llm_response_with_tool(
            prompt_template=FUNCTION_PROMPT,
            prompt_kwargs=dict(
                fn_definition=model.definition,
                bound_parameters=model.bound_parameters,
                return_value=model.return_value,
            ),
            type_=type_,
        )

    return wrapper


class AIModel(BaseModel):
    """
    A Pydantic model that can be instantiated from a natural language string, in
    addition to keyword arguments.
    """

    @classmethod
    def from_text(cls, text: str, llm_kwargs: dict = None, **kwargs) -> "AIModel":
        """Async text constructor"""
        ai_kwargs = cast(text, cls, llm_kwargs=llm_kwargs, **kwargs)
        ai_kwargs.update(kwargs)
        return cls(**ai_kwargs)

    def __init__(self, text: str = None, *, llm_kwargs: dict = None, **kwargs):
        ai_kwargs = kwargs
        if text is not None:
            ai_kwargs = cast(text, type(self), llm_kwargs=llm_kwargs).model_dump()
            ai_kwargs.update(kwargs)
        super().__init__(**ai_kwargs)


def model(
    type_: Union[Type[M], None] = None, llm_kwargs: dict = None
) -> Union[Type[M], Callable[[Type[M]], Type[M]]]:
    """
    Class decorator for instantiating a Pydantic model from a string. Equivalent
    to subclassing AIModel.
    """
    llm_kwargs = llm_kwargs or {}

    def decorator(cls: Type[M]) -> Type[M]:
        class WrappedModel(AIModel, cls):
            @wraps(cls.__init__)
            def __init__(self, *args, **kwargs):
                super().__init__(*args, llm_kwargs=llm_kwargs, **kwargs)

        WrappedModel.__name__ = cls.__name__
        WrappedModel.__doc__ = cls.__doc__
        return WrappedModel

    if type_ is not None:
        return decorator(type_)
    return decorator
