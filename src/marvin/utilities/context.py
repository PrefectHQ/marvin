import contextvars
from contextlib import contextmanager


class ScopedContext:
    def __init__(self):
        self._context_storage = contextvars.ContextVar(
            "scoped_context_storage", default={}
        )

    def get(self, key, default=None):
        return self._context_storage.get().get(key, default)

    def set(self, **kwargs):
        ctx = self._context_storage.get()
        updated_ctx = {**ctx, **kwargs}
        self._context_storage.set(updated_ctx)

    @contextmanager
    def __call__(self, **kwargs):
        current_context = self._context_storage.get().copy()
        self.set(**kwargs)
        try:
            yield
        finally:
            self._context_storage.set(current_context)
