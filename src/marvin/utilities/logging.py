import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from rich.logging import RichHandler

import marvin


def maybe_quote(value: Any) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


@lru_cache
def get_logger(name: str | None = None) -> logging.Logger:
    """Retrieves a logger with the given name, or the root logger if no name is given.

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


# Prevent circular import
if TYPE_CHECKING:
    import marvin.settings


def setup_logging(settings: "marvin.settings.Settings") -> None:
    logger = get_logger()

    # Set level from settings
    logger.setLevel(settings.log_level)

    # Clear existing handlers to avoid duplicates if called multiple times
    logger.handlers.clear()

    # --- Setup Console Handler (Rich) ---
    handler = RichHandler(rich_tracebacks=True, markup=False)
    formatter = logging.Formatter("%(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # --- Setup File Handler (optional) ---
    if settings.log_file:
        log_file_path = settings.log_file.expanduser().resolve()
        # Ensure the directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        # Set the file handler level to match the main logger level
        file_handler.setLevel(settings.log_level)
        logger.addHandler(file_handler)

        # Ensure the specific MCP logger also writes to the file
        mcp_integration_logger = get_logger("marvin._internal.integrations.mcp")
        # Check if handler already exists on this specific logger
        if not any(h is file_handler for h in mcp_integration_logger.handlers):
            mcp_integration_logger.addHandler(file_handler)
        mcp_integration_logger.setLevel(
            settings.log_level
        )  # Ensure it respects the global level
        mcp_integration_logger.propagate = (
            False  # Prevent duplicate logs if root also logs
        )

    logger.propagate = False
