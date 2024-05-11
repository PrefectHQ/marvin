"""Module for defining context utilities."""

import contextvars
from contextlib import contextmanager
from typing import Any, Generator


class ScopedContext:
    """
    `ScopedContext` provides a context management mechanism using `contextvars`.

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

    def __init__(self, initial_value: dict = None):
        """Initializes the ScopedContext with an initial valuedictionary."""
        self._context_storage = contextvars.ContextVar(
            "scoped_context_storage", default=initial_value or {}
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._context_storage.get().get(key, default)

    def __getitem__(self, key: str) -> Any:
        notfound = object()
        result = self.get(key, default=notfound)
        if result == notfound:
            raise KeyError(key)
        return result

    def set(self, **kwargs: Any) -> None:
        ctx = self._context_storage.get()
        updated_ctx = {**ctx, **kwargs}
        token = self._context_storage.set(updated_ctx)
        return token

    @contextmanager
    def __call__(self, **kwargs: Any) -> Generator[None, None, Any]:
        current_context_copy = self._context_storage.get().copy()
        token = self.set(**kwargs)
        try:
            yield
        finally:
            try:
                self._context_storage.reset(token)
            except ValueError as exc:
                if "was created in a different context" in str(exc).lower():
                    # the only way we can reach this line is if the setup and
                    # teardown of this context are run in different frames or
                    # threads (which happens with pytest fixtures!), in which case
                    # the token is considered invalid. This catch serves as a
                    # "manual" reset of the context values
                    self._context_storage.set(current_context_copy)
                else:
                    raise


ctx = ScopedContext()
