import contextvars
from contextlib import contextmanager
from typing import Any, Generator


class ScopedContext:
    def __init__(self):
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
