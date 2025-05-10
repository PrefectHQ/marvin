import inspect
from contextlib import ContextDecorator
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

try:
    from prefect import Task
    from prefect import tags as prefect_tags
    from prefect.artifacts import acreate_markdown_artifact
    from prefect.cache_policies import INPUTS
    from prefect.context import get_run_context
    from pydantic_ai.tools import Tool
except ImportError:
    raise ImportError(
        "To use the Prefect integration, install `marvin[prefect]`."
    ) from None


from marvin import Agent

T = TypeVar("T")
P = ParamSpec("P")


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
        """Patch the method on the class and all subclasses with the decorator."""
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

    def _patch_method(
        self,
        cls: type,
        method_name: str,
        decorator: Callable[..., Callable[..., T]],
    ):
        """Patch a method on a class with a given decorator."""
        original_method = getattr(cls, method_name)
        modified_method = decorator(original_method, **self.decorator_kwargs)
        setattr(cls, method_name, modified_method)
        self.patched_methods.append((cls, method_name, original_method))


def _prefect_task_wrapped_tool_call(
    func: Callable[P, T],
    tags: set | None = None,
    settings: dict[str, Any] | None = None,
) -> Callable[..., Callable[P, T]]:
    """Decorator for wrapping a function with a prefect decorator."""
    tags = tags or set()
    settings = settings or {}

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        tool_self = args[0]
        assert isinstance(tool_self, Tool), "expected a `pydantic_ai.tools.Tool`"
        with prefect_tags(*tags):
            fn = (
                Task(func, **settings)
                if not isinstance(func, Task)
                else func.with_options(**settings)
            )

            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            if get_run_context():
                tool_name = getattr(tool_self, "name", None) or getattr(
                    tool_self, "__name__", "unknown-tool"
                )
                tool_return_content = (
                    getattr(result, "content")
                    if hasattr(result, "content")
                    else result
                    if isinstance(result, str)
                    else str(result)
                )
                await acreate_markdown_artifact(
                    key=f"{tool_name.replace('_', '-')}-result",
                    markdown=f"# `{tool_name}`\u00a0returned\n\n```python\n{tool_return_content!r}\n```",
                    description=f"tool call result from {tool_name!r}",
                )

            return result  # type: ignore

    return wrapper  # type: ignore


class WatchToolCallsAsPrefectTasks(DecorateMethodContext):
    """Context decorator for patching a method with a prefect flow."""

    def __init__(
        self,
        patch_cls: type = Tool,
        patch_method_name: str = "run",
        settings: dict[str, Any] | None = None,
        tags: set[str] | None = None,
    ):
        """Initialize the context manager.
        Args:
            patch_cls: The class to patch. Defaults to `pydantic_ai.tools.Tool`.
            patch_method_name: The name of the method to patch. Defaults to `pydantic_ai.tools.Tool.run`.
            settings: Options to apply to the Prefect task. See docs for [configuring tasks](https://docs.prefect.io/v3/develop/write-tasks#task-configuration)
            tags: Prefect tags to apply to the task
        """

        if not settings:
            settings = {}

        if not settings.get("cache_policy"):
            settings["cache_policy"] = INPUTS - "run_context"

        if not settings.get("task_run_name"):
            settings["task_run_name"] = "{self.function.__name__}"

        super().__init__(
            patch_cls=patch_cls,
            patch_method_name=patch_method_name,
            decorator=_prefect_task_wrapped_tool_call,
            tags=tags,
            settings=settings,
        )


class PrefectAgent(Agent):
    """An agent whose actions are instrumented with Prefect decorators."""

    def __init__(self, *args: Any, **kwargs: Any):
        self.prefect_task_options = kwargs.pop("prefect_task_options", {})
        super().__init__(*args, **kwargs)

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the agent."""
        with WatchToolCallsAsPrefectTasks(settings=self.prefect_task_options):
            return super().run(*args, **kwargs)

    async def run_async(self, *args: Any, **kwargs: Any) -> Any:
        """Run the agent asynchronously."""
        with WatchToolCallsAsPrefectTasks(settings=self.prefect_task_options):
            return await super().run_async(*args, **kwargs)
