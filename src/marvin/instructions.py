from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator, List

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

# Global context var for current instructions
current_instructions: ContextVar[List[str]] = ContextVar(
    "current_instructions", default=[]
)


@contextmanager
def instructions(instruction: str) -> Generator[list[str], None, None]:
    """
    Temporarily add instructions to the current instruction stack. The
    instruction is removed when the context is exited.

    with instructions("talk like a pirate"):
        ...
    """
    if not instruction:
        yield
        return

    stack = current_instructions.get()
    token = current_instructions.set(stack + [instruction])
    try:
        yield
    finally:
        current_instructions.reset(token)


def get_instructions() -> List[str]:
    """
    Get the current instruction stack.
    """
    return current_instructions.get()
