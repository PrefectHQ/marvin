import datetime
from typing import Literal

import pendulum
import sqlalchemy as sa
from sqlmodel import Field

import marvin
from marvin.infra.database import AsyncSession, JSONType, provide_session
from marvin.models.ids import BotID, MessageID, ThreadID
from marvin.utilities.models import CreatedUpdatedMixin, MarvinSQLModel
from marvin.utilities.types import MarvinBaseModel

RoleType = Literal["system", "user", "ai"]


class BaseMessage(MarvinBaseModel):
    id: MessageID = Field(default_factory=MessageID.new)
    role: RoleType
    content: str
    name: str = None
    timestamp: datetime.datetime = Field(default_factory=lambda: pendulum.now("utc"))
    bot_id: BotID = None
    data: dict = Field(default_factory=dict)


class Message(MarvinSQLModel, BaseMessage, table=True):
    __table_args__ = (
        sa.ForeignKeyConstraint(["thread_id"], ["thread.id"], ondelete="CASCADE"),
        sa.Index(
            "ix_message__thread_id_timestamp",
            "thread_id",
            "timestamp",
        ),
    )
    id: MessageID = Field(default_factory=MessageID.new, primary_key=True)
    thread_id: ThreadID
    role: str  # should be one of `RoleType` at this time, could change in the future
    timestamp: datetime.datetime = Field(
        default_factory=lambda: pendulum.now("utc"),
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    data: dict = Field(
        default_factory=dict,
        sa_column=sa.Column(JSONType, nullable=False, server_default="{}"),
    )


class MessageCreate(MarvinBaseModel):
    role: RoleType
    content: str
    name: str = None
    bot_id: BotID = None
    data: dict = Field(default_factory=dict)


class MessageRead(MarvinBaseModel):
    id: MessageID
    role: RoleType
    content: str
    name: str = None
    timestamp: datetime.datetime
    bot_id: BotID = None
    data: dict = Field(default_factory=dict)


class UserMessageCreate(MessageCreate):
    role: Literal["user"] = "user"


class Thread(MarvinSQLModel, CreatedUpdatedMixin, table=True):
    __table_args__ = (sa.Index("uq_thread__lookup_key", "lookup_key", unique=True),)
    id: ThreadID = Field(default_factory=ThreadID.new, primary_key=True)
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


class ThreadCreate(MarvinBaseModel):
    lookup_key: str
    name: str = None
    context: dict = Field(default_factory=dict)
    is_visible: bool = False


class ThreadUpdate(MarvinBaseModel):
    lookup_key: str = None
    name: str = None
    context: dict = None
    is_visible: bool = None


class ThreadRead(MarvinBaseModel):
    id: ThreadID
    lookup_key: str
    name: str = None
    is_visible: bool = False
    context: dict = Field(default_factory=dict)
    created_at: datetime.datetime = None
    updated_at: datetime.datetime = None

    @classmethod
    def from_model(cls, thread: Thread):
        return cls(
            id=thread.id,
            lookup_key=thread.lookup_key,
            name=thread.name,
            is_visible=thread.is_visible,
            context=thread.context,
        )


# class ThreadSummary(DBModel, table=True):
#     """
#     Table for storing summaries of threads at a certain point, to assist with
#     long-term memory
#     """

#     __table_args__ = (
#         sa.ForeignKeyConstraint(["thread_id"], ["thread.id"], ondelete="CASCADE"),
#         sa.Index("ix_thread_summary__thread_id_timestamp", "thread_id", "timestamp"),
#     )

#     id: GenericID = Field(default_factory=GenericID.new, primary_key=True)
#     thread_id: ThreadID
#     summary: str
#     timestamp: datetime.datetime
