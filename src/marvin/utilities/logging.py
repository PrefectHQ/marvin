import logging
from functools import lru_cache
from typing import Optional

import marvin


@lru_cache()
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retrieves a logger with the given name, or the root logger if no name is given.

    Args:
        name: The name of the logger to retrieve.

    Returns:
        The logger with the given name, or the root logger if no name is given.

    Example:
        Basic Usage of `get_logger`
        ```python
        from marvin.utilities.logging import get_logger

        logger = get_logger("marvin.test")
        logger.info("This is a test") # Output: marvin.test: This is a test

        debug_logger = get_logger("marvin.debug")
        debug_logger.debug_kv("TITLE", "log message", "green")
        ```
    """
    parent_logger = logging.getLogger("marvin")

    if name:
        # Append the name if given but allow explicit full names e.g. "marvin.test"
        # should not become "marvin.marvin.test"
        if not name.startswith(parent_logger.name + "."):
            logger = parent_logger.getChild(name)
        else:
            logger = logging.getLogger(name)
    else:
        logger = parent_logger

    return logger


def setup_logging(level: Optional[str] = None) -> None:
    logger = get_logger()

    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(marvin.settings.log_level)
