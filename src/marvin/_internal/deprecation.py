"""
Deprecation utilities for Marvin.

Based on Prefect's deprecation patterns but simplified for Marvin's needs.
"""

import functools
import warnings
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


class MarvinDeprecationWarning(DeprecationWarning):
    """A Marvin-specific deprecation warning."""


def generate_deprecation_message(
    name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    help: str = "",
) -> str:
    """Generate a deprecation warning message."""
    if start_date is None and end_date is None:
        # Default to 1 month from now
        end_date = datetime.now() + timedelta(days=30)
    elif start_date and not end_date:
        # Calculate end date as 1 month after start
        end_date = start_date + timedelta(days=30)

    end_date_str = end_date.strftime("%b %Y") if end_date else "unknown"

    message = (
        f"{name} is deprecated and will be removed after {end_date_str}. {help}"
    ).strip()

    return message


def deprecated_class(
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    stacklevel: int = 2,
    help: str = "",
) -> Callable[[type[T]], type[T]]:
    """
    Decorator to mark a class as deprecated.

    Example:
        @deprecated_class(
            start_date=datetime(2025, 1, 1),
            help="Use Agent directly instead."
        )
        class OldClass:
            pass
    """

    def decorator(cls: type[T]) -> type[T]:
        message = generate_deprecation_message(
            name=f"{cls.__module__}.{cls.__name__}",
            start_date=start_date,
            end_date=end_date,
            help=help,
        )

        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self: T, *args: Any, **kwargs: Any) -> None:
            warnings.warn(message, MarvinDeprecationWarning, stacklevel=stacklevel)
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator


def deprecated_callable(
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    stacklevel: int = 2,
    help: str = "",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to mark a function as deprecated.

    Example:
        @deprecated_callable(
            start_date=datetime(2025, 1, 1),
            help="Use new_function() instead."
        )
        def old_function():
            pass
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        message = generate_deprecation_message(
            name=f"{fn.__module__}.{fn.__name__}",
            start_date=start_date,
            end_date=end_date,
            help=help,
        )

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            warnings.warn(message, MarvinDeprecationWarning, stacklevel=stacklevel)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
