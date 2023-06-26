import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from typer import Typer

P = ParamSpec("P")
R = TypeVar("R")

# Comment from GitHub issue: https://github.com/tiangolo/typer/issues/88
# User: https://github.com/macintacos

class AsyncTyper(Typer):
    """Asyncronous Typer that derives from Typer.

    Use this when you have an asynchronous command you want to build, otherwise, just use Typer.
    """

    def acommand(  # type: ignore # Because we're being generic in this decorator, 'Any' is fine for the args.
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[
        [Callable[P, Coroutine[Any, Any, R]]],
        Callable[P, Coroutine[Any, Any, R]],
    ]:
        """An async decorator for Typer commands that are asynchronous."""

        def decorator(  # type: ignore # Because we're being generic in this decorator, 'Any' is fine for the args.
            async_func: Callable[P, Coroutine[Any, Any, R]],
        ) -> Callable[P, Coroutine[Any, Any, R]]:
            @wraps(async_func)
            def sync_func(*_args: P.args, **_kwargs: P.kwargs) -> R:
                return asyncio.run(async_func(*_args, **_kwargs))

            # Now use app.command as normal to register the synchronous function
            self.command(*args, **kwargs)(sync_func)

            # We return the async function unmodified, so its library functionality is preserved.
            return async_func

        return decorator