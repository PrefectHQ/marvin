"""
Core LLM tools for working with text and structured data.
"""

import inspect
from collections import deque
from enum import Enum
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    GenericAlias,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    get_origin,
)

from cachetools import LRUCache
from pydantic import BaseModel

import marvin
import marvin.utilities.tools
from marvin._mappings.types import (
    cast_labels_to_grammar,
    cast_type_to_labels,
)
from marvin.ai.prompts.text_prompts import (
    CAST_PROMPT,
    CLASSIFY_PROMPT,
    EXTRACT_PROMPT,
    FUNCTION_PROMPT,
    GENERATE_PROMPT,
)
from marvin.client.openai import ChatCompletion, MarvinClient
from marvin.types import ChatRequest, ChatResponse
from marvin.utilities.context import ctx
from marvin.utilities.jinja import Transcript
from marvin.utilities.logging import get_logger
from marvin.utilities.python import PythonFunction

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)

logger = get_logger(__name__)

GENERATE_CACHE = LRUCache(maxsize=1000)


class EjectRequest(Exception):
    def __init__(self, request):
        self.request = request
        super().__init__("Ejected request.")


def generate_llm_response(
    prompt_template: str,
    prompt_kwargs: Optional[dict] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> ChatResponse:
    """
    Generates a language model response based on a provided prompt template.

    This function uses a language model to generate a response based on a provided prompt template.
    The function supports additional arguments for the prompt and the language model.

    Args:
        prompt_template (str): The template for the prompt.
        prompt_kwargs (dict, optional): Additional keyword arguments for the prompt. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the language model. Defaults to None.

    Returns:
        ChatResponse: The generated response from the language model.
    """
    client = client or MarvinClient()
    model_kwargs = model_kwargs or {}
    prompt_kwargs = prompt_kwargs or {}
    messages = Transcript(content=prompt_template).render_to_messages(**prompt_kwargs)

    request = ChatRequest(messages=messages, **model_kwargs)
    if ctx.get("eject_request"):
        raise EjectRequest(request)
    if marvin.settings.log_verbose:
        logger.debug_kv("Request", request.model_dump_json(indent=2))
    response = client.generate_chat(**request.model_dump())
    if marvin.settings.log_verbose:
        logger.debug_kv("Response", response.model_dump_json(indent=2))
    tool_outputs = _get_tool_outputs(request, response)
    return ChatResponse(request=request, response=response, tool_outputs=tool_outputs)


def _get_tool_outputs(request: ChatRequest, response: ChatCompletion) -> list[Any]:
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
    tool_name: Optional[str] = None,
    prompt_kwargs: Optional[dict] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> T:
    """
    Generates a language model response based on a provided prompt template and a specific tool.

    This function uses a language model to generate a response based on a
    provided prompt template. The response is cast to a Python type using a tool
    call. The function supports additional arguments for the prompt and the
    language model.

    Args:
        prompt_template (str): The template for the prompt.
        type_ (Union[GenericAlias, type[T]]): The type of the response to
            generate.
        tool_name (str, optional): The name of the tool to use for the
            generation. Defaults to None.
        prompt_kwargs (dict, optional): Additional keyword arguments for the
            prompt. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        T: The generated response from the language model.
    """
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
        client=client,
    )

    return response.tool_outputs[0]


def _generate_typed_llm_response_with_logit_bias(
    prompt_template: str,
    prompt_kwargs: dict,
    encoder: Callable[[str], list[int]] = None,
    max_tokens: int = 1,
    model_kwargs: dict = None,
    client: Optional[MarvinClient] = None,
):
    """
    Generates a language model response with logit bias based on a provided
    prompt template.

    This function uses a language model to generate a response with logit bias
    based on a provided prompt template. The function supports additional
    arguments for the prompt. It also allows specifying an encoder function to
    be used for the generation.

    The LLM will be constrained to output a single number representing the
    0-indexed position of the chosen option. Therefore the labels must be
    present (and ideally enumerated) in the prompt template, and will be
    provided as the kwarg `labels`

    Args:
        prompt_template (str): The template for the prompt.
        prompt_kwargs (dict): Additional keyword arguments for the prompt.
        encoder (Callable[[str], list[int]], optional): The encoder function to
            use for the generation. Defaults to None.
        max_tokens (int, optional): The maximum number of tokens for the
            generation. Defaults to 1.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        ChatResponse: The generated response from the language model.

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
        client=client,
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
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> T:
    """
    Converts the input data into the specified type.

    This function uses a language model to convert the input data into a specified type.
    The conversion process can be guided by specific instructions. The function also
    supports additional arguments for the language model.

    Args:
        data (str): The data to be converted.
        target (type): The type to convert the data into.
        instructions (str, optional): Specific instructions for the conversion. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        T: The converted data of the specified type.
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
            client=client,
        )

    return _generate_typed_llm_response_with_tool(
        prompt_template=CAST_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=target,
        model_kwargs=model_kwargs | dict(temperature=0),
        client=client,
    )


def extract(
    data: str,
    target: type[T],
    instructions: Optional[str] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> list[T]:
    """
    Extracts entities of a specific type from the provided data.

    This function uses a language model to identify and extract entities of the
    specified type from the input data. The extracted entities are returned as a
    list.

    Args:
        data (str): The data from which to extract entities.
        target (type): The type of entities to extract.
        instructions (str, optional): Specific instructions for the extraction.
            Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        list: A list of extracted entities of the specified type.
    """
    model_kwargs = model_kwargs or {}
    return _generate_typed_llm_response_with_tool(
        prompt_template=EXTRACT_PROMPT,
        prompt_kwargs=dict(data=data, instructions=instructions),
        type_=list[target],
        model_kwargs=model_kwargs | dict(temperature=0),
        client=client,
    )


def classify(
    data: str,
    labels: Union[Enum, list[T], type],
    instructions: str = None,
    model_kwargs: dict = None,
    client: Optional[MarvinClient] = None,
) -> T:
    """
    Classifies the provided data based on the provided labels.

    This function uses a language model with a logit bias to classify the input
    data. The logit bias constrains the language model's response to a single
    token, making this function highly efficient for classification tasks. The
    function will always return one of the provided labels.

    Args:
        data (str): The data to be classified.
        labels (Union[Enum, list[T], type]): The labels to classify the data into.
        instructions (str, optional): Specific instructions for the
            classification. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        T: The label that the data was classified into.
    """

    model_kwargs = model_kwargs or {}
    return _generate_typed_llm_response_with_logit_bias(
        prompt_template=CLASSIFY_PROMPT,
        prompt_kwargs=dict(data=data, labels=labels, instructions=instructions),
        model_kwargs=model_kwargs | dict(temperature=0),
        client=client,
    )


def generate(
    target: Optional[type[T]] = None,
    instructions: Optional[str] = None,
    n: int = 1,
    use_cache: bool = True,
    temperature: float = 1,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> list[T]:
    """
    Generates a list of 'n' items of the provided type or based on instructions.

    Either a type or instructions must be provided. If instructions are provided
    without a type, the type is assumed to be a string. The function generates at
    least 'n' items.

    Args:
        target (type, optional): The type of items to generate. Defaults to None.
        instructions (str, optional): Instructions for the generation. Defaults to None.
        n (int, optional): The number of items to generate. Defaults to 1.
        use_cache (bool, optional): If True, the function will cache the last
            100 responses for each (target, instructions, and temperature) and use
            those to avoid repetition on subsequent calls. Defaults to True.
        temperature (float, optional): The temperature for the generation. Defaults to 1.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        list: A list of generated items.
    """

    if target is None and instructions is None:
        raise ValueError("Must provide either a target type or instructions.")
    elif target is None:
        target = str

    # cache the last 30 responses for each (target, instructions, and temperature)
    # to avoid repetition and encourage variation
    cache_key = (target, instructions, temperature)
    cached_responses = GENERATE_CACHE.setdefault(cache_key, deque(maxlen=100))
    previous_responses = list(cached_responses) if use_cache else []

    # make sure we generate at least n items
    result = [0] * (n + 1)
    while len(result) != n:
        result = _generate_typed_llm_response_with_tool(
            prompt_template=GENERATE_PROMPT,
            prompt_kwargs=dict(
                type_=target,
                n=n,
                instructions=instructions,
                previous_responses=previous_responses,
            ),
            type_=list[target],
            model_kwargs=(model_kwargs or {}) | dict(temperature=temperature),
            client=client,
        )

        if len(result) > n:
            result = result[:n]

    # don't cache the respones if we're not using the cache, because the AI will
    # see repeats and conclude they're ok
    if use_cache:
        for r in result:
            cached_responses.appendleft(r)
    return result


def fn(
    func: Optional[Callable] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> Callable:
    """
    Converts a Python function into an AI function using a decorator.

    This decorator allows a Python function to be converted into an AI function.
    The AI function uses a language model to generate its output.

    Args:
        func (Callable, optional): The function to be converted. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (MarvinClient, optional): The client to use for the AI function.

    Returns:
        Callable: The converted AI function.

    Example:
        @fn
        def list_fruit(n:int) -> list[str]:
            '''generates a list of n fruit'''

        list_fruit(3) # ['apple', 'banana', 'orange']
    """

    if func is None:
        return partial(fn, model_kwargs=model_kwargs, client=client)

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
            client=client,
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
        """
        Class method to create an instance of the model from a natural language string.

        Args:
            text (str): The natural language string to convert into an instance of the model.
            model_kwargs (dict, optional): Additional keyword arguments for the
                language model. Defaults to None.
            **kwargs: Additional keyword arguments to pass to the model's constructor.

        Returns:
            Model: An instance of the model.
        """
        ai_kwargs = cast(text, cls, model_kwargs=model_kwargs, **kwargs)
        ai_kwargs.update(kwargs)
        return cls(**ai_kwargs)

    def __init__(
        self,
        text: Optional[str] = None,
        *,
        model_kwargs: Optional[dict] = None,
        client: Optional[MarvinClient] = None,
        **kwargs,
    ):
        """
        Initializes an instance of the model.

        Args:
            text (str, optional): The natural language string to convert into an
                instance of the model. Defaults to None.
            model_kwargs (dict, optional): Additional keyword arguments for the
                language model. Defaults to None.
            **kwargs: Additional keyword arguments to pass to the model's constructor.
        """
        ai_kwargs = kwargs
        if text is not None:
            ai_kwargs = cast(
                text, type(self), model_kwargs=model_kwargs, client=client
            ).model_dump()
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
        instructions (str, optional): Instructions for the AI on
            how to perform the classification.
        model_kwargs (dict, optional): Additional keyword
            arguments to pass to the model.

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
    type_: Union[Type[M], None] = None,
    model_kwargs: Optional[dict] = None,
    client: Optional[MarvinClient] = None,
) -> Union[Type[M], Callable[[Type[M]], Type[M]]]:
    """
    Class decorator for instantiating a Pydantic model from a string.

    This decorator allows a Pydantic model to be instantiated from a string. It's
    equivalent to subclassing the Model class.

    Args:
        type_ (Union[Type[M], None], optional): The type of the Pydantic model.
            Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.

    Returns:
        Union[Type[M], Callable[[Type[M]], Type[M]]]: The decorated Pydantic model.
    """
    model_kwargs = model_kwargs or {}

    def decorator(cls: Type[M]) -> Type[M]:
        class WrappedModel(Model, cls):
            @wraps(cls.__init__)
            def __init__(self, *args, **kwargs):
                super().__init__(
                    *args, model_kwargs=model_kwargs, client=client, **kwargs
                )

        WrappedModel.__name__ = cls.__name__
        WrappedModel.__doc__ = cls.__doc__
        return WrappedModel

    if type_ is not None:
        return decorator(type_)
    return decorator
