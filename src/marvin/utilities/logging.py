"""
Logging Utilities for Marvin Library
====================================

This module provides utilities for configuring and enhancing logging in the Marvin 
library. It leverages the `rich` library to produce styled logs, and offers the ability 
to easily create custom-styled log messages.

Main Features:
--------------
1. `get_logger`: Retrieves a logger instance, allowing for child loggers.
2. `setup_logging`: Configures logging, including level and handlers.
3. `add_logging_methods`: Enhances a logger instance with custom-styled logging methods.

Usage:
------
    logger = get_logger("my_logger")
    logger.info("This is an info log")
    logger.info_style("This is a styled info log", style="bold red")
    logger.info_kv("key", "value", key_style="green", value_style="blue")

Note:
-----
This module assumes that the `marvin` library is properly installed and available in the
PYTHONPATH, as it references `marvin.settings` for default settings.
"""

import logging
from functools import lru_cache, partial
from typing import Any, Optional

from rich.logging import RichHandler
from rich.markup import escape

import marvin


@lru_cache()
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retrieve a logger instance.

    If a name is provided, it fetches/creates a child logger of "marvin" with the given name.
    Otherwise, it returns the parent logger "marvin".

    Args:
    - name (Optional[str]): Name of the child logger. If None, the parent logger "marvin" is returned.

    Returns:
    - logging.Logger: The logger instance.
    """  # noqa: E501

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

    add_logging_methods(logger)
    return logger


def setup_logging(level: Optional[int] = None) -> None:
    """
    Set up logging for the Marvin library.

    This configures the logger with a rich handler for styled logs. If no level is provided,
    the default logging level from `marvin.settings.log_level` is used.

    Args:
    - level (Optional[int]): Desired logging level. If None, uses default from marvin settings.

    Returns:
    - None
    """  # noqa: E501

    logger = get_logger()

    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(marvin.settings.log_level)

    if not any(isinstance(h, RichHandler) for h in logger.handlers):
        handler = RichHandler(rich_tracebacks=True, markup=False)
        formatter = logging.Formatter("%(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def add_logging_methods(logger: logging.Logger) -> None:
    """
    Enhance the logger with custom-styled logging methods.

    This adds methods like `info_style` and `info_kv` to the logger instance, allowing
    for easy styled and key-value logging.

    Args:
    - logger (logging.Logger): Logger instance to be enhanced.

    Returns:
    - None
    """

    def log_style(
        level: int, message: str, style: Optional[str] = "default on default"
    ) -> None:
        """
        Log a message with a specific style.

        Args:
        - level (int): Logging level (e.g., logging.INFO).
        - message (str): Message to log.
        - style (str, optional): Style string for the `rich` library. Defaults to "default on default".

        Returns:
        - None
        """  # noqa: E501
        styled_message = f"[{style}]{escape(message)}[/]"
        logger.log(level, styled_message, extra={"markup": True})

    def log_kv(
        level: int,
        key: str,
        value: Any,
        key_style: str = "default on default",
        value_style: str = "default on default",
        delimiter: str = ": ",
    ) -> None:
        """
        Log a key-value pair with specific styles for each.

        Args:
        - level (int): Logging level (e.g., logging.INFO).
        - key (str): Key string.
        - value (Any): Value to log.
        - key_style (str, optional): Style for the key. Defaults to "default on default".
        - value_style (str, optional): Style for the value. Defaults to "default on default".
        - delimiter (str, optional): Delimiter between key and value. Defaults to ": ".

        Returns:
        - None
        """  # noqa: E501
        kv_message = (
            f"[{key_style}]{escape(key)}{delimiter}[/]"
            f"[{value_style}]{escape(str(value))}[/]"
        )
        logger.log(level, kv_message, extra={"markup": True})

        levels = [
            (logging.DEBUG, "debug"),
            (logging.INFO, "info"),
            (logging.WARNING, "warning"),
            (logging.ERROR, "error"),
            (logging.CRITICAL, "critical"),
        ]

        for level, name in levels:
            setattr(logger, name, partial(logger.log, level))
            setattr(logger, f"{name}_style", partial(log_style, level))
            setattr(logger, f"{name}_kv", partial(log_kv, level))
