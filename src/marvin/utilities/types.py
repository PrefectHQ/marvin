import importlib.util
import json
import logging
import re
import typing
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from types import GenericAlias
from typing import Any, Callable, Generic, Literal, TypeVar, Union

import pydantic
import ulid
from fastapi import APIRouter, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, PrivateAttr, constr
from pydantic.fields import ModelField
from sqlalchemy import TypeDecorator

from marvin.utilities.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
UUID_REGEX = re.compile(
    r"\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}\b"
)
# ulid
ULID_REGEX = r"\b[0-9A-HJ-NP-TV-Z]{26}\b"
# specific prefix
PREFIXED_ULID_REGEX = r"\b{prefix}_[0-9A-HJ-NP-TV-Z]{{26}}\b"
# any prefix
ANY_PREFIX_ULID_REGEX = r"\b[^\W0-9_][^\W_]+_[0-9A-HJ-NP-TV-Z]{26}\b"
# optional prefix
ANY_ULID_REGEX = r"\b(?:[^\W0-9_][^\W_]+_)?[0-9A-HJ-NP-TV-Z]{26}\b"


DISCRIMINATING_TYPE_REGISTRY = {}


@lru_cache()
def get_id_type(prefix: str = None) -> type:
    if prefix is None:
        type_ = constr(regex=ULID_REGEX)
        type_.new = lambda: str(ulid.new())
    else:
        if "_" in prefix:
            raise ValueError("Prefix must not contain underscores.")
        type_ = constr(regex=PREFIXED_ULID_REGEX.format(prefix=prefix))
        type_.new = lambda: f"{prefix}_{ulid.new()}"
        type_.regex = PREFIXED_ULID_REGEX.format(prefix=prefix)
    return type_


class MarvinBaseModel(BaseModel):
    class Config:
        copy_on_model_validation = "shallow"
        validate_assignment = True
        extra = "forbid"
        json_encoders = {}

    def __init__(self, **data):
        # check for any fields annotated as DiscriminatingTypeModel classes and
        # properly instantiate their subclasses from the registry
        for field_name, field in self.__fields__.items():
            # first extract the type of the field
            model = extract_class(field.type_)
            # check if the type is a DiscriminatingTypeModel, and the data
            # contains a value for this field
            if (
                isinstance(model, type)
                and issubclass(model, DiscriminatingTypeModel)
                and data.get(field_name)
            ):
                # load the registered subclasses for this model, as a union if necessary
                if subclasses := DISCRIMINATING_TYPE_REGISTRY.get(model, []):
                    if len(subclasses) > 1:
                        new_model = Union[tuple(subclasses)]
                    else:
                        new_model == subclasses[0]

                # parse the input objects into the appropriate subclass, first
                # by creating a structure that replaces the generic
                # DiscriminatingTypeModel with the new subclass type
                structure = replace_class(field.outer_type_, model, new_model)
                data[field_name] = pydantic.parse_obj_as(structure, data[field_name])

        # instantiate the object
        super().__init__(**data)

    def dict(self, *args, json_compatible=False, **kwargs):
        if json_compatible:
            return json.loads(self.json(*args, **kwargs))
        return super().dict(*args, **kwargs)

    def copy_with_updates(self, exclude: set[str] = None, **updates):
        """
        Copies the current model and updates the copy with the provided updates,
        which can be partial nested dictionaries.

        Unlike `copy(update=updates)`, this method will properly validate
        updates and apply nested updates.
        """
        updated = self.dict(exclude=exclude)

        stack = [(updated, k, v) for k, v in updates.items()]
        while stack:
            m, k, v = stack.pop()
            mv = m.get(k)
            if isinstance(mv, dict) and isinstance(v, dict):
                stack.extend([(mv, vk, vv) for vk, vv in v.items()])
            else:
                m[k] = v

        excluded = set(self.__exclude_fields__ or []).union(exclude or [])
        excluded_kwargs = {e: getattr(self, e) for e in excluded if e not in updated}
        return type(self)(**updated, **excluded_kwargs)


class LoggerMixin(BaseModel):
    _logger: logging.Logger = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._logger = get_logger(type(self).__name__)

    @property
    def logger(self):
        return self._logger


class DiscriminatingTypeModel(MarvinBaseModel):
    def __init_subclass__(cls, **kwargs):
        """
        Automatically generate `discriminator` literals for subclasses and
        register them for deserialization
        """

        if discriminator := getattr(cls, "_discriminator", None) is not None:
            value = discriminator
        else:
            value = f"{cls.__name__}"

        discriminator_field = ModelField.infer(
            name="discriminator",
            value=value,
            annotation=Literal[value],
            class_validators=None,
            config=cls.__config__,
        )
        cls.__fields__["discriminator"] = discriminator_field

        # when a field is annotated, we will lookup all children classes to
        # attempt deserialization. Therefore we must register this subclass
        # under all parents.
        for parent_cls in cls.__mro__:
            if (
                issubclass(parent_cls, DiscriminatingTypeModel)
                and parent_cls is not DiscriminatingTypeModel
            ):
                DISCRIMINATING_TYPE_REGISTRY.setdefault(parent_cls, []).append(cls)


class MarvinRouter(APIRouter):
    """
    Utilities to make the router a little more convenient to use.
    """

    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], **kwargs: Any
    ) -> None:
        """
        Add an API route.

        For routes that return content and have not specified a `response_model`,
        use return type annotation to infer the response model.

        For routes that return No-Content status codes, explicitly set
        a `response_class` to ensure nothing is returned in the response body.
        """
        if kwargs.get("status_code") == status.HTTP_204_NO_CONTENT:
            # any routes that return No-Content status codes must
            # explicilty set a response_class that will handle status codes
            # and not return anything in the body
            kwargs["response_class"] = Response
        return super().add_api_route(path, endpoint, **kwargs)


def pydantic_column_type(pydantic_type):
    """
    SA Column for converting pydantic models to and from JSON
    """

    from marvin.infra.db import JSONType

    class PydanticJSONType(TypeDecorator, Generic[T]):
        impl = JSONType()

        def bind_processor(self, dialect):
            impl_processor = self.impl.bind_processor(dialect)
            if impl_processor:

                def process(value: T):
                    if value is not None:
                        if isinstance(pydantic_type, pydantic.main.ModelMetaclass):
                            # This allows to assign non-InDB models and if they're
                            # compatible, they're directly parsed into the InDB
                            # representation, thus hiding the implementation in the
                            # background. However, the InDB model will still be returned
                            value_to_dump = pydantic_type.from_orm(value)
                        else:
                            value_to_dump = value
                        value = jsonable_encoder(value_to_dump)
                    return impl_processor(value)

            else:

                def process(value):
                    if isinstance(pydantic_type, pydantic.main.ModelMetaclass):
                        # This allows to assign non-InDB models and if they're
                        # compatible, they're directly parsed into the InDB
                        # representation, thus hiding the implementation in the
                        # background. However, the InDB model will still be returned
                        value_to_dump = pydantic_type.from_orm(value)
                    else:
                        value_to_dump = value
                    value = json.dumps(jsonable_encoder(value_to_dump))
                    return value

            return process

        def result_processor(self, dialect, coltype) -> T:
            impl_processor = self.impl.result_processor(dialect, coltype)
            if impl_processor:

                def process(value):
                    value = impl_processor(value)
                    if value is None:
                        return None

                    data = value
                    # Explicitly use the generic directly, not type(T)
                    full_obj = pydantic.parse_obj_as(pydantic_type, data)
                    return full_obj

            else:

                def process(value):
                    if value is None:
                        return None

                    # Explicitly use the generic directly, not type(T)
                    full_obj = pydantic.parse_obj_as(pydantic_type, value)
                    return full_obj

            return process

        def compare_values(self, x, y):
            return x == y

    return PydanticJSONType


def get_all_subclasses(cls):
    return (
        {cls}
        .union(cls.__subclasses__())
        .union([s for c in cls.__subclasses__() for s in get_all_subclasses(c)])
    )


def safe_issubclass(type_, classes):
    if isinstance(type_, type) and not isinstance(type_, GenericAlias):
        return issubclass(type_, classes)
    else:
        return False


def type_to_schema(type_) -> dict:
    if safe_issubclass(type_, pydantic.BaseModel):
        return type_.schema()
    else:

        class Model(pydantic.BaseModel):
            __root__: type_

        return Model.schema()


def schema_to_type(schema: dict):
    # defer for performance
    import datamodel_code_generator

    with TemporaryDirectory() as temporary_directory_name:
        temporary_directory = Path(temporary_directory_name)
        output = Path(temporary_directory / "model.py")

        # write schema to a file
        datamodel_code_generator.generate(
            json.dumps(schema),
            input_file_type=datamodel_code_generator.InputFileType.JsonSchema,
            input_filename="example.json",
            output=output,
            validation=True,
        )

        # import the file
        module_name = "marvin_tmp_models"
        spec = importlib.util.spec_from_file_location(module_name, str(output))
        module = importlib.util.module_from_spec(spec)
        # sys.modules[module_name] = module
        spec.loader.exec_module(module)

        model_name = schema.get("title", "Model")
        model = getattr(module, model_name)
        model.update_forward_refs(**typing.__dict__)

        return model


def format_type_str(type_) -> str:
    """
    The str(type: type) is not very readable, so we format it to be more readable.
    """
    if isinstance(type_, type):
        return type_.__name__
    else:
        return str(type_)


def extract_class(generic_alias):
    """
    Given the following, retrieves type `T`:
        list[T] tuple[T] set[T] dict[Any, T]

    Also works with any combination of these, e.g.:
        list[set[tuple[T]]] dict[Any, [list[T]]]

    However, it will not work if there are multiple types in the container,
    because it gets the "last" type e.g.:
        list[T, U] -> would return U

    """
    if hasattr(generic_alias, "__origin__") and generic_alias.__origin__ in (
        list,
        tuple,
        dict,
        set,
    ):
        return extract_class(generic_alias.__args__[-1])
    else:
        return generic_alias


def replace_class(generic_alias, old_class, new_class):
    """
    Given the following, replaces type `T` with `new_class` (`U` in this case):
        T -> U
        list[T] -> list[U]
        tuple[Any, T] -> tuple[Any, U]
        dict[Any, T] -> dict[Any, U]
        dict[Any, list[T]] -> dict[Any, list[U]]
        set[T] -> set[U]
        list[dict[Any, list[T]]] -> list[dict[Any, list[U]]
    """

    if hasattr(generic_alias, "__origin__") and generic_alias.__origin__ in (
        list,
        tuple,
        dict,
        set,
    ):
        replaced_args = tuple(
            replace_class(arg, old_class, new_class) for arg in generic_alias.__args__
        )
        return generic_alias.__origin__[replaced_args]
    else:
        return new_class if generic_alias == old_class else generic_alias
