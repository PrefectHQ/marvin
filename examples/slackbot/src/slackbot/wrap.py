import inspect
from contextlib import ContextDecorator
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, TypeVar

from prefect import tags as prefect_tags
from prefect import task
from pydantic_ai.tools import Tool

T = TypeVar("T")

_progress_message: ContextVar[Any] = ContextVar("progress_message", default=None)


class DecorateMethodContext(ContextDecorator):
    """Context decorator for patching methods with a decorator."""

    def __init__(
        self,
        patch_cls: type,
        patch_method_name: str,
        decorator: Callable[..., Callable[..., T]],
        **decorator_kwargs,
    ):
        """Initialize the context manager.
        Args:
            decorator_kwargs: Keyword arguments to pass to the decorator.
        """
        self.patch_cls = patch_cls
        self.patch_method = patch_method_name
        self.decorator = decorator
        self.decorator_kwargs = decorator_kwargs

    def __enter__(self):
        """Called when entering the context manager."""
        self.patched_methods = []
        for cls in {self.patch_cls, *self.patch_cls.__subclasses__()}:
            self._patch_method(
                cls=cls,
                method_name=self.patch_method,
                decorator=self.decorator,
            )

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Reset methods when exiting the context manager."""
        for cls, method_name, original_method in self.patched_methods:
            setattr(cls, method_name, original_method)

    def _patch_method(self, cls, method_name, decorator):
        """Patch a method on a class with a decorator."""
        original_method = getattr(cls, method_name)
        modified_method = decorator(original_method, **self.decorator_kwargs)
        setattr(cls, method_name, modified_method)
        self.patched_methods.append((cls, method_name, original_method))


def prefect_wrapped_function(
    func: Callable[..., T],
    decorator: Callable[..., Callable[..., T]] = task,
    tags: set[str] | None = None,
    settings: dict[str, Any] | None = None,
) -> Callable[..., Callable[..., T]]:
    """Decorator for wrapping a function with a prefect decorator."""
    tags = tags or set[str]()

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        if _progress := _progress_message.get():
            tool_name = "Unknown Tool"
            if args and hasattr(args[0], "name"):
                tool_name = args[0].name
            elif (
                args
                and hasattr(args[0], "function")
                and hasattr(args[0].function, "__name__")
            ):
                tool_name = args[0].function.__name__

            try:
                await _progress.append(f"🔧 {tool_name}")
            except Exception:
                pass

        wrapped_callable = decorator(**settings or {})(func)
        with prefect_tags(*tags):
            result = wrapped_callable(*args, **kwargs)  # type: ignore
            if inspect.isawaitable(result):
                result = await result

            return result

    return wrapper  # type: ignore


class WatchToolCalls(DecorateMethodContext):
    """Context decorator for patching a method with a prefect flow."""

    def __init__(
        self,
        patch_cls: type = Tool,
        patch_method_name: str = "run",
        tags: set[str] | None = None,
        settings: dict[str, Any] | None = None,
    ):
        """Initialize the context manager.
        Args:
            tags: Prefect tags to apply to the flow.
            flow_kwargs: Keyword arguments to pass to the flow.
        """
        super().__init__(
            patch_cls=patch_cls,
            patch_method_name=patch_method_name,
            decorator=prefect_wrapped_function,
            tags=tags,
            settings=settings,
        )
