import enum
import inspect
import textwrap
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Generic,
    List,
    Literal,
    Optional,
    ParamSpec,
    Sequence,
    TypeAlias,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from marvin.utilities.asyncio import run_sync
from marvin.utilities.jinja import jinja_env

T = TypeVar("T", infer_variance=True)
P = ParamSpec("P")
R = TypeVar("R")

# A type that can be used as a target for type conversion
TargetType: TypeAlias = type[T] | T | Annotated[T, Any]


@dataclass
class Labels:
    """A container for classification labels.

    This class provides a consistent interface for working with labels,
    whether they come from enums, literals, lists, or other sources.

    Args:
        values: The label values. Can be an enum class, a sequence of values,
            or a Literal type.
        many: Whether this is a multi-label classifier (i.e., can select
            multiple values).

    Examples:
        >>> # Single-label classification with raw values
        >>> labels = Labels(["red", "green", "blue"])
        >>> labels.values
        ("red", "green", "blue")

        >>> # Multi-label classification with raw values
        >>> labels = Labels(["red", "green", "blue"], many=True)
        >>> labels.values
        ("red", "green", "blue")

        >>> # Single-label classification with enum
        >>> class Colors(enum.Enum):
        ...     RED = "red"
        ...     GREEN = "green"
        ...     BLUE = "blue"
        >>> labels = Labels(Colors)
        >>> labels.values  # Returns enum members
        (<Colors.RED: 'red'>, <Colors.GREEN: 'green'>, <Colors.BLUE: 'blue'>)

        >>> # Multi-label classification with enum
        >>> labels = Labels(Colors, many=True)
        >>> labels.values  # Returns enum members
        (<Colors.RED: 'red'>, <Colors.GREEN: 'green'>, <Colors.BLUE: 'blue'>)
    """

    values: type[enum.Enum] | Sequence[Any] | Any
    many: bool = False

    def __post_init__(self):
        # Convert values to a tuple of labels
        if issubclass_safe(self.values, enum.Enum):
            self._labels = tuple(self.values)  # Returns enum members
        elif get_origin(self.values) is Literal:
            self._labels = get_args(self.values)
        elif isinstance(self.values, (list, tuple, set)):
            self._labels = tuple(self.values)  # type: ignore
        else:
            raise ValueError(f"Invalid label type: {type(self.values)}")

    @property
    def labels(self) -> tuple[Any, ...]:
        """Get the label values."""
        return self._labels

    def get_type(self) -> type:
        """Get the type that should be used for validation."""
        return list[int] if self.many else int

    def validate(self, value: int | list[int] | None) -> Any | list[Any]:
        """Validate a value against the labels.

        Args:
            value: An integer index or list of integer indices.

        Returns:
            The label value(s) at the given index(es).
            For enum types, returns the enum member(s).
            For other types, returns the raw value(s).

        Raises:
            ValueError: If the value is invalid.
        """
        if value is None:
            raise ValueError("None is not a valid value for classification")

        if self.many:
            if not isinstance(value, (list, tuple)):
                raise ValueError(
                    f"Expected a list of indices for multi-label classification, got {type(value)}"
                )
            if not value:
                raise ValueError(
                    "Empty list is not allowed for multi-label classification"
                )
            if not all(isinstance(i, int) for i in value):  # type: ignore[reportUnnecessaryIsinstance]
                raise ValueError("All elements must be integers")
            if not all(0 <= i < len(self._labels) for i in value):
                raise ValueError(
                    f"All indices must be between 0 and {len(self._labels)-1}"
                )
            if len(set(value)) != len(value):
                raise ValueError("Duplicate indices are not allowed")
            return [self._labels[i] for i in value]
        else:
            if not isinstance(value, int):
                raise ValueError(
                    f"Expected an integer index for classification, got {type(value)}"
                )
            if not (0 <= value < len(self._labels)):
                raise ValueError(
                    f"Invalid index {value}. Must be between 0 and {len(self._labels)-1}"
                )
            return self._labels[value]

    def get_indexed_labels(self) -> dict[int, str]:
        """Get a mapping of indices to label string representations."""

        def format_value(v: Any) -> str:
            if isinstance(v, enum.Enum):
                return repr(v.value)  # Show the enum's value, not its name
            elif isinstance(v, str):
                return f"'{v}'"  # Single quotes for strings
            else:
                return str(v)

        return {i: format_value(v) for i, v in enumerate(self._labels)}


def as_classifier(type_: type[T]) -> Labels:
    """Convert a type to a Labels instance.
    This should only be called on types that have been verified as classifiers via is_classifier().

    Args:
        typ: A type that represents a classifier (Enum, Literal, sequence, or list thereof)

    Returns:
        Labels: A Labels instance representing the classifier

    Raises:
        ValueError: If the type is not a valid classifier
    """
    typ = type_
    if isinstance(typ, Labels):
        return typ

    # Handle list[T] case for type-level classifiers
    origin = get_origin(typ)
    if origin is list:
        arg = get_args(typ)[0]
        # Handle list[Enum] or list[Literal]
        if (isinstance(arg, type) and issubclass(arg, enum.Enum)) or get_origin(
            arg
        ) is Literal:
            return Labels(arg, many=True)

    # Handle double-nested list shorthand
    if (
        isinstance(typ, list)
        and len(typ) == 1
        and isinstance(typ[0], (list, tuple, set))
    ):
        return Labels(typ[0], many=True)  # type: ignore

    # Convert raw sequences to Labels
    if isinstance(typ, (list, tuple, set)):
        return Labels(typ)

    # Handle remaining single-label cases (Enum, Literal)
    return Labels(typ)


def is_classifier(type_: type[T]) -> bool:
    """Check if a type represents a classification task.
    This includes:
    - Single-label: Enum, Literal, or any sequence of values
    - Multi-label: list[Enum], list[Literal], or list[list]

    Examples:
        >>> class Colors(enum.Enum):
        ...     RED = "red"
        ...     GREEN = "green"
        >>> is_classifier(Colors)  # enum
        True
        >>> is_classifier(Literal["a", "b"])  # literal
        True
        >>> is_classifier(["a", "b"])  # list of values
        True
        >>> is_classifier([1, "red", MyClass()])  # mixed values
        True
        >>> is_classifier(list[Colors])  # multi-label enum
        True
        >>> is_classifier(list[Literal["a", "b"]])  # multi-label literal
        True
        >>> is_classifier(list[["a", 1, MyClass()]])  # multi-label shorthand
        True
    """
    typ = type_
    if isinstance(typ, Labels):
        return True

    # Handle list[T] case
    origin = get_origin(typ)
    if origin is list:
        arg = get_args(typ)[0]
        # Check for list[Enum], list[Literal], or list[list]
        return (
            issubclass_safe(arg, enum.Enum)
            or get_origin(arg) is Literal
            or isinstance(arg, (list, tuple, set))
        )

    # Handle single-label cases
    return (
        # Enum type
        issubclass_safe(typ, enum.Enum)
        # Literal type
        or get_origin(typ) is Literal
        # Any sequence of values
        or isinstance(typ, (list, tuple, set))
    )


def issubclass_safe(x: Any, cls: Union[type, tuple[type, ...]]) -> bool:
    """
    Safely check if x is a subclass of cls without raising errors.

    This combines isinstance(x, type) and issubclass(x, cls) checks in a safe way
    that won't raise TypeError if x is not a type.

    Args:
        x: The value to check
        cls: A type or tuple of types to check against

    Returns:
        bool: True if x is a type and is a subclass of cls, False otherwise

    Example:
        >>> issubclass_safe(str, object)  # type is subclass
        True
        >>> issubclass_safe(42, object)  # not a type
        False
        >>> issubclass_safe(str, (int, float))  # not a subclass
        False
    """
    return isinstance(x, type) and issubclass(x, cls)


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

    _dataclass_config: dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs: Any):
        """
        Initialize subclass with inherited dataclass configuration.

        Merges parent class _dataclass_config with subclass-specific config.
        Subclass config takes precedence over parent config.
        """
        super().__init_subclass__(**kwargs)
        parent_config: dict[str, Any] = {}
        for base in reversed(cls.__mro__[1:]):  # reverse to respect MRO
            if hasattr(base, "_dataclass_config"):
                if TYPE_CHECKING:
                    assert issubclass(base, AutoDataClass)
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
class PythonFunction(Generic[P, R]):
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

    function: Callable[P, R]
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
    def from_function(
        cls, func: Callable[P, R], **kwargs: Any
    ) -> "PythonFunction[P, R]":
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

        function_dict: dict[str, Any] = {
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
    def from_function_call(
        cls, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> "PythonFunction[P, R]":
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
            return_value = run_sync(return_value)

        # render the docstring with the bound arguments, if it was supplied as jinja
        docstring = jinja_env.from_string(func.__doc__ or "").render(
            **dict(bound.arguments.items())
        )

        instance = cls.from_function(
            func,
            docstring=docstring,
            bound_parameters={k: v for k, v in bound.arguments.items()},
            return_value=return_value,
        )

        return instance
