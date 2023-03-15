import datetime
from typing import Optional

import pendulum
import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from marvin.utilities.types import MarvinBaseModel

# define naming conventions for our Base class to use
# sqlalchemy will use the following templated strings
# to generate the names of indices, constraints, and keys
#
# we offset the table name with two underscores (__) to
# help differentiate, for example, between "flow_run.state_type"
# and "flow_run_state.type".
#
# more information on this templating and available
# customization can be found here
# https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.MetaData
#
# this also allows us to avoid having to specify names explicitly
# when using sa.ForeignKey.use_alter = True
# https://docs.sqlalchemy.org/en/14/core/constraints.html
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(table_name)s__%(column_0_N_name)s",
    "uq": "uq_%(table_name)s__%(column_0_N_name)s",
    "ck": "ck_%(table_name)s__%(constraint_name)s",
    "fk": "fk_%(table_name)s__%(column_0_N_name)s__%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class MarvinSQLModel(SQLModel, MarvinBaseModel):
    __repr_include__: list[str] = []
    __repr_exclude__: list[str] = []

    class Config:
        copy_on_model_validation = False

    def __repr__(self):
        repr_include = set(self.__repr_include__) or set(self.__fields__)
        repr_exclude = set(self.__repr_exclude__)
        for cls in type(self).__mro__:
            if issubclass(cls, MarvinSQLModel):
                repr_exclude.update(cls.__repr_exclude__)

        repr_attrs = ", ".join(
            f"{k}={getattr(self, k)!r}"
            for k in self.__fields__
            if k in repr_include.difference(repr_exclude)
        )
        return f"{self.__class__.__name__}({repr_attrs})"

    # required in order to access columns with server defaults
    # or SQL expression defaults, subsequent to a flush, without
    # triggering an expired load
    #
    # this allows us to load attributes with a server default after
    # an INSERT, for example
    #
    # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = {"extend_existing": True}


class TimestampMixin:
    __repr_exclude__ = ["created_at", "updated_at"]

    created_at: Optional[datetime.datetime] = Field(
        default_factory=lambda: pendulum.now("utc"),
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    updated_at: Optional[datetime.datetime] = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
            index=True,
        )
    )
