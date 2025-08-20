"""Generic monkey-patching utilities."""

from contextlib import ContextDecorator
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")


class MonkeyPatch(ContextDecorator):
    """Context manager for temporarily patching methods on classes.

    This is a clean, reusable utility for monkey-patching that doesn't
    know anything about the specific framework or use case.
    """

    def __init__(
        self,
        target_cls: type,
        method_name: str,
        wrapper_fn: Callable[[Callable], Callable],
    ):
        """Initialize the monkey patch.

        Args:
            target_cls: The class to patch
            method_name: Name of the method to patch
            wrapper_fn: Function that takes the original method and returns a wrapped version
        """
        self.target_cls = target_cls
        self.method_name = method_name
        self.wrapper_fn = wrapper_fn
        self.patched_items = []

    def __enter__(self):
        """Apply the monkey patch."""
        # Patch the target class and all its subclasses
        for cls in {self.target_cls, *self.target_cls.__subclasses__()}:
            original_method = getattr(cls, self.method_name, None)
            if original_method is not None:
                # Mark the original method so we can detect it
                if not hasattr(original_method, "_monkey_patch_original"):
                    wrapped_method = self.wrapper_fn(original_method)
                    wrapped_method._monkey_patch_original = original_method
                    setattr(cls, self.method_name, wrapped_method)
                    self.patched_items.append((cls, self.method_name, original_method))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original methods."""
        for cls, method_name, original_method in self.patched_items:
            setattr(cls, method_name, original_method)
        self.patched_items.clear()


def create_wrapper(
    decorator_fn: Callable,
    should_skip: Callable[[tuple, dict], bool] | None = None,
    **decorator_kwargs,
) -> Callable[[Callable], Callable]:
    """Create a wrapper function that applies a decorator conditionally.

    Args:
        decorator_fn: The decorator to apply (e.g., prefect.task)
        should_skip: Optional function to determine if decoration should be skipped
        **decorator_kwargs: Keyword arguments to pass to the decorator

    Returns:
        A wrapper function suitable for use with MonkeyPatch
    """

    def wrapper_factory(original_method: Callable) -> Callable:
        # Check if original method is async
        import inspect

        is_async = inspect.iscoroutinefunction(original_method)

        if is_async:

            @wraps(original_method)
            async def async_wrapper(*args, **kwargs):
                # Check if we should skip decoration
                if should_skip and should_skip(args, kwargs):
                    return await original_method(*args, **kwargs)

                # Apply the decorator
                decorated = decorator_fn(**decorator_kwargs)(original_method)
                result = decorated(*args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result

            return async_wrapper
        else:

            @wraps(original_method)
            def sync_wrapper(*args, **kwargs):
                # Check if we should skip decoration
                if should_skip and should_skip(args, kwargs):
                    return original_method(*args, **kwargs)

                # Apply the decorator
                decorated = decorator_fn(**decorator_kwargs)(original_method)
                return decorated(*args, **kwargs)

            return sync_wrapper

    return wrapper_factory
