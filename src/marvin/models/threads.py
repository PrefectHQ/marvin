import datetime
from typing import Literal

import pendulum
import sqlalchemy as sa
from sqlmodel import Field

import marvin
from marvin.infra.db import AsyncSession, JSONType, provide_session
from marvin.models.base import BaseSQLModel
from marvin.models.ids import BotID, MessageID, ThreadID
from marvin.utilities.types import MarvinBaseModel

RoleType = Literal["system", "user", "ai"]


class BaseMessage(MarvinBaseModel):
    timestamp: datetime.datetime = Field(default_factory=lambda: pendulum.now("utc"))
    role: RoleType
    name: str = None
    content: str
    data: dict = Field(default_factory=dict)


class Message(BaseMessage, BaseSQLModel, table=True):
    __table_args__ = (
        sa.ForeignKeyConstraint(["thread_id"], ["thread.id"], ondelete="CASCADE"),
        sa.Index(
            "ix_message__thread_id_timestamp",
            "thread_id",
            sa.text("timestamp DESC"),
        ),
    )
    id: MessageID = Field(default_factory=MessageID.new, primary_key=True)
    thread_id: ThreadID
    role: str
    timestamp: datetime.datetime = Field(
        default_factory=lambda: pendulum.now("utc"),
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    bot_id: BotID = None
    data: dict = Field(
        default_factory=dict,
        sa_column=sa.Column(JSONType, nullable=False, server_default="{}"),
    )

    def to_dict(self) -> dict:
        return self.dict(include={"role", "name", "content"}, include_none=False)


class MessageCreate(BaseMessage):
    pass


class Thread(BaseSQLModel, table=True):
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["parent_thread_id"], ["thread.id"], ondelete="CASCADE"
        ),
        sa.Index("uq_thread__lookup_key", "lookup_key", unique=True),
    )
    id: ThreadID = Field(default_factory=ThreadID.new, primary_key=True)
    parent_thread_id: ThreadID = None
    lookup_key: str = Field(
        None,
        description="Optional, user-provided key to lookup a thread.",
    )
    name: str = None
    is_visible: bool = Field(
        False,
        index=True,
        description=(
            "Every conversation takes place in a thread; however, only certain threads"
            ' are "visible" to users. Visible threads are meaningful to users and are'
            " typically displayed in the UI; when users dismiss threads from the UI"
            " they can be marked as invisible. Defaults to false."
        ),
    )
    context: dict = Field(
        default_factory=dict,
        sa_column=sa.Column(JSONType, nullable=False, server_default="{}"),
    )

    @provide_session()
    async def get_messages(self, n: int = None, session: AsyncSession = None):
        return await marvin.api.threads._get_messages_by_thread_id(
            thread_id=self.id, n=n, session=session
        )
