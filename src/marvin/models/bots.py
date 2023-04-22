import datetime

import sqlalchemy as sa
from sqlmodel import Field

import marvin
from marvin.bot.input_transformers import InputTransformer
from marvin.infra.database import JSONType
from marvin.models.ids import BotID
from marvin.plugins.base import Plugin
from marvin.utilities.models import CreatedUpdatedMixin, MarvinSQLModel
from marvin.utilities.types import MarvinBaseModel


class BotConfig(MarvinSQLModel, CreatedUpdatedMixin, table=True):
    __tablename__ = "bot_config"
    __repr_exclude__ = {"profile_picture"}
    __table_args__ = (sa.Index("uq_bot_config__name", "name", unique=True),)
    id: BotID = Field(default_factory=BotID.new, primary_key=True)
    name: str
    personality: str
    instructions: str
    description: str = None
    llm_settings: dict = Field(
        default_factory=dict,
        sa_column=sa.Column(JSONType, nullable=False, server_default="{}"),
    )
    plugins: list[dict] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONType, nullable=False, server_default="[]"),
    )
    input_transformers: list[dict] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONType, nullable=False, server_default="[]"),
    )
    profile_picture: str = None


class BotConfigCreate(MarvinBaseModel):
    name: str
    description: str = None
    personality: str = Field(
        default_factory=lambda: marvin.bot.base.DEFAULT_PERSONALITY
    )
    instructions: str = Field(
        default_factory=lambda: marvin.bot.base.DEFAULT_INSTRUCTIONS
    )
    plugins: list[Plugin] = Field(default_factory=list)
    input_transformers: list[InputTransformer] = Field(default_factory=list)
    llm_settings: dict = Field(default_factory=dict)


class BotConfigUpdate(MarvinBaseModel):
    personality: str = None
    description: str = None
    instructions: str = None
    plugins: list[Plugin] = None
    profile_picture: str = None
    llm_settings: dict = None


class BotConfigRead(MarvinBaseModel):
    id: BotID
    name: str
    description: str = None
    personality: str
    instructions: str
    plugins: list[dict]
    input_transformers: list[dict]
    profile_picture: str = None
    created_at: datetime.datetime = None
    updated_at: datetime.datetime = None
    llm_settings: dict = None
