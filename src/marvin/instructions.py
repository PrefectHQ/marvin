from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

# Global context var for current instructions
_current_instructions: ContextVar[list[str]] = ContextVar(
    "current_instructions",
    default=[],
)


@contextmanager
def instructions(instruction: str) -> Generator[None, None, None]:
    """Temporarily add instructions to the current instruction stack. The
    instruction is removed when the context is exited.

    with instructions("talk like a pirate"):
        ...
    """
    if not instruction:
        yield
        return

    stack = _current_instructions.get()
    token = _current_instructions.set(stack + [instruction])
    try:
        yield
    finally:
        _current_instructions.reset(token)


def get_instructions() -> list[str]:
    """Get the current instruction stack."""
    return _current_instructions.get()
