"""
Dynamic Import Utilities
========================

This module provides utility functions to dynamically import modules and classes 
at runtime. Such utilities are particularly useful for frameworks and libraries 
that need to load plugins or components based on configuration strings.

Functions:
- cached_import: Imports a class from a module, with checks for prev. imported modules
- import_string: Given a string path to a module and class, imports and returns it.
"""

import sys
from importlib import import_module


def cached_import(module_path: str, class_name: str) -> type:
    """
    Import and return a class from a module, leveraging cached imports when possible.

    This function checks if the module is already imported; if it is, it returns the
    class directly. Otherwise, it imports the module first and then returns the class.

    Args:
    - module_path (str): The path to the module.
    - class_name (str): The name of the class to import from the module.

    Returns:
    - type: The imported class.

    Raises:
    - AttributeError: If the class isn't found in the module.
    """
    # Check if the module is already imported
    module = sys.modules.get(module_path)
    if (
        not module
        or getattr(module, "__spec__", None)
        and getattr(module.__spec__, "_initializing", False)
    ):  # noqa: E501
        module = import_module(module_path)

    return getattr(module, class_name)


def import_string(dotted_path: str) -> type:
    """
    Import and return a class based on a dotted path string.

    Given a string in the format "module.path.ClassName", this function will import
    "ClassName" from "module.path".

    Args:
    - dotted_path (str): The dotted path to the module and class.

    Returns:
    - type: The imported class.

    Raises:
    - ImportError: If the import fails due to an invalid path or missing class.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError(f"'{dotted_path}' doesn't look like a module path") from err

    try:
        return cached_import(module_path, class_name)
    except AttributeError as err:
        raise ImportError(
            f"Module '{module_path}' does not have a '{class_name}' attribute or class"
        ) from err  # noqa: E501
