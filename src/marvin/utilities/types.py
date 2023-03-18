import collections
import json
import logging
import re
from functools import lru_cache
from typing import Any, Callable, Generic, Literal, TypeVar, Union

import pydantic
import ulid
from fastapi import APIRouter, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, PrivateAttr, constr
from pydantic.fields import ModelField
from sqlalchemy import TypeDecorator
from typing_extensions import Annotated

from marvin.infra.db import JSONType
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
        """Automatically generate `type` literals for subclasses."""

        value = f"{cls.__name__}"
        annotation = Literal[value]

        tag_field = ModelField.infer(
            name="type",
            value=value,
            annotation=annotation,
            class_validators=None,
            config=cls.__config__,
        )
        cls.__fields__["type"] = tag_field

    @classmethod
    def as_discriminated_union(cls):
        subclasses = get_all_subclasses(cls)
        subclass_names = [s.__name__ for s in subclasses]
        if len(subclasses) > len(set(subclass_names)):
            repeated_types = [
                item
                for item, count in collections.Counter(subclass_names).items()
                if count > 1
            ]
            repeated_subclasses = [
                s for s in subclasses if s.__name__ in repeated_types
            ]
            logger.warn(
                f"Multiple subclasses of `{cls}` have the same class name (or custom"
                " `type` literal), which will cause issues with deserialization:"
                f" {repeated_subclasses}"
            )

        union = Union[tuple(subclasses)]
        return Annotated[union, Field(discriminator="type")]


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
