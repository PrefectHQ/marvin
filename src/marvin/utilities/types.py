import asyncio
import enum
import inspect
import textwrap
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    List,
    Literal,
    Optional,
    TypeVar,
    get_args,
    get_origin,
)

from marvin.utilities.jinja import prompt_env

T = TypeVar("T")


def create_enum(values: list[Any], name: str = "Labels") -> type[enum.Enum]:
    """Create an Enum from a list of values.
    The enum names will be LABEL_<index> (e.g., LABEL_0, LABEL_1, LABEL_2)
    and the values will be the original objects."""
    return enum.Enum(name, {f"LABEL_{i}": v for i, v in enumerate(values)})


def is_classifier(typ) -> bool:
    """Check if a type represents a classification task.
    This includes both single-label (Enum/Literal) and multi-label (list[Enum/Literal]) classification."""
    origin = get_origin(typ)
    if origin is list:
        # Check if it's list[Enum] or list[Literal]
        arg = get_args(typ)[0]
        return (isinstance(arg, type) and issubclass(arg, enum.Enum)) or get_origin(
            arg
        ) is Literal
    return (isinstance(typ, type) and issubclass(typ, enum.Enum)) or get_origin(
        typ
    ) is Literal


def get_labels(typ) -> Optional[tuple[Any, ...]]:
    """Get the label values from a classification type.
    Works with both Enum/Literal and list[Enum/Literal] types."""
    origin = get_origin(typ)
    if origin is list:
        # Get labels from list[Enum/Literal]
        arg = get_args(typ)[0]
        if isinstance(arg, type) and issubclass(arg, enum.Enum):
            return tuple(v.value for v in arg)
        elif get_origin(arg) is Literal:
            return get_args(arg)
    elif isinstance(typ, type) and issubclass(typ, enum.Enum):
        return tuple(v.value for v in typ)
    elif origin is Literal:
        return get_args(typ)
    return None


def get_indexed_labels(typ) -> dict[int, Any]:
    """Get the indexed labels and string representations from a classification type."""
    labels = get_labels(typ)

    return {i: str(v) for i, v in enumerate(labels)}


def get_classifier_type(typ) -> type:
    """Get the type that should be used for validation of a classifier.
    Returns int for Enum/Literal and list[int] for list[Enum/Literal]."""
    origin = get_origin(typ)
    if origin is list:
        return list[int]
    return int


class AutoDataClass:
    """
    Base class for automatically applying `@dataclass` to subclasses with configurable behavior.

    Subclasses can define their dataclass configuration by setting the `_dataclass_config`
    attribute directly. The configuration is applied during class creation.

    Attributes:
        _dataclass_config (dict): Configuration options passed to the
            `dataclass` decorator, for example `{"kw_only": True}`.

    Example:
        >>> from dataclasses import asdict
        >>> class Base(AutoDataClass):
        ...     common_field: str
        ...
        >>> class Derived(Base):
        ...     _dataclass_config = {"kw_only": True}
        ...     specific_field: int
        ...
        >>> obj = Derived(common_field="example", specific_field=42)
        >>> asdict(obj)
        {'common_field': 'example', 'specific_field': 42}
    """

    _dataclass_config = {}

    def __init_subclass__(cls, **kwargs):
        """
        Initialize subclass with inherited dataclass configuration.

        Merges parent class _dataclass_config with subclass-specific config.
        Subclass config takes precedence over parent config.
        """
        super().__init_subclass__(**kwargs)
        parent_config = {}
        for base in reversed(cls.__mro__[1:]):  # reverse to respect MRO
            if hasattr(base, "_dataclass_config"):
                parent_config.update(base._dataclass_config)

        # Create new dict to avoid modifying parent's config
        if not hasattr(cls, "_dataclass_config"):
            cls._dataclass_config = {}
        cls._dataclass_config = {**parent_config, **cls._dataclass_config}

        # Apply dataclass decorator with merged config
        return dataclass(cls, **cls._dataclass_config)


@dataclass
class ParameterModel:
    name: str
    annotation: Optional[str]
    default: Optional[str]


@dataclass
class PythonFunction:
    """
    A dataclass representing a Python function.

    Attributes:
        function (Callable): The original function object.
        signature (inspect.Signature): The signature object of the function.
        name (str): The name of the function.
        docstring (Optional[str]): The docstring of the function.
        parameters (List[ParameterModel]): The parameters of the function.
        return_annotation (Optional[Any]): The return annotation of the function.
        source_code (str): The source code of the function.
        bound_parameters (dict[str, Any]): The parameters of the function bound with values.
        return_value (Optional[Any]): The return value of the function call.
    """

    function: Callable
    signature: inspect.Signature
    name: str
    parameters: List[ParameterModel]
    docstring: Optional[str] = None
    return_annotation: Optional[Any] = None
    source_code: Optional[str] = None
    bound_parameters: dict[str, Any] = field(default_factory=dict)
    return_value: Optional[Any] = None

    @property
    def definition(self) -> str:
        docstring = inspect.cleandoc(self.docstring) if self.docstring else ""
        formatted_docstring = textwrap.indent(
            f'"""\n{docstring}\n"""' if docstring else "",
            prefix="    ",
        )
        return f"def {self.name}{self.signature}:\n{formatted_docstring}".strip()

    @classmethod
    def from_function(cls, func: Callable, **kwargs) -> "PythonFunction":
        """
        Create a PythonFunction instance from a function.

        Args:
            func (Callable): The function to create a PythonFunction instance from.
            **kwargs: Additional keyword arguments to set as attributes on the PythonFunction instance.

        Returns:
            PythonFunction: The created PythonFunction instance.
        """
        name = kwargs.pop("name", func.__name__)
        docstring = kwargs.pop("docstring", func.__doc__)
        sig = inspect.signature(func)
        parameters = [
            ParameterModel(
                name=name,
                annotation=(
                    str(param.annotation)
                    if param.annotation is not param.empty
                    else None
                ),
                default=(
                    repr(param.default) if param.default is not param.empty else None
                ),
            )
            for name, param in sig.parameters.items()
        ]

        try:
            source_code = inspect.getsource(func).strip()
        except OSError as e:
            error_message = str(e)
            if "source code" in error_message:
                source_code = None
            else:
                raise

        function_dict = {
            "function": func,
            "signature": sig,
            "name": name,
            "docstring": inspect.cleandoc(docstring) if docstring else None,
            "parameters": parameters,
            "return_annotation": sig.return_annotation,
            "source_code": source_code,
        }

        function_dict.update(kwargs)

        return cls(**function_dict)

    @classmethod
    def from_function_call(cls, func: Callable, *args, **kwargs) -> "PythonFunction":
        """
        Create a PythonFunction instance from a function call.

        Args:
            func (Callable): The function to call.
            *args: Positional arguments to pass to the function call.
            **kwargs: Keyword arguments to pass to the function call.

        Returns:
            PythonFunction: The created PythonFunction instance, with the return value of the function call set as an attribute.
        """
        sig = inspect.signature(func)

        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        return_value = func(*bound.args, **bound.kwargs)
        if inspect.iscoroutine(return_value):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return_value = asyncio.create_task(return_value)
            else:
                return_value = loop.run_until_complete(return_value)

        # render the docstring with the bound arguments, if it was supplied as jinja
        docstring = prompt_env.from_string(func.__doc__ or "").render(
            **dict(bound.arguments.items())
        )

        instance = cls.from_function(
            func,
            docstring=docstring,
            bound_parameters={k: v for k, v in bound.arguments.items()},
            return_value=return_value,
        )

        return instance


@dataclass
class Labels:
    """A helper class for creating classification labels.

    Args:
        values: list[Any]
        many: bool = False

    Example:
        >>> Task(result_type=Labels(['a', 'b']))  # single-label classification
        >>> Task(result_type=Labels(['a', 'b'], many=True))  # multi-label classification
    """

    values: list[Any]
    many: bool = False
