from functools import wraps
from typing import Any, Callable, TypeVar, Union

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

ConfigDict = TypeVar("ConfigDict", bound=dict[str, Any])


def default_error_handler(exception: Exception) -> bool:
    return "ValidationError" in str(type(exception))


def retry_with_fallback(
    retry_configs: list[Union[ConfigDict, tuple[ConfigDict, int]]],
    error_handler: Callable[[Exception], Any] = default_error_handler,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    A decorator that retries a function with different configurations.

    Args:
        retry_configs: A list of configurations to try. Each configuration can be either a
            dictionary of function kwargs or a tuple of (function_kwargs, retry_count).
        error_handler: A function that takes an exception as input and returns a truthy value
            if the exception should be handled. Defaults to handling exceptions with 'ValidationError' in their name.

    Returns:
        The decorated function.

    Example:
        ```python
        from pydantic import BaseModel
        from marvin.utilities.retries import retry_with_fallback

        class SomeFancyType(BaseModel):
            some_field: str

        class LLMMadLib(BaseModel):
            what_i_want: SomeFancyType

        @retry_with_fallback(
            [
                # try a cheaper model first at higher temperature
                ({"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.7}}, 3),
                # if that fails, try again with the same model at lower temperature
                ({"model_kwargs": {"model": "gpt-3.5-turbo", "temperature": 0.3}}, 3),
                # then try a more expensive model at lower temperature
                ({"model_kwargs": {"model": "gpt-4", "temperature": 0.0}}, 2),
            ]
        )
        def event_handler(model_kwargs):
            print(f"Trying with {model_kwargs}")
            if 'some_model_fails_to_call_FormatResponse' != 'cool':
                LLMMadLib(what_i_want={"im sorry": "but as Large Language Model..."})
            return "Nice madlib!"

        event_handler({"model": "gpt-3.5-turbo", "temperature": 0.9})
        ```
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for config in retry_configs:
                param_values, retries = (
                    (config, 1) if isinstance(config, dict) else config
                )

                for _ in range(retries):
                    # Merge inner dictionaries
                    for param_name, value in param_values.items():
                        if param_name in kwargs:
                            # Update only the keys that are not present in the user-provided dictionary
                            for key, val in value.items():
                                kwargs[param_name].setdefault(key, val)
                        else:
                            kwargs[param_name] = value

                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        logger.debug_kv("Retrying", str(e), "red")
                        last_exception = e
                        if not error_handler(e):
                            raise

            raise RuntimeError(
                f"All retries have failed. Last exception: {last_exception}"
            ) from last_exception

        return wrapper

    return decorator
