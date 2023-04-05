from contextlib import contextmanager

from marvin import ai_fn


@ai_fn
def explain_error(exc: str) -> str:
    """Explain the error and how to fix it, if possible."""


# a Python context manager that automatically explains errors
@contextmanager
def ai_errors():
    try:
        yield
    except Exception as exc:
        print(explain_error(exc))
        raise


# use the context manager like this
with ai_errors():
    x = 1 + "abc"
