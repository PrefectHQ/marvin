import inspect
from collections import defaultdict
from contextlib import ContextDecorator
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, TypeVar

from prefect import tags as prefect_tags
from prefect import task

T = TypeVar("T")

_progress_message: ContextVar[Any] = ContextVar("progress_message", default=None)
_tool_usage_counts: ContextVar[dict[str, int] | None] = ContextVar(
    "tool_usage_counts", default=None
)
_current_tool: ContextVar[str | None] = ContextVar("current_tool", default=None)


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
    max_tool_calls: int = 10,  # Default limit per agent run (matches settings)
) -> Callable[..., Callable[..., T]]:
    """Decorator for wrapping a function with a prefect decorator."""
    tags = tags or set[str]()

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        # For call_tool method signature: self, name, tool_args, ctx, tool
        # Check if this is an internal/output tool and skip wrapping entirely
        tool = kwargs.get("tool") or (args[4] if len(args) > 4 else None)
        is_internal_tool = (
            tool
            and hasattr(tool, "tool_def")
            and hasattr(tool.tool_def, "kind")
            and tool.tool_def.kind == "output"
        )

        # Skip Prefect wrapping entirely for internal tools like final_result
        if is_internal_tool:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

        # Get tool name for tracking
        tool_name = kwargs.get("name", "Unknown Tool")
        if not tool_name or tool_name == "Unknown Tool":
            if len(args) > 1:
                tool_name = args[1]

        # Always track and enforce tool usage limits
        counts = _tool_usage_counts.get()
        if counts is None:
            counts = defaultdict(int)
            _tool_usage_counts.set(counts)
        counts[tool_name] += 1

        # Check if we've exceeded the limit
        total_calls = sum(counts.values())
        if total_calls > max_tool_calls:
            # Return a message that tells the agent to stop using tools and continue
            # This will be returned as the tool result, which the agent will see
            return "Tool use limit reached. Please continue with the information you've gathered so far to answer the user's question."

        _current_tool_token = None
        if _progress := _progress_message.get():
            # Set current tool for progress tracking
            _current_tool_token = _current_tool.set(tool_name)

            try:
                # Build the progress message with better formatting
                lines = []
                lines.append(f"🔧 Using: `{tool_name}`")
                lines.append("")  # Empty line for spacing

                # Build summary of all tools used
                if counts:
                    lines.append("📊 Tools used:")
                    for tool, count in sorted(counts.items()):
                        lines.append(f"  • `{tool}` ({count}x)")

                full_message = "\n".join(lines)
                await _progress.update(full_message)
            except Exception:
                pass

        try:
            # Update task_run_name with actual tool name if present
            dynamic_settings = dict(settings or {})
            if (
                "task_run_name" in dynamic_settings
                and "{tool_name}" in dynamic_settings["task_run_name"]
            ):
                # Get tool name for task_run_name formatting
                tool_name = kwargs.get("name", "Unknown Tool")
                if not tool_name or tool_name == "Unknown Tool":
                    if len(args) > 1:
                        tool_name = args[1]
                dynamic_settings["task_run_name"] = dynamic_settings[
                    "task_run_name"
                ].format(tool_name=tool_name)

            wrapped_callable = decorator(**dynamic_settings)(func)
            with prefect_tags(*tags):
                result = wrapped_callable(*args, **kwargs)  # type: ignore
                if inspect.isawaitable(result):
                    result = await result

                return result
        finally:
            if _progress and _current_tool_token is not None:
                _current_tool.reset(_current_tool_token)

    return wrapper  # type: ignore


class WatchToolCalls(DecorateMethodContext):
    """Context decorator for patching a method with a prefect flow."""

    def __init__(
        self,
        patch_cls: type | None = None,
        patch_method_name: str = "call_tool",
        tags: set[str] | None = None,
        settings: dict[str, Any] | None = None,
        max_tool_calls: int = 10,
    ):
        """Initialize the context manager.
        Args:
            tags: Prefect tags to apply to the flow.
            settings: Settings to pass to the decorator.
            max_tool_calls: Maximum number of tool calls allowed per turn.
        """
        # Import here to avoid circular imports
        from pydantic_ai.toolsets.abstract import AbstractToolset

        super().__init__(
            patch_cls=patch_cls or AbstractToolset,
            patch_method_name=patch_method_name,
            decorator=prefect_wrapped_function,
            tags=tags,
            settings=settings,
            max_tool_calls=max_tool_calls,
        )
