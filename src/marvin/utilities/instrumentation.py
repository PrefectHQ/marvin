"""Module for defining Prefect plugins for langchain."""

import inspect
from contextlib import ContextDecorator
from functools import wraps
from typing import Callable, Type, TypeVar

from prefect import Flow, flow
from prefect import tags as prefect_tags

from marvin import Bot

T = TypeVar("T")


class DecorateMethod(ContextDecorator):
    """Context decorator for patching methods with a decorator."""

    def __init__(
        self,
        patch_cls: Type,
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
        self._patch_method(
            cls=self.patch_cls,
            method_name=self.patch_method,
            decorator=self.decorator,
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset methods when exiting the context manager."""
        for cls, method_name, original_method in self.patched_methods:
            setattr(cls, method_name, original_method)

    def _patch_method(self, cls, method_name, decorator):
        """Patch a method on a class with a decorator."""
        original_method = getattr(cls, method_name)
        modified_method = decorator(original_method, **self.decorator_kwargs)
        setattr(cls, method_name, modified_method)
        self.patched_methods.append((cls, method_name, original_method))


def observe_invocation(
    func: Callable[..., T],
    tags: set | None = None,
    flow_kwargs: dict | None = None,
) -> Callable[..., Flow]:
    """Decorator for wrapping a method with a prefect flow."""

    tags = tags or set()

    @wraps(func)
    async def wrapper(*args, **kwargs):
        flow_object = flow(**(flow_kwargs or {}))(func)

        with prefect_tags(*tags):
            result = flow_object(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result

    return wrapper


class WatchBotSay(DecorateMethod):
    """Context decorator for observing `Bot.say` calls as prefect flows."""

    def __init__(
        self,
        patch_cls: Type = Bot,
        patch_method_name: str = "say",
        tags: set | None = None,
        flow_kwargs: dict | None = None,
    ):
        """Initialize the context manager.

        Args:
            tags: Prefect tags to apply to the flow.
            flow_kwargs: Keyword arguments to pass to the flow.
        """
        super().__init__(
            patch_cls=patch_cls,
            patch_method_name=patch_method_name,
            decorator=observe_invocation,
            tags=tags,
            flow_kwargs=flow_kwargs,
        )
