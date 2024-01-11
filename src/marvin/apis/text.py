import inspect
from enum import Enum
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    GenericAlias,
    Literal,
    Type,
    TypeVar,
    Union,
    get_origin,
)

from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin._mappings.types import (
    cast_labels_to_grammar,
    cast_type_to_labels,
)
from marvin.apis.prompts.text_templates import (
    CAST_PROMPT,
    CLASSIFY_PROMPT,
    EXTRACT_PROMPT,
    FUNCTION_PROMPT,
    GENERATE_PROMPT,
)
from marvin.client.openai import ChatCompletion, MarvinClient
from marvin.requests import ChatRequest, ChatResponse
from marvin.utilities.jinja import Transcript
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

logger = get_logger(__name__)


def generate_llm_response(
    prompt_template: str,
    prompt_kwargs: dict = None,
    model_kwargs: dict = None,
) -> ChatResponse:
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)
    request = ChatRequest(messages=messages, **model_kwargs)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = MarvinClient().generate_chat(**request.model_dump())
    if marvin.settings.log_verbose:
        logger.debug_kv("Response", response.model_dump_json(indent=2))
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
    model_kwargs: dict = None,
) -> T:
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    tool = marvin.utilities.tools.tool_from_type(type_, tool_name=tool_name)
    tool_choice = tool_choice = {
        "type": "function",
        "function": {"name": tool.function.name},
    }
    model_kwargs.update(tools=[tool], tool_choice=tool_choice)

    # adding the tool parameters to the context helps GPT-4 pay attention to field
    # descriptions. If they are only in the tool signature it often ignores them.
    prompt_kwargs["response_format"] = tool.function.parameters

    response = generate_llm_response(
        prompt_template=prompt_template,
        prompt_kwargs=prompt_kwargs,
        model_kwargs=model_kwargs,
    )

    return response.tool_outputs[0]


def _generate_typed_llm_response_with_logit_bias(
    prompt_template: str,
    prompt_kwargs: dict,
    encoder: Callable[[str], list[int]] = None,
    max_tokens: int = 1,
    model_kwargs: dict = None,
) -> T:
    """
    Generates a response to a prompt that is constrained to a set of labels.

    The LLM will be constrained to output a single number representing the
    0-indexed position of the chosen option. Therefore the labels must be
    present (and ideally enumerated) in the prompt template, and will be
    provided as the kwarg `labels`
    """
    model_kwargs = model_kwargs or {}

    if "labels" not in prompt_kwargs:
        raise ValueError("Labels must be provided as a kwarg to the prompt template.")
    labels = prompt_kwargs["labels"]
    label_strings = cast_type_to_labels(labels)
    grammar = cast_labels_to_grammar(
        labels=label_strings, encoder=encoder, max_tokens=max_tokens
    )
    model_kwargs.update(grammar.model_dump())
    response = generate_llm_response(
        prompt_template=prompt_template,
        prompt_kwargs=(prompt_kwargs or {}) | dict(labels=label_strings),
        model_kwargs=model_kwargs | dict(temperature=0),
    )

    # the response contains a single number representing the index of the chosen
    label_index = int(response.response.choices[0].message.content)

    if labels is bool:
        return bool(label_index)

    result = label_strings[label_index]
    return labels(result) if isinstance(labels, type) else result


def cast(
    data: str,
    target: type[T],
    instructions: str = None,
    model_kwargs: dict = None,
) -> T:
    """
    Convert data into the provided type.
    """
    model_kwargs = model_kwargs or {}

    # if the user provided a `to` type that represents a list of labels, we use
    # `classify()` for performance.
    if (
        get_origin(target) == Literal
        or (isinstance(target, type) and issubclass(target, Enum))
        or isinstance(target, list)
        or target is bool
    ):
        return classify(
            data=data,
            labels=target,
            instructions=instructions,
            model_kwargs=model_kwargs,
        )

    return _generate_typed_llm_response_with_tool(
        prompt_template=CAST_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=target,
        model_kwargs=model_kwargs | dict(temperature=0),
    )


def extract(
    data: str,
    target: type[T],
    instructions: str = None,
    model_kwargs: dict = None,
) -> list[T]:
    """
    Extract entities from the provided data.
    """
    model_kwargs = model_kwargs or {}
    return _generate_typed_llm_response_with_tool(
        prompt_template=EXTRACT_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=list[target],
        model_kwargs=model_kwargs | dict(temperature=0),
    )


def classify(
    data: str,
    labels: Union[Enum, list[T], type],
    instructions: str = None,
    model_kwargs: dict = None,
) -> T:
    """
    Classify the provided information as of the provided labels.

    This uses a logit bias to constrain the LLM response to a single token. It
    is highly efficient for classification tasks and will always return one of
    the provided responses.
    """

    model_kwargs = model_kwargs or {}
    return _generate_typed_llm_response_with_logit_bias(
        prompt_template=CLASSIFY_PROMPT,
        prompt_kwargs=dict(data=data, labels=labels, instructions=instructions),
        model_kwargs=model_kwargs | dict(temperature=0),
    )


def generate(
    type_: type[T] = None,
    instructions: str = None,
    n: int = 1,
    temperature: float = 1,
    model_kwargs: dict = None,
) -> list[T]:
    """
    Generate a list of n items of the provided type or instructions.

    Either a type or instructions must be provided. If instructions are
    provided without a type, the type is assumed to be a string.
    """

    if type_ is None and instructions is None:
        raise ValueError("Must provide either a type or instructions.")
    elif type_ is None:
        type_ = str

    # make sure we generate at least n items
    result = [0] * (n + 1)
    while len(result) != n:
        result = _generate_typed_llm_response_with_tool(
            prompt_template=GENERATE_PROMPT,
            prompt_kwargs=dict(type_=type_, n=n, instructions=instructions),
            type_=list[type_],
            model_kwargs=(model_kwargs or {}) | dict(temperature=temperature),
        )

        if len(result) > n:
            result = result[:n]
    return result


def fn(func: Callable = None, model_kwargs: dict = None):
    """
    A decorator that converts a Python function into an AI function.

    @fn
    def list_fruit(n:int) -> list[str]:
        '''generates a list of n fruit'''

    list_fruit(3) # ['apple', 'banana', 'orange']
    """

    if func is None:
        return partial(fn, model_kwargs=model_kwargs)

    @wraps(func)
    def wrapper(*args, **kwargs):
        model = PythonFunction.from_function_call(func, *args, **kwargs)
        post_processor = None

        # written instructions or missing annotations are treated as "-> str"
        if (
            isinstance(model.return_annotation, str)
            or model.return_annotation is None
            or model.return_annotation is inspect.Signature.empty
        ):
            type_ = str

        # convert list annotations into Enums
        elif isinstance(model.return_annotation, list):
            type_ = Enum(
                "Labels",
                {f"v{i}": label for i, label in enumerate(model.return_annotation)},
            )
            post_processor = lambda result: result.value  # noqa E731

        else:
            type_ = model.return_annotation

        result = _generate_typed_llm_response_with_tool(
            prompt_template=FUNCTION_PROMPT,
            prompt_kwargs=dict(
                fn_definition=model.definition,
                bound_parameters=model.bound_parameters,
                return_value=model.return_value,
            ),
            type_=type_,
            model_kwargs=model_kwargs,
        )

        if post_processor is not None:
            result = post_processor(result)
        return result

    return wrapper


class Model(BaseModel):
    """
    A Pydantic model that can be instantiated from a natural language string, in
    addition to keyword arguments.
    """

    @classmethod
    def from_text(cls, text: str, model_kwargs: dict = None, **kwargs) -> "Model":
        """Async text constructor"""
        ai_kwargs = cast(text, cls, model_kwargs=model_kwargs, **kwargs)
        ai_kwargs.update(kwargs)
        return cls(**ai_kwargs)

    def __init__(self, text: str = None, *, model_kwargs: dict = None, **kwargs):
        ai_kwargs = kwargs
        if text is not None:
            ai_kwargs = cast(text, type(self), model_kwargs=model_kwargs).model_dump()
            ai_kwargs.update(kwargs)
        super().__init__(**ai_kwargs)


def classifier(cls=None, *, instructions=None, model_kwargs=None):
    """
    Class decorator that modifies the behavior of an Enum class to classify a string.

    This decorator modifies the __call__ method of the Enum class to use the
    `marvin.classify` function instead of the default Enum behavior. This allows
    the Enum class to classify a string based on its members.

    Args:
        cls (Enum, optional): The Enum class to be decorated.
        instructions (str, optional): Instructions for the AI on how to perform the classification.
        model_kwargs (dict, optional): Additional keyword arguments to pass to the model.

    Returns:
        Enum: The decorated Enum class with modified __call__ method.

    Raises:
        AssertionError: If the decorated class is not a subclass of Enum.
    """

    if cls is None:
        return partial(classifier, instructions=instructions, model_kwargs=model_kwargs)
    else:
        if not (isinstance(cls, type) and issubclass(cls, Enum)):
            raise TypeError(
                "Only subclasses of Enum can be decorated with @classifier."
            )

        enum_instructions = (
            f"Labels name: {cls.__name__}\nAdditional instructions: {cls.__doc__}"
        )
        instructions = instructions or enum_instructions

        def new(cls, value):
            if value in cls.__members__.values():
                return value
            elif value in {m.value for m in cls.__members__.values()}:
                return super(cls, cls).__new__(cls, value)
            else:
                return marvin.classify(
                    value, cls, instructions=instructions, **(model_kwargs or {})
                )

        cls.__new__ = new
        return cls


def model(
    type_: Union[Type[M], None] = None, model_kwargs: dict = None
) -> Union[Type[M], Callable[[Type[M]], Type[M]]]:
    """
    Class decorator for instantiating a Pydantic model from a string. Equivalent
    to subclassing Model.
    """
    model_kwargs = model_kwargs or {}

    def decorator(cls: Type[M]) -> Type[M]:
        class WrappedModel(Model, cls):
            @wraps(cls.__init__)
            def __init__(self, *args, **kwargs):
                super().__init__(*args, model_kwargs=model_kwargs, **kwargs)

        WrappedModel.__name__ = cls.__name__
        WrappedModel.__doc__ = cls.__doc__
        return WrappedModel

    if type_ is not None:
        return decorator(type_)
    return decorator
