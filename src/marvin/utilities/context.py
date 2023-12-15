"""Module for defining context utilities."""

import contextvars
from contextlib import contextmanager
from typing import Any, Generator


class ScopedContext:
    """`ScopedContext` provides a context management mechanism using `contextvars`.

    This class allows setting and retrieving key-value pairs in a scoped context,
    which is preserved across asynchronous tasks and threads within the same context.

    Attributes:
        _context_storage (ContextVar): A context variable to store the context data.

    Example:
        Basic Usage of ScopedContext
        ```python
        context = ScopedContext()
        with context(key="value"):
            assert context.get("key") == "value"
        # Outside the context, the value is no longer available.
        assert context.get("key") is None
        ```
    """

    def __init__(self):
        """Initializes the ScopedContext with a default empty dictionary."""
        self._context_storage = contextvars.ContextVar(
            "scoped_context_storage", default={}
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._context_storage.get().get(key, default)

    def set(self, **kwargs: Any) -> None:
        ctx = self._context_storage.get()
        updated_ctx = {**ctx, **kwargs}
        self._context_storage.set(updated_ctx)

    @contextmanager
    def __call__(self, **kwargs: Any) -> Generator[None, None, Any]:
        current_context = self._context_storage.get().copy()
        self.set(**kwargs)
        try:
            yield
        finally:
            self._context_storage.set(current_context)
