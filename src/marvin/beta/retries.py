from functools import wraps
from typing import Callable

from pydantic import ValidationError


def default_exception_handler(exc: Exception) -> str:
    return str(exc)


def retry_fn_on_validation_error(
    fn=None,
    max_retries: int = 3,
    exception_handler: Callable[[Exception], str] = default_exception_handler,
):
    """Decorator for `marvin.fn` that retries the function if it raises a `ValidationError`.
    Optionally, you can provide a custom exception handler to parse the validation error
    and return a custom message that will be appended to the original docstring.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            additional_context = ""
            original_docstring = fn.__wrapped__.__doc__
            retries = 0
            while True:
                try:
                    if additional_context:
                        fn.__wrapped__.__doc__ = f"{original_docstring}\n\nYou've tried this before, but it failed:\n{additional_context}"
                    return fn(*args, **kwargs)
                except ValidationError as e:
                    additional_context += f"\n{exception_handler(e)}"
                    retries += 1
                    if retries == max_retries:
                        raise e

        return wrapper

    if fn is None:
        return decorator
    else:
        return decorator(fn)
