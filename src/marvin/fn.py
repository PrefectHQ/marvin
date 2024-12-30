from typing import Callable, Optional
from functools import partial, wraps
import inspect

from marvin.utilities.types import PythonFunction


def fn(func: Optional[Callable] = None) -> Callable:
    """
    Converts a Python function into an AI function using a decorator.

    This decorator allows a Python function to be converted into an AI function.
    The AI function uses a language model to generate its output.

    Args:
        func (Callable, optional): The function to be converted. Defaults to None.
        model_kwargs (dict, optional): Additional keyword arguments for the
            language model. Defaults to None.
        client (AsyncMarvinClient, optional): The client to use for the AI function.

    Returns:
        Callable: The converted AI function.

    Example:
        ```python
        @fn
        def list_fruit(n:int) -> list[str]:
            '''generates a list of n fruit'''

        list_fruit(3) # ['apple', 'banana', 'orange']
        ```
    """

    if func is None:
        return partial(fn)

    @wraps(func)
    async def async_wrapper(*args, _model_kwargs: dict = None, **kwargs):
        """
        _model_kwargs allows users to provide model overrides at call time
        it is merged into the model_kwargs dict
        """
        model = PythonFunction.from_function_call(func, *args, **kwargs)

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

        result = await _generate_typed_llm_response_with_tool(
            prompt_template=FUNCTION_PROMPT,
            prompt_kwargs=dict(
                fn_definition=model.definition,
                bound_parameters=model.bound_parameters,
                return_value=model.return_value,
            ),
            type_=type_,
            model_kwargs=(model_kwargs or {}) | (_model_kwargs or {}),
            client=client,
        )

        return result

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return run_sync(async_wrapper(*args, **kwargs))

        return sync_wrapper
