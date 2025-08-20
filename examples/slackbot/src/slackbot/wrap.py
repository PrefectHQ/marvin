"""Clean wrapper for monitoring pydantic-ai tool calls with Prefect.

This module provides a clean separation between:
1. Generic monkey-patching (handled by _internal.monkey_patch)
2. Tool tracking (handled by _internal.tool_tracking)
3. Prefect-specific integration (this module)
"""

import inspect

# Add a context variable to track if we're already in a wrapped call
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable

from prefect import task

from ._internal.monkey_patch import MonkeyPatch
from ._internal.tool_tracking import ToolUsageTracker

# Export the context variables for backward compatibility
from ._internal.tool_tracking import current_tool as _current_tool
from ._internal.tool_tracking import progress_message as _progress_message
from ._internal.tool_tracking import tool_usage_counts as _tool_usage_counts

_in_wrapped_call: ContextVar[bool] = ContextVar("_in_wrapped_call", default=False)


def create_prefect_tool_wrapper(
    tracker: ToolUsageTracker,
    task_settings: dict[str, Any] | None = None,
) -> Callable[[Callable], Callable]:
    """Create a wrapper that integrates tool tracking with Prefect tasks.

    Args:
        tracker: Tool usage tracker instance
        task_settings: Settings to pass to prefect.task decorator

    Returns:
        A wrapper function that decorates methods with Prefect tasks and tracking
    """
    task_settings = task_settings or {}

    def wrapper_factory(original_method: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(original_method)

        if is_async:

            @wraps(original_method)
            async def async_wrapper(*args, **kwargs):
                # Check if we're already in a wrapped call to avoid double-wrapping
                if _in_wrapped_call.get():
                    # Already wrapped, just call the original
                    return await original_method(*args, **kwargs)

                # Extract tool information from pydantic-ai's call_tool signature
                # Signature: self, name, tool_args, ctx, tool
                tool_name = kwargs.get("name", "Unknown Tool")
                if not tool_name or tool_name == "Unknown Tool":
                    if len(args) > 1:
                        tool_name = args[1]

                # Check for internal tools that should skip Prefect wrapping
                tool = kwargs.get("tool") or (args[4] if len(args) > 4 else None)
                is_internal = (
                    tool
                    and hasattr(tool, "tool_def")
                    and hasattr(tool.tool_def, "kind")
                    and tool.tool_def.kind == "output"
                )

                if is_internal:
                    # Skip all decoration for internal tools
                    return await original_method(*args, **kwargs)

                # Track the tool call
                limit_msg = tracker.track_call(tool_name)
                if limit_msg:
                    return limit_msg

                # Update progress if available
                await tracker.update_progress(tool_name)

                # Build dynamic settings for this specific call
                dynamic_settings = dict(task_settings)
                if (
                    "task_run_name" in dynamic_settings
                    and "{tool_name}" in dynamic_settings["task_run_name"]
                ):
                    dynamic_settings["task_run_name"] = dynamic_settings[
                        "task_run_name"
                    ].format(tool_name=tool_name)

                # Set context variable to prevent double-wrapping
                token = _in_wrapped_call.set(True)
                try:
                    # Create task-decorated function inline
                    task_fn = task(**dynamic_settings)(original_method)
                    return await task_fn(*args, **kwargs)
                finally:
                    _in_wrapped_call.reset(token)

            return async_wrapper
        else:
            # For sync methods (shouldn't happen with pydantic-ai but for completeness)
            @wraps(original_method)
            def sync_wrapper(*args, **kwargs):
                tool_name = kwargs.get("name", "Unknown Tool")
                if not tool_name or tool_name == "Unknown Tool":
                    if len(args) > 1:
                        tool_name = args[1]

                limit_msg = tracker.track_call(tool_name)
                if limit_msg:
                    return limit_msg

                dynamic_settings = dict(task_settings)
                if (
                    "task_run_name" in dynamic_settings
                    and "{tool_name}" in dynamic_settings["task_run_name"]
                ):
                    dynamic_settings["task_run_name"] = dynamic_settings[
                        "task_run_name"
                    ].format(tool_name=tool_name)

                task_fn = task(**dynamic_settings)(original_method)
                return task_fn(*args, **kwargs)

            return sync_wrapper

    return wrapper_factory


class WatchToolCalls:
    """Context manager for monitoring pydantic-ai tool calls with Prefect.

    This integrates:
    - Monkey patching (via MonkeyPatch)
    - Tool tracking (via ToolUsageTracker)
    - Prefect tasks (via create_prefect_tool_wrapper)
    """

    def __init__(
        self,
        max_tool_calls: int = 50,
        settings: dict[str, Any] | None = None,
    ):
        """Initialize the tool call watcher.

        Args:
            max_tool_calls: Maximum number of tool calls allowed
            settings: Settings to pass to Prefect task decorator
        """
        self.tracker = ToolUsageTracker(max_calls=max_tool_calls)
        self.settings = settings or {}
        self.monkey_patch = None

    def __enter__(self):
        """Start watching tool calls."""
        # Import here to avoid circular dependency
        from pydantic_ai.toolsets.abstract import AbstractToolset

        # Create the wrapper with our tracker
        wrapper = create_prefect_tool_wrapper(
            tracker=self.tracker,
            task_settings=self.settings,
        )

        # Apply the monkey patch
        self.monkey_patch = MonkeyPatch(
            target_cls=AbstractToolset,
            method_name="call_tool",
            wrapper_fn=wrapper,
        )
        self.monkey_patch.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop watching tool calls."""
        if self.monkey_patch:
            self.monkey_patch.__exit__(exc_type, exc_val, exc_tb)


__all__ = ["WatchToolCalls", "_progress_message", "_tool_usage_counts", "_current_tool"]
