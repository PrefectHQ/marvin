import inspect
from functools import wraps
from typing import Any, Callable

from pydantic import BaseModel, Field

from marvin.utilities.logging import get_logger
from marvin.utilities.pydantic import parse_as


class RetryConfig(BaseModel):
    override_kwargs: dict[str, Any] = Field(default_factory=dict, alias="model_kwargs")
    retries: int = 1


def default_error_handler(exception: Exception) -> bool:
    print(type(exception), exception)
    return "ValidationError" in str(type(exception))


logger = get_logger(__name__)


def retry_with_fallback(
    retry_configs: list[RetryConfig],
    config_field_name: str = "model_kwargs",
    error_handler: Callable[[Exception], bool] = default_error_handler,
) -> Callable:
    """Decorator that retries a function with different kwargs.

    Args:
        retry_configs (list[RetryConfig]): A list of retry configurations.
        error_handler (Callable[[Exception], bool], optional): A function that determines whether an exception should be handled. Defaults to default_error_handler.

    Examples:
        ```python
        from pydantic import BaseModel, Field
        from marvin.utilities.retries import retry_with_fallback

        class SomeFancyType(BaseModel):
            some_field: str

        class LLMMadLib(BaseModel):
            what_i_want: SomeFancyType

        RETRY_CONFIGS = [
            {'model_kwargs': {'model': 'gpt-3.5-turbo', 'temperature': 0.7}, 'retries': 3},
            {'model_kwargs': {'model': 'gpt-3.5-turbo', 'temperature': 0.3}, 'retries': 3},
            {'model_kwargs': {'model': 'gpt-4', 'temperature': 0.0}, 'retries': 2},
        ]

        @retry_with_fallback(RETRY_CONFIGS)
        def make_a_complex_schema(model_kwargs=None):
            if 'my_schema_is_too_complex_for_wimpy_models' != False:
                LLMMadLib(what_i_want="I'm sorry, as a Large Language Model, I can't do that.")
            return LLMMadLib(what_i_want=SomeFancyType(some_field="I'm a fancy type!"))

        print(make_a_complex_schema())
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                maybe_coro = func(*args, **kwargs)
                if inspect.isawaitable(maybe_coro):
                    return await maybe_coro
                return maybe_coro

            except Exception as initial_exception:
                if not error_handler(initial_exception):
                    raise
                last_exception = None

                for config in parse_as(list[RetryConfig], retry_configs):
                    for _ in range(config.retries):
                        logger.debug_kv(
                            "Retrying",
                            f"{func.__name__} with {config_field_name}={config.override_kwargs}.",
                            "red",
                        )
                        try:
                            maybe_coro = func(
                                *args,
                                **kwargs | {config_field_name: config.override_kwargs},
                            )
                            if inspect.isawaitable(maybe_coro):
                                return await maybe_coro
                            return maybe_coro

                        except Exception as e:
                            last_exception = e
                            if not error_handler(e):
                                raise
                raise RuntimeError(
                    f"All retries have failed. Last exception: {last_exception!r}"
                ) from last_exception

        return wrapper

    return decorator
