import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

from marvin.utilities.logging import get_logger


def retry_on_exception(
    exception_types: Optional[
        Union[Type[Exception], Tuple[Type[Exception], ...]]
    ] = None,
    retries: int = 3,
    retry_delay_seconds: float = 0.5,
) -> Callable:
    if exception_types is None:
        exception_types = Exception
    if not isinstance(exception_types, tuple):
        exception_types = (exception_types,)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            logger = get_logger("utilities.retries")
            while attempts <= retries:
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    logger.warn(f"Exception raised! {e}\nRetrying...")
                    attempts += 1
                    if attempts > retries:
                        raise e
                    time.sleep(retry_delay_seconds)

        return wrapper

    return decorator
