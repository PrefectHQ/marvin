import sqlalchemy as sa
from sqlmodel import Field

from marvin.bots.input_transformers import InputTransformer
from marvin.infra.db import JSONType
from marvin.models.ids import BotID
from marvin.plugins.base import Plugin
from marvin.utilities.models import MarvinSQLModel
from marvin.utilities.types import MarvinBaseModel


class BotConfig(MarvinSQLModel, table=True):
    __repr_exclude__ = {"profile_picture"}
    __table_args__ = (sa.Index("uq_topic__name", "name", unique=True),)
    id: BotID = Field(default_factory=BotID.new, primary_key=True)
    name: str
    personality: str
    instructions: str
    plugins: list[dict] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONType, nullable=False, server_default="[]"),
    )
    input_transformers: list[dict] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONType, nullable=False, server_default="[]"),
    )
    profile_picture: bytes = None


class BotConfigCreate(MarvinBaseModel):
    name: str
    personality: str = "depressed"
    instructions: str = "Act as a helpful bot, according to your personality."
    plugins: list[Plugin.as_discriminated_union()] = Field(default_factory=list)
    input_transformers: list[InputTransformer.as_discriminated_union()] = Field(
        default_factory=list
    )


class BotConfigUpdate(BotConfigCreate):
    profile_picture: bytes = None
