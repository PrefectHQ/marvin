import sqlalchemy as sa
from sqlmodel import Field

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
        sa_column=sa.Column(JSONType, nullable=False, server_default="[]"),
    )
    profile_picture: bytes = None


class BotConfigCreate(MarvinBaseModel):
    name: str
    personality: str
    instructions: str
    plugins: list[Plugin]


class BotConfigUpdate(BotConfigCreate):
    profile_picture: bytes = None
