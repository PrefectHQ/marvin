"""Convert JSON Schema to Python types with validation.

The jsonschema_to_type function converts a JSON Schema into a Python type that can be used
for validation with Pydantic. It supports:

- Basic types (string, number, integer, boolean, null)
- Complex types (arrays, objects)
- Format constraints (date-time, email, uri)
- Numeric constraints (minimum, maximum, multipleOf)
- String constraints (minLength, maxLength, pattern)
- Array constraints (minItems, maxItems, uniqueItems)
- Object properties with defaults
- References and recursive schemas
- Enums and constants
- Union types

Example:
    ```python
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name", "age"]
    }

    # Name is optional and will be inferred from schema's "title" property if not provided
    Person = jsonschema_to_type(schema)
    # Creates a validated dataclass with name, age, and optional email fields
    ```
"""

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import MISSING, field, make_dataclass
from datetime import datetime
from enum import Enum
from typing import (
    Annotated,
    Any,
    Dict,
    ForwardRef,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import (
    AnyUrl,
    EmailStr,
    Field,
    Json,
    StringConstraints,
    model_validator,
)

__all__ = ["jsonschema_to_type", "merge_defaults"]

T = TypeVar("T")

FORMAT_TYPES = {
    "date-time": datetime,
    "email": EmailStr,
    "uri": AnyUrl,
    "json": Json,
}

_classes = {}


def jsonschema_to_type(schema: Dict[str, Any], name: str = None) -> type:
    """Convert JSON schema to appropriate Python type with validation.

    Args:
        schema: A JSON Schema dictionary defining the type structure and validation rules
        name: Optional name for object schemas. Only allowed when schema type is "object".
            If not provided for objects, name will be inferred from schema's "title"
            property or default to "Root".

    Returns:
        A Python type (typically a dataclass for objects) with Pydantic validation

    Raises:
        ValueError: If a name is provided for a non-object schema

    Examples:
        Create a dataclass from an object schema:
        ```python
        schema = {
            "type": "object",
            "title": "Person",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }

        Person = jsonschema_to_type(schema)
        # Creates a dataclass with name, age, and optional email fields:
        # @dataclass
        # class Person:
        #     name: str
        #     age: int
        #     email: str | None = None
        ```
        Person(name="John", age=30)

        Create a scalar type with constraints:
        ```python
        schema = {
            "type": "string",
            "minLength": 3,
            "pattern": "^[A-Z][a-z]+$"
        }

        NameType = jsonschema_to_type(schema)
        # Creates Annotated[str, StringConstraints(min_length=3, pattern="^[A-Z][a-z]+$")]

        @dataclass
        class Name:
            name: NameType
        ```
    """
    # Always use the top-level schema for references
    if schema.get("type") == "object":
        return create_dataclass(schema, name, schemas=schema)
    elif name:
        raise ValueError(f"Can not apply name to non-object schema: {name}")
    return schema_to_type(schema, schemas=schema)


def hash_schema(schema: Dict[str, Any]) -> str:
    """Generate a deterministic hash for schema caching."""
    return hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()


def resolve_ref(ref: str, schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve JSON Schema reference to target schema."""
    path = ref.replace("#/", "").split("/")
    current = schemas
    for part in path:
        current = current.get(part, {})
    return current


def create_string_type(schema: Dict[str, Any]) -> type:
    """Create string type with optional constraints."""
    if "const" in schema:
        return Literal[schema["const"]]  # type: ignore

    if fmt := schema.get("format"):
        if fmt == "uri":
            return AnyUrl
        elif fmt == "uri-reference":
            return str
        return FORMAT_TYPES.get(fmt, str)

    constraints = {
        k: v
        for k, v in {
            "min_length": schema.get("minLength"),
            "max_length": schema.get("maxLength"),
            "pattern": schema.get("pattern"),
        }.items()
        if v is not None
    }

    return Annotated[str, StringConstraints(**constraints)] if constraints else str


def create_numeric_type(base: Type[Union[int, float]], schema: Dict[str, Any]) -> type:
    """Create numeric type with optional constraints."""
    if "const" in schema:
        return Literal[schema["const"]]  # type: ignore

    constraints = {
        k: v
        for k, v in {
            "gt": schema.get("exclusiveMinimum"),
            "ge": schema.get("minimum"),
            "lt": schema.get("exclusiveMaximum"),
            "le": schema.get("maximum"),
            "multiple_of": schema.get("multipleOf"),
        }.items()
        if v is not None
    }

    return Annotated[base, Field(**constraints)] if constraints else base


def create_enum(name: str, values: List[Any]) -> type:
    """Create enum type from list of values."""
    if all(isinstance(v, str) for v in values):
        return Enum(name, {v.upper(): v for v in values})
    return Literal[tuple(values)]  # type: ignore


def create_array_type(schema: Dict[str, Any], schemas: Dict[str, Any]) -> type:
    """Create list/set type with optional constraints."""
    items = schema.get("items", {})
    if isinstance(items, list):
        # Handle positional item schemas
        item_types = [schema_to_type(s, schemas) for s in items]
        combined = Union[tuple(item_types)]
        base = list[combined]
    else:
        # Handle single item schema
        item_type = schema_to_type(items, schemas)
        base = set if schema.get("uniqueItems") else list
        base = base[item_type]

    constraints = {
        k: v
        for k, v in {
            "min_length": schema.get("minItems"),
            "max_length": schema.get("maxItems"),
        }.items()
        if v is not None
    }

    return Annotated[base, Field(**constraints)] if constraints else base


def schema_to_type(schema: Dict[str, Any], schemas: Dict[str, Any]) -> type:
    """Convert schema to appropriate Python type."""
    if not schema:
        return object
    if "type" not in schema and "properties" in schema:
        return create_dataclass(schema, schema.get("title"), schemas)

    # Handle references first
    if "$ref" in schema:
        ref = schema["$ref"]
        # Handle self-reference
        if ref == "#":
            return ForwardRef(schema.get("title", "Root"))
        return schema_to_type(resolve_ref(ref, schemas), schemas)

    if "const" in schema:
        return Literal[schema["const"]]  # type: ignore

    if "enum" in schema:
        return create_enum(f"Enum_{len(_classes)}", schema["enum"])

    schema_type = schema.get("type")
    if not schema_type:
        return Any

    if isinstance(schema_type, list):
        # Create a copy of the schema for each type, but keep all constraints
        types = []
        for t in schema_type:
            type_schema = schema.copy()
            type_schema["type"] = t
            types.append(schema_to_type(type_schema, schemas))
        has_null = type(None) in types
        types = [t for t in types if t is not type(None)]
        if has_null:
            return Optional[Union[tuple(types)] if len(types) > 1 else types[0]]
        return Union[tuple(types)]

    type_handlers = {
        "string": lambda s: create_string_type(s),
        "integer": lambda s: create_numeric_type(int, s),
        "number": lambda s: create_numeric_type(float, s),
        "boolean": lambda _: bool,
        "null": lambda _: type(None),
        "array": lambda s: create_array_type(s, schemas),
        "object": lambda s: create_dataclass(s, s.get("title"), schemas),
    }

    return type_handlers.get(schema_type, lambda _: Any)(schema)


def sanitize_name(name: str) -> str:
    """Convert string to valid Python identifier."""
    # Step 1: replace everything except [0-9a-zA-Z_] with underscores
    cleaned = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    # Step 2: deduplicate underscores
    cleaned = re.sub(r"__+", "_", cleaned)
    # Step 3: lowercase
    cleaned = cleaned.lower()
    # Step 4: if the first char of original name isn't a letter, prepend field_
    if not name or not re.match(r"[a-zA-Z]", name[0]):
        cleaned = f"field_{cleaned}"
    # Step 5: deduplicate again and strip trailing underscores
    cleaned = re.sub(r"__+", "_", cleaned).strip("_")
    return cleaned


def get_default_value(
    schema: Dict[str, Any], prop_name: str, parent_default: Dict[str, Any] = None
) -> Any:
    """Get default value with proper priority ordering.
    1. Value from parent's default if it exists
    2. Property's own default if it exists
    3. None
    """
    if parent_default is not None and prop_name in parent_default:
        return parent_default[prop_name]
    return schema.get("default")


def create_field_with_default(
    field_type: type,
    default_value: Any,
    schema: Dict[str, Any],
) -> Any:
    """Create a field with simplified default handling."""
    # Always use None as default for complex types
    if isinstance(default_value, (dict, list)) or default_value is None:
        return field(default=None)

    # For simple types, use the value directly
    return field(default=default_value)


def create_dataclass(
    schema: Dict[str, Any], name: str = None, schemas: Dict[str, Any] = None
) -> type:
    """Create dataclass from object schema."""
    name = name or schema.get("title", "Root")
    schema_hash = hash_schema(schema)
    cache_key = (schema_hash, name)
    original_schema = schema.copy()  # Store copy for validator

    # Return existing class if already built
    if cache_key in _classes:
        existing = _classes[cache_key]
        if existing is None:
            return ForwardRef(name)
        return existing

    # Place placeholder for recursive references
    _classes[cache_key] = None

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref == "#":
            return ForwardRef(name)
        schema = resolve_ref(ref, schemas or {})

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    fields = []
    for prop_name, prop_schema in properties.items():
        field_name = sanitize_name(prop_name)

        # Check for self-reference in property
        if prop_schema.get("$ref") == "#":
            field_type = ForwardRef(name)
        else:
            field_type = schema_to_type(prop_schema, schemas)

        default_val = prop_schema.get("default", MISSING)
        is_required = prop_name in required

        # Include alias in field metadata
        meta = {"alias": prop_name}

        if default_val is not MISSING:
            if isinstance(default_val, (dict, list)):
                field_def = field(
                    default_factory=lambda d=default_val: deepcopy(d), metadata=meta
                )
            else:
                field_def = field(default=default_val, metadata=meta)
        else:
            if is_required:
                field_def = field(metadata=meta)
            else:
                field_def = field(default=None, metadata=meta)

        if is_required and default_val is not MISSING:
            fields.append((field_name, field_type, field_def))
        elif is_required:
            fields.append((field_name, field_type, field_def))
        else:
            fields.append((field_name, Optional[field_type], field_def))

    cls = make_dataclass(name, fields, kw_only=True)

    # Add model validator for defaults
    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        if isinstance(data, dict):
            return merge_defaults(data, original_schema)
        return data

    setattr(cls, "_apply_defaults", _apply_defaults)

    # Store completed class
    _classes[cache_key] = cls
    return cls


def merge_defaults(
    data: Dict[str, Any], schema: Dict[str, Any], parent_default: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Merge defaults with provided data at all levels."""
    # If we have no data
    if not data:
        # Start with parent default if available
        if parent_default:
            result = dict(parent_default)
        # Otherwise use schema default if available
        elif "default" in schema:
            result = dict(schema["default"])
        # Otherwise start empty
        else:
            result = {}
    # If we have data and a parent default, merge them
    elif parent_default:
        result = dict(parent_default)
        for key, value in data.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                # recursively merge nested dicts
                result[key] = merge_defaults(value, {"properties": {}}, result[key])
            else:
                result[key] = value
    # Otherwise just use the data
    else:
        result = dict(data)

    # For each property in the schema
    for prop_name, prop_schema in schema.get("properties", {}).items():
        # If property is missing, apply defaults in priority order
        if prop_name not in result:
            if parent_default and prop_name in parent_default:
                result[prop_name] = parent_default[prop_name]
            elif "default" in prop_schema:
                result[prop_name] = prop_schema["default"]

        # If property exists and is an object, recursively merge
        if (
            prop_name in result
            and isinstance(result[prop_name], dict)
            and prop_schema.get("type") == "object"
        ):
            # Get the appropriate default for this nested object
            nested_default = None
            if parent_default and prop_name in parent_default:
                nested_default = parent_default[prop_name]
            elif "default" in prop_schema:
                nested_default = prop_schema["default"]

            result[prop_name] = merge_defaults(
                result[prop_name], prop_schema, nested_default
            )

    return result
