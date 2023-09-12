"""
Pydantic Utilities for Marvin Framework
=======================================

This module provides utility functions and classes for integrating Pydantic
within the Marvin framework. The primary focus is on:

- Providing a base model for Marvin with configuration adjustments.
- Offering a mixin for easy logging integration in models.
- Converting Python functions into Pydantic models and OpenAPI schemas.
- Supporting type conversions and inspections for Pydantic and OpenAPI 
  integration.

Use cases include API documentation, data validation, and runtime type inspections.
"""

import inspect
import logging
from types import GenericAlias
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from pydantic import BaseModel, PrivateAttr, create_model

from marvin.utilities.logging import get_logger


class MarvinBaseModel(BaseModel):
    """
    Base model for Marvin, configured to forbid any extra attributes
    during model instantiation.
    """

    class Config:
        extra = "forbid"


class LoggerMixin(BaseModel):
    """
    A mixin for Pydantic's BaseModel that integrates logging.

    Provides a logger instance, easing logging within models and methods.

    Attributes:
    - _logger: The logger instance, set during instantiation.
    """

    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._logger = get_logger(type(self).__name__)

    @property
    def logger(self) -> logging.Logger:
        """Returns the logger instance associated with the model."""
        return self._logger


def create_model_from_function(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Type[BaseModel]:
    """
    Convert a function's signature into a Pydantic model.

    This function creates a Pydantic model whose fields correspond to the function's
    parameters. All parameters must have type annotations.

    Args:
    - function (Callable): The target function to convert.
    - name (Optional[str]): A custom name for the generated model.
                            Defaults to the function's name.

    Returns:
    - Type[BaseModel]: The generated Pydantic model.

    Raises:
    - ValueError: If any parameter lacks a type annotation or encounters
                  a Pydantic-related error.
    """
    signature = inspect.signature(function)
    fields = {
        param_name: (
            param.annotation,
            param.default if param.default != param.empty else ...,
        )
        for param_name, param in signature.parameters.items()
        if param_name != getattr(function, "__self__", None)
    }

    try:
        return create_model(name or function.__name__, **fields)  # type: ignore
    except RuntimeError as exc:
        if "see `arbitrary_types_allowed` " in str(exc):
            raise ValueError(
                f"Error creating model for {function.__name__} with signature {signature}: {exc}"  # noqa: E501
            ) from exc
        else:
            raise


def function_to_openapi_schema(
    function: Callable[..., Any],
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert a function's signature into an OpenAPI schema.

    Args:
    - function (Callable): The target function to convert.
    - name (Optional[str]): A custom name for the generated schema.
                            Defaults to the function's name.

    Returns:
    - Dict[str, Any]: The OpenAPI schema representation.
    """
    Model = create_model_from_function(function, name=name, description=description)
    return Model.schema()


def safe_issubclass(
    type_: Type[Any], classes: Union[Type[Any], Tuple[Type[Any], ...]]
) -> bool:
    """
    Safely determine if a type is a subclass of one or multiple classes.

    This function is a safe version of the built-in `issubclass` function. It doesn't
    raise a TypeError if the first argument is not a class.

    Args:
    - type_ (Type[Any]): The type to inspect.
    - classes (Union[Type[Any], Tuple[Type[Any], ...]]): The class or tuple of classes
                                                        to check against.

    Returns:
    - bool: True if `type_` is a subclass of any entry in `classes`, False otherwise.
    """
    if isinstance(type_, type) and not isinstance(type_, GenericAlias):
        return issubclass(type_, classes)
    return False


def contains_type_in_genericalias(
    genericalias: Union[Type[Any], GenericAlias],
    target_types: Union[Type[Any], Tuple[Type[Any], ...]],
) -> bool:
    """
    Determine whether a type or generic alias contains a target type or types.

    This function is useful for checking if a type contains a specific subtype,
    like a Pydantic model within a more complex type.

    Args:
    - genericalias (Union[Type[Any], GenericAlias]): The main type or generic to inspect
    - target_types (Union[Type[Any], Tuple[Type[Any], ...]]): The target type/s to check

    Returns:
    - bool: True if the target type(s) is found within the main type, False otherwise.
    """
    if isinstance(target_types, tuple):
        return any(contains_type_in_genericalias(genericalias, t) for t in target_types)

    if isinstance(genericalias, GenericAlias):
        if safe_issubclass(genericalias.__origin__, target_types):
            return True
        return any(
            contains_type_in_genericalias(arg, target_types)
            for arg in genericalias.__args__
        )

    return safe_issubclass(genericalias, target_types)


# ------------------
# Deprecated aliases
# ------------------
function_to_schema = function_to_openapi_schema
genericalias_contains = contains_type_in_genericalias
function_to_model = create_model_from_function
